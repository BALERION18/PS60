"""Model store — save and load trained ML models with metadata.

All trained models are stored as .pkl files (joblib format) alongside
a .json sidecar that records training metadata: when it was trained,
what data it was trained on, hyperparameters, and validation scores.

Directory layout (default, overridable via env var MODEL_STORE_DIR):

    models/
    └── vibration_anomaly/
        ├── vibration_anomaly_v1.pkl      ← joblib-serialised sklearn Pipeline
        └── vibration_anomaly_v1.json     ← metadata sidecar

The model version is embedded in the filename so multiple versions
can coexist.  The loader always picks the version explicitly requested,
or the "latest" symlink if one is maintained.

Thread/process safety: writes use atomic rename (write to .tmp, rename)
so a partially written file is never visible to the inference path.
"""
from __future__ import annotations

import json
import os
import shutil
import tempfile
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import joblib
import structlog

log = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Default model store directory
# ---------------------------------------------------------------------------
_DEFAULT_STORE_DIR = Path(
    os.environ.get("MODEL_STORE_DIR", "models")
)


# ---------------------------------------------------------------------------
# Metadata dataclass
# ---------------------------------------------------------------------------

@dataclass
class ModelMetadata:
    """Sidecar metadata stored alongside every saved model."""
    model_name: str
    model_version: str
    trained_at: str                     # ISO-8601 UTC
    algorithm: str                      # e.g. "IsolationForest"
    feature_names: list[str]            # ordered feature list used at training
    n_features: int
    n_training_samples: int
    hyperparameters: Dict[str, Any]     # key hyperparams used
    val_scores: Dict[str, float]        # e.g. {"recall_anomaly": 0.94, ...}
    notes: str = ""
    model_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "ModelMetadata":
        return cls(**d)

    @classmethod
    def from_json_file(cls, path: Path) -> "ModelMetadata":
        with open(path, "r", encoding="utf-8") as f:
            return cls.from_dict(json.load(f))

    def to_json_file(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)


# ---------------------------------------------------------------------------
# ModelStore
# ---------------------------------------------------------------------------

class ModelStore:
    """Handles saving and loading of sklearn-compatible model objects.

    Args:
        store_dir: Root directory for model storage.
                   Defaults to MODEL_STORE_DIR env var, or ./models.
    """

    def __init__(self, store_dir: Optional[Path] = None) -> None:
        self._root = Path(store_dir) if store_dir else _DEFAULT_STORE_DIR
        self._root.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Paths
    # ------------------------------------------------------------------

    def _model_dir(self, model_name: str) -> Path:
        return self._root / model_name

    def _pkl_path(self, model_name: str, version: str) -> Path:
        return self._model_dir(model_name) / f"{model_name}_{version}.pkl"

    def _meta_path(self, model_name: str, version: str) -> Path:
        return self._model_dir(model_name) / f"{model_name}_{version}.json"

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------

    def save(
        self,
        model: Any,
        metadata: ModelMetadata,
    ) -> Path:
        """Persist a trained model and its metadata sidecar atomically.

        Args:
            model:    A fitted sklearn estimator (or Pipeline).
            metadata: ModelMetadata instance describing the training run.

        Returns:
            Path to the saved .pkl file.
        """
        model_dir = self._model_dir(metadata.model_name)
        model_dir.mkdir(parents=True, exist_ok=True)

        pkl_path  = self._pkl_path(metadata.model_name, metadata.model_version)
        meta_path = self._meta_path(metadata.model_name, metadata.model_version)

        # Atomic write: dump to temp file, then rename
        fd, tmp_pkl = tempfile.mkstemp(dir=model_dir, suffix=".tmp.pkl")
        os.close(fd)
        try:
            joblib.dump(model, tmp_pkl, compress=3)
            shutil.move(tmp_pkl, pkl_path)
        except Exception:
            os.unlink(tmp_pkl)
            raise

        # Metadata sidecar (not atomic but harmless if partial)
        metadata.to_json_file(meta_path)

        log.info(
            "model_store.saved",
            model_name=metadata.model_name,
            version=metadata.model_version,
            path=str(pkl_path),
            n_train=metadata.n_training_samples,
            val_scores=metadata.val_scores,
        )
        return pkl_path

    # ------------------------------------------------------------------
    # Load
    # ------------------------------------------------------------------

    def load(
        self,
        model_name: str,
        version: str,
    ) -> tuple[Any, ModelMetadata]:
        """Load a model and its metadata.

        Args:
            model_name: e.g. "vibration_anomaly"
            version:    e.g. "v1"

        Returns:
            (model, metadata) tuple.

        Raises:
            FileNotFoundError: if the .pkl file does not exist.
        """
        pkl_path  = self._pkl_path(model_name, version)
        meta_path = self._meta_path(model_name, version)

        if not pkl_path.exists():
            raise FileNotFoundError(
                f"No model found at {pkl_path}. "
                f"Run the training script first: "
                f"python -m scripts.train_vibration_model"
            )

        model = joblib.load(pkl_path)

        metadata: ModelMetadata
        if meta_path.exists():
            metadata = ModelMetadata.from_json_file(meta_path)
        else:
            log.warning("model_store.no_metadata", path=str(meta_path))
            metadata = ModelMetadata(
                model_name=model_name,
                model_version=version,
                trained_at="unknown",
                algorithm="unknown",
                feature_names=[],
                n_features=0,
                n_training_samples=0,
                hyperparameters={},
                val_scores={},
                notes="Metadata sidecar missing",
            )

        log.info(
            "model_store.loaded",
            model_name=model_name,
            version=version,
            trained_at=metadata.trained_at,
            val_scores=metadata.val_scores,
        )
        return model, metadata

    def exists(self, model_name: str, version: str) -> bool:
        """Return True if the model .pkl file exists on disk."""
        return self._pkl_path(model_name, version).exists()

    def list_versions(self, model_name: str) -> list[str]:
        """Return all saved versions for a model name, sorted newest first."""
        model_dir = self._model_dir(model_name)
        if not model_dir.exists():
            return []
        versions = []
        for p in model_dir.glob(f"{model_name}_*.pkl"):
            # Extract version from filename: {model_name}_{version}.pkl
            stem = p.stem  # e.g. "vibration_anomaly_v1"
            version = stem[len(model_name) + 1:]  # strip prefix + underscore
            versions.append(version)
        return sorted(versions, reverse=True)


# ---------------------------------------------------------------------------
# Module-level singleton (lazy init — no model loaded until first call)
# ---------------------------------------------------------------------------
_default_store: Optional[ModelStore] = None


def get_model_store() -> ModelStore:
    """Return the default ModelStore singleton."""
    global _default_store
    if _default_store is None:
        _default_store = ModelStore()
    return _default_store


def utcnow_iso() -> str:
    """Return current UTC time as ISO-8601 string."""
    return datetime.now(tz=timezone.utc).isoformat()

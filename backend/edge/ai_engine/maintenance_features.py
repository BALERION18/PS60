"""Feature engineering for the Predictive Maintenance Random Forest model.

Feature vector layout (fixed order — never reorder after training):

    Index  Name                          Description
    -----  ----------------------------  -----------------------------------------
    0      runtime_hours_since_service   Hours since last maintenance event
    1      anomaly_score_latest          Latest IF score from Model 2 (lower = worse)
    2      anomaly_events_7d             Count of anomaly events in last 7 days
    3      anomaly_events_30d            Count of anomaly events in last 30 days
    4      vibration_trend_7d            Mean vibration RMS over last 7 days
    5      vibration_std_7d              Std-dev of vibration over last 7 days
    6      oil_pressure_trend_7d         Mean oil pressure over last 7 days
    7      oil_pressure_drop_rate        Rate of oil pressure decline (bar/day)
    8      coolant_temp_trend_7d         Mean coolant temp over last 7 days
    9      coolant_temp_max_7d           Peak coolant temp in last 7 days
    10     power_output_trend_7d         Mean power output over last 7 days
    11     power_variance_7d             Variance of power output (load instability)
    12     fuel_consumption_trend_7d     Mean fuel consumption over last 7 days
    13     runtime_hours_total           Estimated total asset lifetime hours
    14     days_since_last_maintenance   Calendar days since last service

All values are normalised to [0, 1] using clip_normalise() with physical maxima.
Missing/unavailable values fall back to their nominal (healthy) defaults.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np

# ---------------------------------------------------------------------------
# Feature spec: (name, clip_max, nominal_value)
# clip_max  — physical upper bound for normalisation
# nominal   — used when a value is not available (healthy/average default)
# ---------------------------------------------------------------------------
MAINT_FEATURE_SPEC: List[tuple] = [
    # name                          clip_max   nominal
    ("runtime_hours_since_service", 2000.0,    500.0),
    ("anomaly_score_latest",          1.0,      0.0),   # inverted IF score: 0=normal,1=critical
    ("anomaly_events_7d",            20.0,      0.0),
    ("anomaly_events_30d",           60.0,      0.0),
    ("vibration_trend_7d",           30.0,      3.0),
    ("vibration_std_7d",             10.0,      0.5),
    ("oil_pressure_trend_7d",        10.0,      4.5),
    ("oil_pressure_drop_rate",        2.0,      0.0),   # bar/day drop (positive = drop)
    ("coolant_temp_trend_7d",       120.0,     85.0),
    ("coolant_temp_max_7d",         120.0,     92.0),
    ("power_output_trend_7d",       250.0,    100.0),
    ("power_variance_7d",          2500.0,    100.0),
    ("fuel_consumption_trend_7d",    60.0,     15.0),
    ("runtime_hours_total",       50000.0,   8000.0),
    ("days_since_last_maintenance",  730.0,     90.0),
]

MAINT_FEATURE_NAMES: List[str] = [f[0] for f in MAINT_FEATURE_SPEC]
N_MAINT_FEATURES: int = len(MAINT_FEATURE_SPEC)

# ---------------------------------------------------------------------------
# Urgency classes (labels)
# ---------------------------------------------------------------------------
URGENCY_CLASSES = ["NONE", "LOW", "MEDIUM", "HIGH"]
URGENCY_TO_INT  = {u: i for i, u in enumerate(URGENCY_CLASSES)}
INT_TO_URGENCY  = {i: u for i, u in enumerate(URGENCY_CLASSES)}

# Recommended tasks per urgency + dominant signal
TASK_DESCRIPTIONS = {
    ("HIGH",   "vibration"):    "Bearing inspection & lubrication — urgent",
    ("HIGH",   "oil"):          "Oil system inspection — potential seal failure",
    ("HIGH",   "coolant"):      "Cooling system inspection — overtemp risk",
    ("HIGH",   "runtime"):      "Scheduled major service overdue",
    ("MEDIUM", "vibration"):    "Monitor vibration — schedule bearing check",
    ("MEDIUM", "oil"):          "Check oil level and pressure sensors",
    ("MEDIUM", "coolant"):      "Inspect coolant level and thermostat",
    ("MEDIUM", "runtime"):      "Routine service due within 2 weeks",
    ("LOW",    "vibration"):    "Log vibration trend — no immediate action",
    ("LOW",    "runtime"):      "Upcoming scheduled service — plan resources",
    ("NONE",   "nominal"):      "No maintenance required",
}


def _clip_norm(value: float, clip_max: float) -> float:
    """Clip to [0, clip_max] then normalise to [0, 1]."""
    return float(np.clip(value, 0.0, clip_max) / clip_max) if clip_max > 0 else 0.0


def _invert_if_score(raw_if_score: float) -> float:
    """Convert IsolationForest decision_function score to anomaly intensity.

    IF score is in roughly [-0.5, 0.5] where lower = more anomalous.
    We invert so that 0 = normal and 1 = most anomalous (for the RF to work
    intuitively — higher feature value = worse condition).
    """
    # Shift: [-0.5, 0.5] → [1.0, 0.0]
    return float(np.clip((-raw_if_score + 0.5), 0.0, 1.0))


# ---------------------------------------------------------------------------
# Feature vector builder
# ---------------------------------------------------------------------------

def build_feature_vector(
    runtime_hours_since_service: float = 500.0,
    anomaly_score_latest: float        = 0.1,    # raw IF score
    anomaly_events_7d: int             = 0,
    anomaly_events_30d: int            = 0,
    vibration_trend_7d: float          = 3.0,
    vibration_std_7d: float            = 0.5,
    oil_pressure_trend_7d: float       = 4.5,
    oil_pressure_drop_rate: float      = 0.0,
    coolant_temp_trend_7d: float       = 85.0,
    coolant_temp_max_7d: float         = 92.0,
    power_output_trend_7d: float       = 100.0,
    power_variance_7d: float           = 100.0,
    fuel_consumption_trend_7d: float   = 15.0,
    runtime_hours_total: float         = 8000.0,
    days_since_last_maintenance: float = 90.0,
) -> np.ndarray:
    """Build a normalised feature vector for the maintenance classifier.

    All raw values are accepted in physical units and normalised internally.
    Returns np.ndarray of shape (N_MAINT_FEATURES,) with values in [0, 1].
    """
    # Invert IF score so higher = worse (more anomalous)
    anomaly_intensity = _invert_if_score(anomaly_score_latest)

    raw_values = [
        runtime_hours_since_service,
        anomaly_intensity,               # already inverted
        float(anomaly_events_7d),
        float(anomaly_events_30d),
        vibration_trend_7d,
        vibration_std_7d,
        oil_pressure_trend_7d,
        oil_pressure_drop_rate,
        coolant_temp_trend_7d,
        coolant_temp_max_7d,
        power_output_trend_7d,
        power_variance_7d,
        fuel_consumption_trend_7d,
        runtime_hours_total,
        days_since_last_maintenance,
    ]

    vec = np.empty(N_MAINT_FEATURES, dtype=np.float32)
    for i, (raw, (_, clip_max, _)) in enumerate(zip(raw_values, MAINT_FEATURE_SPEC)):
        vec[i] = _clip_norm(raw, clip_max)

    return vec


def build_feature_dict_to_vector(features: Dict[str, float]) -> np.ndarray:
    """Build feature vector from a dict of {feature_name: raw_value}.

    Missing keys fall back to their nominal defaults.
    """
    kwargs = {}
    for name, _, nominal in MAINT_FEATURE_SPEC:
        kwargs[name] = features.get(name, nominal)
    return build_feature_vector(**kwargs)


# ---------------------------------------------------------------------------
# Dominant signal detector (for task description selection)
# ---------------------------------------------------------------------------

def dominant_signal(features: Dict[str, float]) -> str:
    """Identify which sensor group is driving the maintenance need.

    Returns one of: 'vibration', 'oil', 'coolant', 'runtime', 'nominal'
    """
    vib   = features.get("vibration_trend_7d", 3.0)
    oil   = features.get("oil_pressure_trend_7d", 4.5)
    drop  = features.get("oil_pressure_drop_rate", 0.0)
    cool  = features.get("coolant_temp_trend_7d", 85.0)
    hours = features.get("runtime_hours_since_service", 500.0)
    anom  = features.get("anomaly_events_7d", 0)

    # Oil pressure critically low takes priority — most dangerous single-sensor fault
    if oil < 3.0 or drop > 0.3:
        return "oil"
    if cool > 100.0:
        return "coolant"
    if vib > 10.0 or anom > 5:
        return "vibration"
    if hours > 1500.0:
        return "runtime"
    return "nominal"


def get_task_description(urgency: str, features: Dict[str, float]) -> str:
    """Return a human-readable maintenance task description."""
    signal = dominant_signal(features)
    key = (urgency, signal)
    if key in TASK_DESCRIPTIONS:
        return TASK_DESCRIPTIONS[key]
    # Fallback
    fallback = {
        "HIGH":   "Immediate inspection required",
        "MEDIUM": "Schedule maintenance within 2 weeks",
        "LOW":    "Monitor and plan next service",
        "NONE":   "No maintenance required",
    }
    return fallback.get(urgency, "Review asset condition")


# ---------------------------------------------------------------------------
# AssetState — rolling accumulator for live inference
# ---------------------------------------------------------------------------

@dataclass
class AssetState:
    """Accumulates per-asset telemetry for maintenance feature computation.

    Updated incrementally as sensor readings arrive and anomaly scores
    are produced by Model 2.  Maintains rolling windows for trend features.
    """
    asset_id: str
    runtime_hours_since_service: float = 500.0
    runtime_hours_total: float         = 8000.0
    days_since_last_maintenance: float = 90.0

    # Rolling windows (raw values, kept for up to 7 days × samples/day)
    vibration_window:    List[float] = field(default_factory=list)
    oil_pressure_window: List[float] = field(default_factory=list)
    coolant_temp_window: List[float] = field(default_factory=list)
    power_output_window: List[float] = field(default_factory=list)
    fuel_consumption_window: List[float] = field(default_factory=list)

    # Anomaly event counts
    anomaly_events_7d:  int   = 0
    anomaly_events_30d: int   = 0
    anomaly_score_latest: float = 0.1   # raw IF score

    # Window max length (7 days × 8640 readings/day at 10s interval = 60480)
    # Use 8640 as a practical cap (~1 day at 10s)
    _MAX_WINDOW: int = field(default=8640, init=False, repr=False)

    def update_sensor(self, suffix: str, value: float) -> None:
        """Push one sensor value into the appropriate rolling window."""
        def _push(lst: List[float], v: float) -> None:
            lst.append(v)
            if len(lst) > self._MAX_WINDOW:
                lst.pop(0)

        if suffix == "vibration_rms":
            _push(self.vibration_window, value)
        elif suffix == "oil_pressure_bar":
            _push(self.oil_pressure_window, value)
        elif suffix == "coolant_temp_c":
            _push(self.coolant_temp_window, value)
        elif suffix == "power_output_kw":
            _push(self.power_output_window, value)
        elif suffix == "fuel_consumption_lph":
            _push(self.fuel_consumption_window, value)

    def update_anomaly(self, if_score: float, is_anomaly: bool) -> None:
        """Record the latest IF anomaly score and increment event counters."""
        self.anomaly_score_latest = if_score
        if is_anomaly:
            self.anomaly_events_7d  += 1
            self.anomaly_events_30d += 1

    def _mean(self, lst: List[float], default: float) -> float:
        return float(np.mean(lst)) if lst else default

    def _std(self, lst: List[float], default: float) -> float:
        return float(np.std(lst)) if len(lst) > 1 else default

    def _max(self, lst: List[float], default: float) -> float:
        return float(max(lst)) if lst else default

    def _drop_rate(self, lst: List[float]) -> float:
        """Estimate bar/day drop rate from oil pressure window."""
        if len(lst) < 2:
            return 0.0
        # Simple linear slope: negative slope = drop
        x = np.arange(len(lst), dtype=float)
        slope = float(np.polyfit(x, lst, 1)[0])
        # Convert from per-sample to per-day (10s sample = 8640/day)
        return max(0.0, -slope * 8640.0)

    def to_feature_vector(self) -> np.ndarray:
        """Build a maintenance feature vector from current accumulated state."""
        return build_feature_vector(
            runtime_hours_since_service = self.runtime_hours_since_service,
            anomaly_score_latest        = self.anomaly_score_latest,
            anomaly_events_7d           = self.anomaly_events_7d,
            anomaly_events_30d          = self.anomaly_events_30d,
            vibration_trend_7d          = self._mean(self.vibration_window, 3.0),
            vibration_std_7d            = self._std(self.vibration_window, 0.5),
            oil_pressure_trend_7d       = self._mean(self.oil_pressure_window, 4.5),
            oil_pressure_drop_rate      = self._drop_rate(self.oil_pressure_window),
            coolant_temp_trend_7d       = self._mean(self.coolant_temp_window, 85.0),
            coolant_temp_max_7d         = self._max(self.coolant_temp_window, 92.0),
            power_output_trend_7d       = self._mean(self.power_output_window, 100.0),
            power_variance_7d           = self._std(self.power_output_window, 10.0) ** 2,
            fuel_consumption_trend_7d   = self._mean(self.fuel_consumption_window, 15.0),
            runtime_hours_total         = self.runtime_hours_total,
            days_since_last_maintenance = self.days_since_last_maintenance,
        )

    def to_feature_dict(self) -> Dict[str, float]:
        """Return a dict of raw (un-normalised) feature values for diagnostics."""
        return {
            "runtime_hours_since_service": self.runtime_hours_since_service,
            "anomaly_score_latest":        self.anomaly_score_latest,
            "anomaly_events_7d":           float(self.anomaly_events_7d),
            "anomaly_events_30d":          float(self.anomaly_events_30d),
            "vibration_trend_7d":          self._mean(self.vibration_window, 3.0),
            "vibration_std_7d":            self._std(self.vibration_window, 0.5),
            "oil_pressure_trend_7d":       self._mean(self.oil_pressure_window, 4.5),
            "oil_pressure_drop_rate":      self._drop_rate(self.oil_pressure_window),
            "coolant_temp_trend_7d":       self._mean(self.coolant_temp_window, 85.0),
            "coolant_temp_max_7d":         self._max(self.coolant_temp_window, 92.0),
            "power_output_trend_7d":       self._mean(self.power_output_window, 100.0),
            "power_variance_7d":           self._std(self.power_output_window, 10.0) ** 2,
            "fuel_consumption_trend_7d":   self._mean(self.fuel_consumption_window, 15.0),
            "runtime_hours_total":         self.runtime_hours_total,
            "days_since_last_maintenance": self.days_since_last_maintenance,
        }

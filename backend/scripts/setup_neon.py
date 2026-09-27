#!/usr/bin/env python3
"""
VajraX — Neon Database Bootstrap Script
========================================
Runs Alembic migrations against both Neon databases (edge + cloud) and
verifies that every expected table is present and populated with seed data.

Usage
-----
    # From project root, with .env loaded:
    python scripts/setup_neon.py

    # Verify-only mode (no migrations, just check tables):
    python scripts/setup_neon.py --verify-only

Prerequisites
-------------
    pip install python-dotenv alembic sqlalchemy psycopg2-binary asyncpg

Environment variables required (in .env or shell):
    CLOUD_DATABASE_URL  — Neon cloud DB connection string
    EDGE_DATABASE_URL   — Neon edge DB connection string
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Load .env from project root before importing anything that reads env vars
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(_PROJECT_ROOT / ".env", override=False)
except ImportError:
    # python-dotenv not installed; assume env vars are already set in shell
    pass


# ---------------------------------------------------------------------------
# Colours for terminal output
# ---------------------------------------------------------------------------
_GREEN = "\033[92m"
_RED = "\033[91m"
_YELLOW = "\033[93m"
_CYAN = "\033[96m"
_BOLD = "\033[1m"
_RESET = "\033[0m"

def ok(msg: str) -> None:
    print(f"  {_GREEN}✓{_RESET} {msg}")

def fail(msg: str) -> None:
    print(f"  {_RED}✗{_RESET} {msg}")

def info(msg: str) -> None:
    print(f"  {_CYAN}→{_RESET} {msg}")

def header(msg: str) -> None:
    print(f"\n{_BOLD}{_CYAN}{msg}{_RESET}")


# ---------------------------------------------------------------------------
# Expected tables per database
# ---------------------------------------------------------------------------
EDGE_TABLES = [
    "sensor_readings",
    "alerts",
    "outbound_queue",
    "black_box_frames",
    "inventory_items",
    "asset_cache",
    "audit_log",
    "link_status_log",
]

CLOUD_TABLES = [
    "sensor_readings",
    "alerts",
    "black_box_frames",
    "inventory_items",
    "audit_log",
    "link_status_log",
    "assets",
    "maintenance_events",
    "resupply_manifests",
    "resupply_line_items",
    "ai_predictions",
    "station_connections",
    "station_config",
    "users",
    "roles",
    "user_roles",
]

CLOUD_SEED_CHECKS = [
    # (table, expected_min_rows, description)
    ("roles", 4, "ADMIN / OPERATOR / STATION_CREW / VIEWER"),
    ("station_connections", 2, "maitri + bharati"),
    ("assets", 16, "8 assets per station"),
    ("users", 1, "admin user"),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sync_url(async_url: str) -> str:
    """Convert asyncpg URL to psycopg2-compatible URL for Alembic."""
    url = async_url
    url = url.replace("postgresql+asyncpg://", "postgresql://")
    url = url.replace("postgres+asyncpg://", "postgresql://")
    return url


def _check_env() -> tuple[str, str]:
    """Return (cloud_url, edge_url) or exit with a clear error."""
    cloud_url = os.environ.get("CLOUD_DATABASE_URL") or os.environ.get("DATABASE_URL")
    edge_url = os.environ.get("EDGE_DATABASE_URL") or os.environ.get("DATABASE_URL")

    missing = []
    if not cloud_url:
        missing.append("CLOUD_DATABASE_URL")
    if not edge_url:
        missing.append("EDGE_DATABASE_URL")

    if missing:
        print(
            f"\n{_RED}Error:{_RESET} The following environment variables are not set:\n"
            + "\n".join(f"  • {v}" for v in missing)
            + f"\n\nAdd them to your {_BOLD}.env{_RESET} file and try again.\n"
            + "Example:\n"
            + "  CLOUD_DATABASE_URL=postgresql+asyncpg://user:pass@ep-xxx.neon.tech/vajrax_cloud?sslmode=require\n"
            + "  EDGE_DATABASE_URL=postgresql+asyncpg://user:pass@ep-xxx.neon.tech/vajrax_edge?sslmode=require\n"
        )
        sys.exit(1)

    return cloud_url, edge_url  # type: ignore[return-value]


def _run_alembic(migration_target: str, db_url: str) -> bool:
    """Run `alembic upgrade head` for the given target.  Returns True on success."""
    env = {
        **os.environ,
        "MIGRATION_TARGET": migration_target,
        # Pass the *async* URL; env.py strips asyncpg for alembic
        "CLOUD_DATABASE_URL" if migration_target == "cloud" else "EDGE_DATABASE_URL": db_url,
        "PYTHONPATH": str(_PROJECT_ROOT),
    }
    result = subprocess.run(
        [
            sys.executable, "-m", "alembic",
            "-c", str(_PROJECT_ROOT / "shared" / "db" / "alembic.ini"),
            "upgrade", "head",
        ],
        env=env,
        capture_output=True,
        text=True,
        cwd=str(_PROJECT_ROOT),
    )
    if result.returncode != 0:
        print(result.stderr)
        return False
    return True


def _verify_tables(db_url: str, expected_tables: list[str], label: str) -> bool:
    """Connect and verify all expected tables exist. Returns True if all found."""
    import sqlalchemy as sa

    sync_url = _sync_url(db_url)
    engine = sa.create_engine(sync_url, pool_pre_ping=True)
    all_ok = True
    try:
        with engine.connect() as conn:
            for table in expected_tables:
                result = conn.execute(
                    sa.text(
                        "SELECT EXISTS ("
                        "  SELECT 1 FROM information_schema.tables "
                        "  WHERE table_schema = 'public' AND table_name = :t"
                        ")"
                    ),
                    {"t": table},
                )
                exists = result.scalar()
                if exists:
                    ok(f"[{label}] {table}")
                else:
                    fail(f"[{label}] {table}  ← MISSING")
                    all_ok = False
    finally:
        engine.dispose()
    return all_ok


def _verify_seed(cloud_url: str) -> bool:
    """Verify seed data exists in the cloud database. Returns True if all pass."""
    import sqlalchemy as sa

    sync_url = _sync_url(cloud_url)
    engine = sa.create_engine(sync_url, pool_pre_ping=True)
    all_ok = True
    try:
        with engine.connect() as conn:
            for table, min_rows, description in CLOUD_SEED_CHECKS:
                result = conn.execute(sa.text(f"SELECT COUNT(*) FROM {table}"))
                count = result.scalar() or 0
                if count >= min_rows:
                    ok(f"[cloud seed] {table}: {count} rows ({description})")
                else:
                    fail(
                        f"[cloud seed] {table}: {count} rows "
                        f"(expected ≥ {min_rows} — {description})"
                    )
                    all_ok = False
    finally:
        engine.dispose()
    return all_ok


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="VajraX Neon Database Bootstrap"
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Skip migrations; only verify that tables and seed data exist.",
    )
    args = parser.parse_args()

    print(f"\n{_BOLD}VajraX — Neon Database Setup{_RESET}")
    print("=" * 50)

    cloud_url, edge_url = _check_env()

    # Mask credentials in display
    def _safe(url: str) -> str:
        return url.split("@")[-1] if "@" in url else url

    info(f"Cloud DB: {_safe(cloud_url)}")
    info(f"Edge  DB: {_safe(edge_url)}")

    success = True

    if not args.verify_only:
        # ---- Run edge migration ----
        header("1/4  Running Edge migrations…")
        if _run_alembic("edge", edge_url):
            ok("Edge migrations applied successfully")
        else:
            fail("Edge migrations FAILED — check the output above")
            success = False

        # ---- Run cloud migration ----
        header("2/4  Running Cloud migrations…")
        if _run_alembic("cloud", cloud_url):
            ok("Cloud migrations applied successfully")
        else:
            fail("Cloud migrations FAILED — check the output above")
            success = False

    # ---- Verify edge tables ----
    header("3/4  Verifying Edge tables…")
    if not _verify_tables(edge_url, EDGE_TABLES, "edge"):
        success = False

    # ---- Verify cloud tables + seed ----
    header("4/4  Verifying Cloud tables and seed data…")
    if not _verify_tables(cloud_url, CLOUD_TABLES, "cloud"):
        success = False
    if not _verify_seed(cloud_url):
        success = False

    # ---- Summary ----
    print("\n" + "=" * 50)
    if success:
        print(f"{_GREEN}{_BOLD}✓ All checks passed.{_RESET}")
        print(
            f"\nNext steps:\n"
            f"  1. Start the Cloud backend:  {_CYAN}uvicorn cloud.main:app --port 8200 --reload{_RESET}\n"
            f"  2. Start the Edge backend:   {_CYAN}STATION_ID=maitri uvicorn edge.main:app --port 8100 --reload{_RESET}\n"
        )
    else:
        print(f"{_RED}{_BOLD}✗ Some checks failed. Review the output above.{_RESET}")
        sys.exit(1)


if __name__ == "__main__":
    main()

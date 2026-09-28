"""Alert ID generation for VajraX.

Alert IDs are used as de-duplication keys across the Edge and Cloud.
They are designed to be:
  - Globally unique across both stations
  - Lexicographically sortable by creation time
  - Human-readable for incident review

Format: {station_id}-{domain}-{unix_ms}-{rand_4hex}
Example: maitri-energy-1724745600000-a3f1
"""
from __future__ import annotations

import secrets

from shared.utils.time import utcnow, unix_ms


def generate_alert_id(station_id: str, domain: str) -> str:
    """Generate a unique, sortable alert ID.

    Args:
        station_id: The station identifier ("maitri" | "bharati").
        domain: The alert domain ("energy", "weather", "environment", etc.).

    Returns:
        A string of the form "{station_id}-{domain}-{unix_ms}-{rand_4hex}".
    """
    ts_ms = unix_ms(utcnow())
    rand_hex = secrets.token_hex(4)  # 8 hex characters — collision prob < 1 in 2^32
    return f"{station_id}-{domain}-{ts_ms}-{rand_hex}"


def parse_alert_id(alert_id: str) -> dict[str, str | int]:
    """Parse an alert_id back into its component parts.

    Returns:
        dict with keys: station_id, domain, unix_ms (int), rand_hex.

    Raises:
        ValueError: if the alert_id does not match the expected format.
    """
    parts = alert_id.split("-")
    if len(parts) < 4:
        raise ValueError(f"Invalid alert_id format: {alert_id!r}")
    # station_id may contain no dashes; domain is single word; unix_ms and rand are last two
    rand_hex = parts[-1]
    ts_ms_str = parts[-2]
    domain = parts[-3]
    station_id = "-".join(parts[:-3])
    try:
        ts_ms = int(ts_ms_str)
    except ValueError as exc:
        raise ValueError(f"Invalid alert_id (bad unix_ms): {alert_id!r}") from exc
    return {
        "station_id": station_id,
        "domain": domain,
        "unix_ms": ts_ms,
        "rand_hex": rand_hex,
    }

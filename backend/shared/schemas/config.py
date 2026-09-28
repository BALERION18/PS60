"""Pydantic schema for station configuration YAML files."""
from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class StationId(str, Enum):
    MAITRI = "maitri"
    BHARATI = "bharati"


class SensorQuality(str, Enum):
    NOMINAL = "NOMINAL"
    DEGRADED = "DEGRADED"
    STALE = "STALE"
    SENSOR_FAULT = "SENSOR_FAULT"


class AlertSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Domain(str, Enum):
    ENERGY = "energy"
    WEATHER = "weather"
    ENVIRONMENT = "environment"
    INFRASTRUCTURE = "infrastructure"
    LOGISTICS = "logistics"
    NETWORK = "network"


class SensorConfig(BaseModel):
    """Configuration for a single sensor on a station."""
    sensor_id: str = Field(..., description="Unique sensor identifier: {station_id}.{domain}.{asset_id}.{metric}")
    domain: Domain
    asset_id: Optional[str] = None
    metric_name: str
    unit: str
    sampling_interval_s: int = Field(..., ge=1, description="Expected readings interval in seconds")
    nominal_min: Optional[float] = None
    nominal_max: Optional[float] = None


class ThresholdRule(BaseModel):
    """A single threshold alert rule."""
    sensor_id: str
    metric_name: str
    condition: str = Field(..., description="Comparison: 'lt', 'lte', 'gt', 'gte', 'eq', 'neq'")
    threshold_value: float
    severity: AlertSeverity
    description_template: str = Field(..., description="Alert description, may use {value} and {threshold}")

    @field_validator("condition")
    @classmethod
    def validate_condition(cls, v: str) -> str:
        allowed = {"lt", "lte", "gt", "gte", "eq", "neq"}
        if v not in allowed:
            raise ValueError(f"condition must be one of {allowed}, got '{v}'")
        return v


class RateOfChangeRule(BaseModel):
    """Alert if a sensor value changes faster than max_rate_per_minute."""
    sensor_id: str
    max_rate_per_minute: float
    severity: AlertSeverity
    description_template: str


class CompositeRule(BaseModel):
    """Multi-sensor composite alert rule."""
    rule_id: str
    description: str
    condition_expression: str = Field(..., description="Python-safe expression using sensor_id references")
    severity: AlertSeverity
    description_template: str


class BlackBoxConfig(BaseModel):
    """Configuration for black-box event capture."""
    trigger_severities: List[AlertSeverity] = Field(default=[AlertSeverity.CRITICAL])
    pre_event_window_s: int = Field(default=300, description="Seconds of pre-event history to capture")
    post_resolution_tail_s: int = Field(default=900, description="Seconds of post-resolution tail")


class SyncConfig(BaseModel):
    """Outbound sync configuration."""
    heartbeat_interval_s: int = Field(default=60)
    telemetry_batch_window_s: Dict[Domain, int] = Field(
        default_factory=lambda: {
            Domain.ENERGY: 300,       # 5 min
            Domain.WEATHER: 900,      # 15 min
            Domain.ENVIRONMENT: 900,  # 15 min
        }
    )
    max_queue_size_bytes: int = Field(default=1_073_741_824, description="1 GB")
    queue_retention_days: int = Field(default=30)
    # Priority: 0 = black-box (never evict), 1 = CRITICAL/HIGH alerts, 2 = MEDIUM/LOW, 3 = telemetry
    priority_map: Dict[str, int] = Field(
        default_factory=lambda: {
            "black_box": 0,
            "alert_critical": 1,
            "alert_high": 1,
            "alert_medium": 2,
            "alert_low": 2,
            "telemetry": 3,
        }
    )


class StationConfig(BaseModel):
    """Root configuration schema for a VajraX station instance."""
    station_id: StationId
    display_name: str
    location: str
    latitude: float
    longitude: float
    elevation_m: float
    timezone: str = Field(default="UTC")

    sensors: List[SensorConfig]
    threshold_rules: List[ThresholdRule]
    rate_of_change_rules: List[RateOfChangeRule] = Field(default_factory=list)
    composite_rules: List[CompositeRule] = Field(default_factory=list)

    black_box: BlackBoxConfig = Field(default_factory=BlackBoxConfig)
    sync: SyncConfig = Field(default_factory=SyncConfig)

    # Station-specific link-health config
    heartbeat_timeout_minutes: int = Field(default=15)

    # Pre-provisioned API keys for offline local auth.
    # Format: "ROLE.hex_secret" — see edge/auth/local_auth.py for details.
    local_api_keys: List[str] = Field(default_factory=list)


    @classmethod
    def from_yaml(cls, path: str) -> "StationConfig":
        """Load and validate a station config from a YAML file."""
        import yaml  # type: ignore
        with open(path, "r") as f:
            data = yaml.safe_load(f)
        return cls.model_validate(data)

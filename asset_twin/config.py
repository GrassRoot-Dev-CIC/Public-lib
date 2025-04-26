"""
Configuration for asset twin thresholds and behavior.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class MaintenanceThresholds:
    """
    Thresholds for predictive maintenance rules.
    
    Attributes:
        flow_degradation_ratio: Minimum flow as fraction of rated flow (0.0 to 1.0).
                                If avg flow drops below this, maintenance is needed.
        temperature_margin_celsius: Safety margin below failure temperature.
                                    If temp exceeds (failure_temp - margin), flag for maintenance.
        min_data_points: Minimum telemetry points required to make a prediction.
        evaluation_window_days: Number of days of historical data to consider.
    """
    flow_degradation_ratio: float = 0.8
    temperature_margin_celsius: float = 5.0
    min_data_points: int = 20
    evaluation_window_days: int = 7

    def __post_init__(self):
        """Validate threshold values."""
        if not 0.0 <= self.flow_degradation_ratio <= 1.0:
            raise ValueError(
                f"flow_degradation_ratio must be in [0.0, 1.0], got {self.flow_degradation_ratio}"
            )
        if self.temperature_margin_celsius < 0:
            raise ValueError(
                f"temperature_margin_celsius cannot be negative, got {self.temperature_margin_celsius}"
            )
        if self.min_data_points < 1:
            raise ValueError(
                f"min_data_points must be >= 1, got {self.min_data_points}"
            )
        if self.evaluation_window_days < 1:
            raise ValueError(
                f"evaluation_window_days must be >= 1, got {self.evaluation_window_days}"
            )


@dataclass
class TwinConfig:
    """
    Configuration for an asset twin.
    
    Attributes:
        asset_id: Unique identifier for the physical asset.
        asset_type: Type of asset (e.g., "pump", "hvac", "chiller").
        rated_flow: Expected normal operating flow rate.
        failure_temperature: Temperature at which asset is expected to fail or shut down.
        thresholds: Maintenance prediction thresholds.
        location: Optional physical location description.
    """
    asset_id: str
    asset_type: str
    rated_flow: float
    failure_temperature: float
    thresholds: Optional[MaintenanceThresholds] = None
    location: Optional[str] = None

    def __post_init__(self):
        """Set default thresholds if not provided."""
        if self.thresholds is None:
            self.thresholds = MaintenanceThresholds()
        
        if not self.asset_id:
            raise ValueError("asset_id cannot be empty")
        if self.rated_flow <= 0:
            raise ValueError(f"rated_flow must be positive, got {self.rated_flow}")




"""
Telemetry data model for asset twins.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class TelemetryPoint:
    """
    Single telemetry measurement from an asset.
    
    Attributes:
        timestamp: When the measurement was taken (UTC).
        flow: Flow rate measurement (units depend on asset type, e.g., L/min, m³/h).
        temperature: Temperature measurement (degrees Celsius).
        pressure: Optional pressure measurement (units depend on asset type).
        metadata: Optional additional sensor data.
    """
    timestamp: datetime
    flow: float
    temperature: float
    pressure: Optional[float] = None
    metadata: Optional[dict] = None

    def __post_init__(self):
        """Validate telemetry values."""
        if self.flow < 0:
            raise ValueError(f"Flow cannot be negative, got {self.flow}")
        # Temperature can be negative in some contexts, but sanity check
        if self.temperature < -100 or self.temperature > 200:
            raise ValueError(f"Temperature out of reasonable range: {self.temperature}°C")



"""
Digital twin implementation for building asset predictive maintenance.

This module implements a rule-based digital twin for physical building assets
(pumps, HVAC systems, etc.) targeting SME property management. The innovation
is bringing IoT-style predictive maintenance to a market typically underserved
by enterprise solutions.

Core Innovation:
    - Rule engine pattern: Domain experts can encode maintenance logic without
      code changes by implementing MaintenanceRule interface
    - Configurable thresholds: Equipment-specific parameters (rated flow,
      temperature limits) externalized from rule logic
    - Temporal analysis: Flow degradation calculated over configurable time
      windows to detect gradual performance decline

Typical Usage:
    >>> from asset_twin import AssetTwin, TwinConfig
    >>> config = TwinConfig(asset_id="PUMP-001", rated_flow_lpm=100.0)
    >>> twin = AssetTwin(config)
    >>> twin.add_telemetry_reading(timestamp=datetime.utcnow(), flow=95.0, temperature=70.0)
    >>> if twin.needs_maintenance():
    ...     assessment = twin.get_maintenance_assessment()

Classes:
    AssetTwin: Main digital twin class managing telemetry and maintenance assessment

Related Modules:
    config: TwinConfig dataclass for asset parameters and thresholds
    telemetry: TelemetryPoint dataclass for sensor readings
    rules: RuleEngine and built-in MaintenanceRule implementations
"""

from datetime import datetime
from typing import List, Optional

from .config import TwinConfig
from .telemetry import TelemetryPoint
from .rules import RuleEngine, RuleResult


class AssetTwin:
    """
    Digital twin for a physical building asset (pump, HVAC, etc.).
    
    Maintains telemetry history and provides predictive maintenance
    assessments based on configurable rules.
    """

    def __init__(self, config: TwinConfig, rule_engine: Optional[RuleEngine] = None):
        """
        Initialize asset twin.
        
        Args:
            config: Configuration including asset ID, thresholds, and rated specs.
            rule_engine: Optional custom rule engine. Uses default if not provided.
        """
        self.config = config
        self.rule_engine = rule_engine or RuleEngine()
        self.telemetry: List[TelemetryPoint] = []

    @property
    def asset_id(self) -> str:
        """Return asset ID for convenience."""
        return self.config.asset_id

    def add_telemetry(self, point: TelemetryPoint) -> None:
        """
        Add a telemetry measurement to the twin's history.
        
        Args:
            point: TelemetryPoint with flow, temperature, etc.
        """
        self.telemetry.append(point)
        # Keep telemetry sorted by timestamp
        self.telemetry.sort(key=lambda t: t.timestamp)

    def add_telemetry_reading(
        self,
        timestamp: datetime,
        flow: float,
        temperature: float,
        pressure: Optional[float] = None,
    ) -> None:
        """
        Convenience method to add telemetry without creating TelemetryPoint explicitly.
        
        Args:
            timestamp: When measurement was taken.
            flow: Flow rate measurement.
            temperature: Temperature measurement.
            pressure: Optional pressure measurement.
        """
        point = TelemetryPoint(
            timestamp=timestamp,
            flow=flow,
            temperature=temperature,
            pressure=pressure,
        )
        self.add_telemetry(point)

    def needs_maintenance(self) -> bool:
        """
        Determine if asset needs maintenance based on current telemetry.
        
        Returns:
            True if any rule indicates maintenance is needed.
        """
        return self.rule_engine.needs_maintenance(self.config, self.telemetry)

    def get_maintenance_assessment(self) -> List[RuleResult]:
        """
        Get detailed assessment from all rules.
        
        Returns:
            List of RuleResult with reasons and triggered values.
        """
        return self.rule_engine.evaluate(self.config, self.telemetry)

    def get_telemetry_count(self) -> int:
        """Return number of telemetry points stored."""
        return len(self.telemetry)

    def get_latest_telemetry(self) -> Optional[TelemetryPoint]:
        """Return most recent telemetry point, or None if no data."""
        if not self.telemetry:
            return None
        return self.telemetry[-1]

    def clear_telemetry(self) -> None:
        """Remove all telemetry data (useful for testing or data retention policies)."""
        self.telemetry.clear()

    def __repr__(self) -> str:
        return (
            f"AssetTwin(asset_id='{self.asset_id}', "
            f"type='{self.config.asset_type}', "
            f"telemetry_points={len(self.telemetry)})"
        )









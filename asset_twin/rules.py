"""
Rule engine for predictive maintenance decisions.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional

from .telemetry import TelemetryPoint
from .config import TwinConfig


@dataclass
class RuleResult:
    """
    Result of evaluating a maintenance rule.
    
    Attributes:
        needs_maintenance: True if maintenance is recommended.
        reason: Human-readable explanation of why maintenance is needed.
        confidence: Confidence level (0.0 to 1.0) in the prediction.
        triggered_values: Specific values that triggered the rule (for debugging).
    """
    needs_maintenance: bool
    reason: str
    confidence: float = 1.0
    triggered_values: Optional[dict] = None


class MaintenanceRule(ABC):
    """
    Abstract base class for maintenance prediction rules.
    """

    @abstractmethod
    def evaluate(
        self,
        config: TwinConfig,
        telemetry: List[TelemetryPoint],
    ) -> RuleResult:
        """
        Evaluate whether maintenance is needed based on telemetry.
        
        Args:
            config: Asset twin configuration with thresholds.
            telemetry: Historical telemetry points (ordered by timestamp).
            
        Returns:
            RuleResult indicating whether maintenance is needed and why.
        """
        pass

    @property
    def name(self) -> str:
        """Return rule name for logging and reporting."""
        return self.__class__.__name__


class FlowDegradationRule(MaintenanceRule):
    """
    Rule that checks for flow degradation below rated capacity.
    
    Triggers maintenance if average flow over the evaluation window
    drops below the configured threshold.
    """

    def evaluate(
        self,
        config: TwinConfig,
        telemetry: List[TelemetryPoint],
    ) -> RuleResult:
        """Check if flow has degraded below acceptable levels."""
        thresholds = config.thresholds
        assert thresholds is not None  # Guaranteed by TwinConfig.__post_init__

        cutoff = datetime.utcnow() - timedelta(days=thresholds.evaluation_window_days)
        window = [t for t in telemetry if t.timestamp >= cutoff]

        if len(window) < thresholds.min_data_points:
            return RuleResult(
                needs_maintenance=False,
                reason=f"Insufficient data: {len(window)} points (need {thresholds.min_data_points})",
                confidence=0.0,
            )

        avg_flow = sum(t.flow for t in window) / len(window)
        threshold_flow = thresholds.flow_degradation_ratio * config.rated_flow

        if avg_flow < threshold_flow:
            return RuleResult(
                needs_maintenance=True,
                reason=f"Flow degradation detected: avg={avg_flow:.2f}, "
                       f"threshold={threshold_flow:.2f} ({thresholds.flow_degradation_ratio*100}% of rated)",
                confidence=0.9,
                triggered_values={
                    "avg_flow": avg_flow,
                    "threshold_flow": threshold_flow,
                    "rated_flow": config.rated_flow,
                    "data_points": len(window),
                },
            )

        return RuleResult(
            needs_maintenance=False,
            reason=f"Flow normal: avg={avg_flow:.2f} >= threshold={threshold_flow:.2f}",
        )


class TemperatureExcursionRule(MaintenanceRule):
    """
    Rule that checks for temperature approaching failure threshold.
    
    Triggers maintenance if maximum temperature over the evaluation window
    exceeds (failure_temperature - margin).
    """

    def evaluate(
        self,
        config: TwinConfig,
        telemetry: List[TelemetryPoint],
    ) -> RuleResult:
        """Check if temperature is approaching failure levels."""
        thresholds = config.thresholds
        assert thresholds is not None

        cutoff = datetime.utcnow() - timedelta(days=thresholds.evaluation_window_days)
        window = [t for t in telemetry if t.timestamp >= cutoff]

        if len(window) < thresholds.min_data_points:
            return RuleResult(
                needs_maintenance=False,
                reason=f"Insufficient data: {len(window)} points (need {thresholds.min_data_points})",
                confidence=0.0,
            )

        max_temp = max(t.temperature for t in window)
        threshold_temp = config.failure_temperature - thresholds.temperature_margin_celsius

        if max_temp > threshold_temp:
            return RuleResult(
                needs_maintenance=True,
                reason=f"Temperature excursion detected: max={max_temp:.1f}°C, "
                       f"threshold={threshold_temp:.1f}°C (failure at {config.failure_temperature}°C)",
                confidence=0.85,
                triggered_values={
                    "max_temperature": max_temp,
                    "threshold_temperature": threshold_temp,
                    "failure_temperature": config.failure_temperature,
                    "data_points": len(window),
                },
            )

        return RuleResult(
            needs_maintenance=False,
            reason=f"Temperature normal: max={max_temp:.1f}°C <= threshold={threshold_temp:.1f}°C",
        )


class RuleEngine:
    """
    Orchestrates evaluation of multiple maintenance rules.
    
    Runs all registered rules and aggregates results to determine
    if maintenance is needed.
    """

    def __init__(self, rules: Optional[List[MaintenanceRule]] = None):
        """
        Initialize rule engine.
        
        Args:
            rules: List of MaintenanceRule instances. Uses default rules if None.
        """
        if rules is None:
            # Default rule set
            self.rules = [
                FlowDegradationRule(),
                TemperatureExcursionRule(),
            ]
        else:
            self.rules = rules

    def evaluate(
        self,
        config: TwinConfig,
        telemetry: List[TelemetryPoint],
    ) -> List[RuleResult]:
        """
        Evaluate all rules against telemetry data.
        
        Args:
            config: Asset twin configuration.
            telemetry: Historical telemetry points.
            
        Returns:
            List of RuleResult, one per rule.
        """
        results = []
        for rule in self.rules:
            result = rule.evaluate(config, telemetry)
            results.append(result)
        return results

    def needs_maintenance(
        self,
        config: TwinConfig,
        telemetry: List[TelemetryPoint],
    ) -> bool:
        """
        Determine if maintenance is needed based on any rule triggering.
        
        Returns True if at least one rule indicates maintenance is needed.
        """
        results = self.evaluate(config, telemetry)
        return any(r.needs_maintenance for r in results)

    def add_rule(self, rule: MaintenanceRule) -> None:
        """Add a new rule to the engine."""
        self.rules.append(rule)

    def remove_rule(self, rule_class_name: str) -> None:
        """Remove a rule by class name."""
        self.rules = [r for r in self.rules if r.__class__.__name__ != rule_class_name]










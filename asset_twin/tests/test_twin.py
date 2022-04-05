"""
Unit tests for asset twin digital twin library.
"""

import pytest
from datetime import datetime, timedelta

from asset_twin import (
    AssetTwin,
    TwinConfig,
    MaintenanceThresholds,
    TelemetryPoint,
    RuleEngine,
)
from asset_twin.rules import FlowDegradationRule, TemperatureExcursionRule


# Fixtures
@pytest.fixture
def basic_config():
    """Standard asset configuration for testing."""
    return TwinConfig(
        asset_id="PUMP-001",
        asset_type="pump",
        rated_flow=100.0,
        failure_temperature=85.0,
        thresholds=MaintenanceThresholds(
            flow_degradation_ratio=0.8,
            temperature_margin_celsius=5.0,
            min_data_points=20,
            evaluation_window_days=7,
        ),
        location="Building A - Basement",
    )


@pytest.fixture
def sample_telemetry():
    """Generate sample normal telemetry over 7 days."""
    points = []
    base_time = datetime.utcnow() - timedelta(days=7)
    
    for i in range(30):
        points.append(
            TelemetryPoint(
                timestamp=base_time + timedelta(hours=i * 6),
                flow=95.0 + (i % 5),  # Normal flow around 95-99
                temperature=65.0 + (i % 3),  # Normal temp around 65-67
            )
        )
    return points


# Test TelemetryPoint
class TestTelemetryPoint:
    def test_valid_telemetry(self):
        """Valid telemetry point should be created."""
        point = TelemetryPoint(
            timestamp=datetime.utcnow(),
            flow=50.0,
            temperature=70.0,
        )
        assert point.flow == 50.0
        assert point.temperature == 70.0

    def test_negative_flow_rejected(self):
        """Negative flow should raise ValueError."""
        with pytest.raises(ValueError, match="Flow cannot be negative"):
            TelemetryPoint(
                timestamp=datetime.utcnow(),
                flow=-10.0,
                temperature=70.0,
            )

    def test_extreme_temperature_rejected(self):
        """Unreasonable temperature should raise ValueError."""
        with pytest.raises(ValueError, match="Temperature out of reasonable range"):
            TelemetryPoint(
                timestamp=datetime.utcnow(),
                flow=50.0,
                temperature=500.0,
            )


# Test Configuration
class TestTwinConfig:
    def test_default_thresholds_created(self):
        """Config without explicit thresholds should use defaults."""
        config = TwinConfig(
            asset_id="TEST-001",
            asset_type="pump",
            rated_flow=100.0,
            failure_temperature=80.0,
        )
        assert config.thresholds is not None
        assert config.thresholds.flow_degradation_ratio == 0.8

    def test_custom_thresholds(self):
        """Config with custom thresholds should preserve them."""
        thresholds = MaintenanceThresholds(
            flow_degradation_ratio=0.9,
            temperature_margin_celsius=10.0,
            min_data_points=50,
            evaluation_window_days=14,
        )
        config = TwinConfig(
            asset_id="TEST-001",
            asset_type="hvac",
            rated_flow=200.0,
            failure_temperature=90.0,
            thresholds=thresholds,
        )
        assert config.thresholds.flow_degradation_ratio == 0.9
        assert config.thresholds.evaluation_window_days == 14

    def test_invalid_flow_degradation_ratio(self):
        """Invalid ratio should raise ValueError."""
        with pytest.raises(ValueError, match="flow_degradation_ratio must be in"):
            MaintenanceThresholds(flow_degradation_ratio=1.5)

    def test_empty_asset_id_rejected(self):
        """Empty asset ID should raise ValueError."""
        with pytest.raises(ValueError, match="asset_id cannot be empty"):
            TwinConfig(
                asset_id="",
                asset_type="pump",
                rated_flow=100.0,
                failure_temperature=80.0,
            )

    def test_negative_rated_flow_rejected(self):
        """Negative rated flow should raise ValueError."""
        with pytest.raises(ValueError, match="rated_flow must be positive"):
            TwinConfig(
                asset_id="TEST",
                asset_type="pump",
                rated_flow=-50.0,
                failure_temperature=80.0,
            )


# Test AssetTwin
class TestAssetTwin:
    def test_create_twin(self, basic_config):
        """Should create twin with config."""
        twin = AssetTwin(basic_config)
        assert twin.asset_id == "PUMP-001"
        assert twin.get_telemetry_count() == 0

    def test_add_telemetry_point(self, basic_config):
        """Should add telemetry point."""
        twin = AssetTwin(basic_config)
        point = TelemetryPoint(
            timestamp=datetime.utcnow(),
            flow=90.0,
            temperature=70.0,
        )
        twin.add_telemetry(point)
        assert twin.get_telemetry_count() == 1

    def test_add_telemetry_reading_convenience(self, basic_config):
        """Convenience method should create and add telemetry."""
        twin = AssetTwin(basic_config)
        twin.add_telemetry_reading(
            timestamp=datetime.utcnow(),
            flow=85.0,
            temperature=68.0,
        )
        assert twin.get_telemetry_count() == 1
        latest = twin.get_latest_telemetry()
        assert latest is not None
        assert latest.flow == 85.0

    def test_telemetry_sorted_by_timestamp(self, basic_config):
        """Telemetry should be kept sorted by timestamp."""
        twin = AssetTwin(basic_config)
        now = datetime.utcnow()
        
        # Add out of order
        twin.add_telemetry_reading(now + timedelta(hours=2), 90.0, 70.0)
        twin.add_telemetry_reading(now, 85.0, 65.0)
        twin.add_telemetry_reading(now + timedelta(hours=1), 88.0, 68.0)
        
        # Should be sorted
        assert twin.telemetry[0].flow == 85.0
        assert twin.telemetry[1].flow == 88.0
        assert twin.telemetry[2].flow == 90.0

    def test_get_latest_telemetry(self, basic_config, sample_telemetry):
        """Should return most recent telemetry point."""
        twin = AssetTwin(basic_config)
        for point in sample_telemetry:
            twin.add_telemetry(point)
        
        latest = twin.get_latest_telemetry()
        assert latest == sample_telemetry[-1]

    def test_get_latest_telemetry_empty(self, basic_config):
        """Should return None when no telemetry."""
        twin = AssetTwin(basic_config)
        assert twin.get_latest_telemetry() is None

    def test_clear_telemetry(self, basic_config, sample_telemetry):
        """Should remove all telemetry."""
        twin = AssetTwin(basic_config)
        for point in sample_telemetry:
            twin.add_telemetry(point)
        
        twin.clear_telemetry()
        assert twin.get_telemetry_count() == 0


# Test Rules
class TestFlowDegradationRule:
    def test_normal_flow_no_maintenance(self, basic_config):
        """Normal flow should not trigger maintenance."""
        rule = FlowDegradationRule()
        
        # Generate normal telemetry: 95-99 L/min (rated: 100, threshold: 80)
        telemetry = []
        base_time = datetime.utcnow() - timedelta(days=5)
        for i in range(30):
            telemetry.append(
                TelemetryPoint(
                    timestamp=base_time + timedelta(hours=i * 4),
                    flow=95.0 + (i % 5),
                    temperature=70.0,
                )
            )
        
        result = rule.evaluate(basic_config, telemetry)
        assert not result.needs_maintenance

    def test_degraded_flow_triggers_maintenance(self, basic_config):
        """Flow below threshold should trigger maintenance."""
        rule = FlowDegradationRule()
        
        # Generate degraded flow: 70-75 L/min (below 80% of 100)
        telemetry = []
        base_time = datetime.utcnow() - timedelta(days=5)
        for i in range(30):
            telemetry.append(
                TelemetryPoint(
                    timestamp=base_time + timedelta(hours=i * 4),
                    flow=70.0 + (i % 5),
                    temperature=70.0,
                )
            )
        
        result = rule.evaluate(basic_config, telemetry)
        assert result.needs_maintenance
        assert "Flow degradation" in result.reason
        assert result.triggered_values is not None
        assert result.triggered_values["avg_flow"] < 80.0

    def test_insufficient_data(self, basic_config):
        """Too few data points should not trigger maintenance."""
        rule = FlowDegradationRule()
        
        # Only 10 points (need 20)
        telemetry = []
        base_time = datetime.utcnow() - timedelta(days=2)
        for i in range(10):
            telemetry.append(
                TelemetryPoint(
                    timestamp=base_time + timedelta(hours=i * 4),
                    flow=50.0,  # Very low, but not enough data
                    temperature=70.0,
                )
            )
        
        result = rule.evaluate(basic_config, telemetry)
        assert not result.needs_maintenance
        assert "Insufficient data" in result.reason


class TestTemperatureExcursionRule:
    def test_normal_temperature_no_maintenance(self, basic_config):
        """Normal temperature should not trigger maintenance."""
        rule = TemperatureExcursionRule()
        
        # Temperature 65-70°C (failure: 85, threshold: 80)
        telemetry = []
        base_time = datetime.utcnow() - timedelta(days=5)
        for i in range(30):
            telemetry.append(
                TelemetryPoint(
                    timestamp=base_time + timedelta(hours=i * 4),
                    flow=95.0,
                    temperature=65.0 + (i % 5),
                )
            )
        
        result = rule.evaluate(basic_config, telemetry)
        assert not result.needs_maintenance

    def test_high_temperature_triggers_maintenance(self, basic_config):
        """Temperature above threshold should trigger maintenance."""
        rule = TemperatureExcursionRule()
        
        # Temperature spiking to 82°C (above threshold of 80)
        telemetry = []
        base_time = datetime.utcnow() - timedelta(days=5)
        for i in range(30):
            telemetry.append(
                TelemetryPoint(
                    timestamp=base_time + timedelta(hours=i * 4),
                    flow=95.0,
                    temperature=75.0 + (i % 8),  # Goes up to 82
                )
            )
        
        result = rule.evaluate(basic_config, telemetry)
        assert result.needs_maintenance
        assert "Temperature excursion" in result.reason
        assert result.triggered_values["max_temperature"] > 80.0


# Test RuleEngine
class TestRuleEngine:
    def test_default_rules_loaded(self):
        """Default rule engine should have flow and temperature rules."""
        engine = RuleEngine()
        assert len(engine.rules) == 2
        rule_names = [r.__class__.__name__ for r in engine.rules]
        assert "FlowDegradationRule" in rule_names
        assert "TemperatureExcursionRule" in rule_names

    def test_custom_rules(self):
        """Should accept custom rule list."""
        engine = RuleEngine(rules=[FlowDegradationRule()])
        assert len(engine.rules) == 1

    def test_add_rule(self):
        """Should allow adding rules dynamically."""
        engine = RuleEngine(rules=[])
        engine.add_rule(FlowDegradationRule())
        assert len(engine.rules) == 1

    def test_remove_rule(self):
        """Should allow removing rules by class name."""
        engine = RuleEngine()
        engine.remove_rule("FlowDegradationRule")
        rule_names = [r.__class__.__name__ for r in engine.rules]
        assert "FlowDegradationRule" not in rule_names

    def test_needs_maintenance_any_rule_triggers(self, basic_config):
        """Should return True if any rule indicates maintenance needed."""
        engine = RuleEngine()
        
        # Degraded flow telemetry
        telemetry = []
        base_time = datetime.utcnow() - timedelta(days=5)
        for i in range(30):
            telemetry.append(
                TelemetryPoint(
                    timestamp=base_time + timedelta(hours=i * 4),
                    flow=70.0,  # Below threshold
                    temperature=70.0,  # Normal
                )
            )
        
        assert engine.needs_maintenance(basic_config, telemetry)

    def test_evaluate_returns_all_results(self, basic_config, sample_telemetry):
        """Evaluate should return result for each rule."""
        engine = RuleEngine()
        results = engine.evaluate(basic_config, sample_telemetry)
        assert len(results) == 2


# Integration Tests
class TestAssetTwinIntegration:
    def test_normal_operation_no_maintenance(self, basic_config):
        """Twin with normal telemetry should not need maintenance."""
        twin = AssetTwin(basic_config)
        
        # Add normal telemetry
        base_time = datetime.utcnow() - timedelta(days=5)
        for i in range(30):
            twin.add_telemetry_reading(
                timestamp=base_time + timedelta(hours=i * 4),
                flow=95.0 + (i % 5),
                temperature=65.0 + (i % 3),
            )
        
        assert not twin.needs_maintenance()

    def test_degraded_flow_needs_maintenance(self, basic_config):
        """Twin with degraded flow should need maintenance."""
        twin = AssetTwin(basic_config)
        
        # Add degraded flow telemetry
        base_time = datetime.utcnow() - timedelta(days=5)
        for i in range(30):
            twin.add_telemetry_reading(
                timestamp=base_time + timedelta(hours=i * 4),
                flow=70.0,  # Below 80% of rated 100
                temperature=65.0,
            )
        
        assert twin.needs_maintenance()
        
        # Check detailed assessment
        assessment = twin.get_maintenance_assessment()
        flow_results = [r for r in assessment if "Flow" in r.reason]
        assert any(r.needs_maintenance for r in flow_results)

    def test_high_temperature_needs_maintenance(self, basic_config):
        """Twin with high temperature should need maintenance."""
        twin = AssetTwin(basic_config)
        
        # Add high temperature telemetry
        base_time = datetime.utcnow() - timedelta(days=5)
        for i in range(30):
            twin.add_telemetry_reading(
                timestamp=base_time + timedelta(hours=i * 4),
                flow=95.0,
                temperature=82.0,  # Above threshold of 80
            )
        
        assert twin.needs_maintenance()

    def test_insufficient_data_no_maintenance(self, basic_config):
        """Twin with insufficient data should not trigger maintenance."""
        twin = AssetTwin(basic_config)
        
        # Add only a few points
        base_time = datetime.utcnow()
        for i in range(5):
            twin.add_telemetry_reading(
                timestamp=base_time + timedelta(hours=i),
                flow=50.0,  # Very low, but not enough data
                temperature=90.0,  # Very high, but not enough data
            )
        
        assert not twin.needs_maintenance()

    def test_repr(self, basic_config):
        """Twin repr should contain key info."""
        twin = AssetTwin(basic_config)
        twin.add_telemetry_reading(datetime.utcnow(), 90.0, 70.0)
        
        repr_str = repr(twin)
        assert "PUMP-001" in repr_str
        assert "pump" in repr_str
        assert "1" in repr_str  # 1 telemetry point



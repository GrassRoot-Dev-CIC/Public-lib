# Asset Twin - Digital Twin for Building Assets

Predictive maintenance system for building equipment (pumps, HVAC, chillers) with telemetry tracking and rule-based analysis.

## Innovation Highlights

- **Rule Engine Architecture**: Pluggable maintenance rules enable domain experts to encode knowledge without code changes
- **SME-Focused Design**: Lightweight digital twin requiring no ML infrastructure—accessible to small facility managers
- **Temporal Analysis**: Flow degradation calculated over configurable time windows, detecting gradual performance decline
- **Active Predictions**: Generates work orders automatically when thresholds breached, shifting from reactive to predictive maintenance

## Overview

This library provides a digital twin implementation for building assets that:
- Tracks real-time telemetry (flow, temperature, pressure)
- Evaluates maintenance needs using configurable rules
- Provides clear separation between data model and rule engine
- Supports extensible rule system for custom logic
- Is fully testable with no external dependencies

## Installation

```bash
# Install from local directory
pip install -e .

# For testing
pip install pytest
```

## Quick Start

```python
from asset_twin import AssetTwin, TwinConfig, MaintenanceThresholds
from datetime import datetime, timedelta

# 1. Configure the asset twin
config = TwinConfig(
    asset_id="PUMP-A1-001",
    asset_type="pump",
    rated_flow=100.0,  # L/min
    failure_temperature=85.0,  # °C
    thresholds=MaintenanceThresholds(
        flow_degradation_ratio=0.8,  # Alert if flow < 80% of rated
        temperature_margin_celsius=5.0,  # Alert if temp > failure - 5°C
        min_data_points=20,
        evaluation_window_days=7,
    ),
    location="Building A - Basement",
)

# 2. Create twin
twin = AssetTwin(config)

# 3. Add telemetry (simulated IoT sensor data)
base_time = datetime.utcnow() - timedelta(days=7)
for hour in range(168):  # 7 days of hourly readings
    twin.add_telemetry_reading(
        timestamp=base_time + timedelta(hours=hour),
        flow=95.0,  # Normal operation
        temperature=70.0,
    )

# 4. Check if maintenance is needed
if twin.needs_maintenance():
    print("Maintenance required!")
    
    # Get detailed assessment
    assessment = twin.get_maintenance_assessment()
    for result in assessment:
        if result.needs_maintenance:
            print(f"  - {result.reason}")
            print(f"    Confidence: {result.confidence:.1%}")
else:
    print("Asset operating normally")
```

## Configuration

### TwinConfig

```python
config = TwinConfig(
    asset_id="HVAC-B2-003",
    asset_type="hvac",
    rated_flow=200.0,
    failure_temperature=90.0,
    thresholds=MaintenanceThresholds(...),
    location="Building B - Roof",
)
```

### MaintenanceThresholds

```python
thresholds = MaintenanceThresholds(
    flow_degradation_ratio=0.8,       # Trigger if avg flow < 80% of rated
    temperature_margin_celsius=5.0,   # Trigger if temp > failure_temp - 5
    min_data_points=20,                # Minimum readings needed for prediction
    evaluation_window_days=7,          # Look back 7 days
)
```

## Built-in Rules

### FlowDegradationRule

Triggers maintenance if average flow over the evaluation window drops below the configured threshold.

**Example**: If rated flow is 100 L/min and `flow_degradation_ratio=0.8`, alert if average flow < 80 L/min.

### TemperatureExcursionRule

Triggers maintenance if maximum temperature over the evaluation window exceeds `failure_temperature - temperature_margin_celsius`.

**Example**: If failure temp is 85°C and margin is 5°C, alert if max temp > 80°C.

## Custom Rules

```python
from asset_twin import MaintenanceRule, RuleResult, RuleEngine

class VibrationRule(MaintenanceRule):
    """Custom rule based on vibration sensor (hypothetical)."""
    
    def evaluate(self, config, telemetry):
        # Access vibration data from telemetry.metadata
        # For example:
        # max_vibration = max(t.metadata.get("vibration", 0) for t in telemetry)
        # if max_vibration > THRESHOLD:
        #     return RuleResult(needs_maintenance=True, reason="High vibration detected")
        
        return RuleResult(
            needs_maintenance=False,
            reason="Vibration normal",
        )

# Use custom rule
engine = RuleEngine(rules=[
    FlowDegradationRule(),
    TemperatureExcursionRule(),
    VibrationRule(),
])

twin = AssetTwin(config, rule_engine=engine)
```

## Integration with Work Order System

```python
from asset_twin import AssetTwin

def check_and_schedule_maintenance(twins, maintenance_api):
    """
    Evaluate all asset twins and create work orders for those needing maintenance.
    
    Args:
        twins: List of AssetTwin instances.
        maintenance_api: Interface to work order system (implement for your platform).
    """
    for twin in twins:
        if twin.needs_maintenance():
            assessment = twin.get_maintenance_assessment()
            
            # Build reason summary
            reasons = [r.reason for r in assessment if r.needs_maintenance]
            
            # Call your work order API
            # maintenance_api.create_ticket(
            #     asset_id=twin.asset_id,
            #     priority="HIGH",
            #     reason="; ".join(reasons),
            #     predicted_by="digital_twin",
            # )
            
            print(f"Created maintenance ticket for {twin.asset_id}")
            print(f"  Reasons: {'; '.join(reasons)}")

# Example usage
# twins = [pump_twin_1, pump_twin_2, hvac_twin_1]
# check_and_schedule_maintenance(twins, maintenance_system)
```

## Telemetry Management

```python
# Add individual point
from asset_twin import TelemetryPoint

point = TelemetryPoint(
    timestamp=datetime.utcnow(),
    flow=92.0,
    temperature=72.0,
    pressure=3.5,  # Optional
    metadata={"sensor_id": "T-001"},  # Optional
)
twin.add_telemetry(point)

# Or use convenience method
twin.add_telemetry_reading(
    timestamp=datetime.utcnow(),
    flow=92.0,
    temperature=72.0,
)

# Query telemetry
count = twin.get_telemetry_count()
latest = twin.get_latest_telemetry()

# Clear old data (e.g., for data retention policy)
twin.clear_telemetry()
```

## Testing

```bash
pytest asset_twin/tests/
```

Tests cover:
- Normal operation (no maintenance needed)
- Flow degradation scenarios
- Temperature excursion scenarios
- Insufficient data handling
- Configuration validation
- Custom rule integration

## Architecture

```
asset_twin/
├── __init__.py              # Public API
├── twin.py                  # AssetTwin main class
├── config.py                # TwinConfig and MaintenanceThresholds
├── telemetry.py             # TelemetryPoint data model
├── rules.py                 # RuleEngine and built-in rules
└── tests/
    └── test_twin.py         # Comprehensive tests
```

## Design Principles

1. **Separation of concerns**: Data model (telemetry) separate from rules engine
2. **Configurable thresholds**: No hardcoded magic numbers
3. **Extensible**: Easy to add custom rules
4. **No external dependencies**: Uses only Python standard library
5. **Deterministic**: Same telemetry + config = same result

## Integration Points

For production deployment, extend with:

### IoT Sensor Integration

```python
# Implement sensor data collection via MQTT or REST API
# Example:

# import paho.mqtt.client as mqtt
# 
# def on_message(client, userdata, msg):
#     data = json.loads(msg.payload)
#     twin = userdata["twins"][data["asset_id"]]
#     twin.add_telemetry_reading(
#         timestamp=datetime.fromisoformat(data["timestamp"]),
#         flow=data["flow"],
#         temperature=data["temperature"],
#     )
```

### Persistence Layer

```python
# Save/load twin state from your database
# 
# class TwinRepository:
#     def save(self, twin: AssetTwin):
#         # Serialize telemetry to database
#         # Save config
#         pass
#     
#     def load(self, asset_id: str) -> AssetTwin:
#         # Load config and telemetry from database
#         # Reconstruct twin
#         pass
```

### Notification Service

```python
# Alert facility managers when maintenance needed
# 
# if twin.needs_maintenance():
#     send_notification(
#         to="facilities@alrabyah.om",
#         subject=f"Maintenance Alert: {twin.asset_id}",
#         body=assessment_report,
#     )
```

## Use Cases

### 1. Preventive Maintenance
Monitor building systems continuously and predict failures before they occur.

### 2. Energy Efficiency
Detect degraded performance (e.g., reduced flow) that increases energy consumption.

### 3. Compliance
Maintain audit trail of asset performance for regulatory compliance.

### 4. Lifecycle Management
Track asset health over time to inform replacement decisions.

## License

Internal use - Al Rabyah property management platform / GrassRoot CIC.






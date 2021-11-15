# ExamBox Tracking - State Machine Library

RFID/QR exam-box tracking with explicit state transitions and audit logging.

## Innovation Highlights

- **Formal State Machine**: Applied automata theory to physical logistics, with compile-time enforcement of allowed transitions
- **Deterministic Workflow**: Same event sequence always produces identical final state—critical for audit compliance
- **Immutable Audit Trail**: Value object pattern ensures event history cannot be tampered with
- **Exception State Design**: Invalid transitions move boxes to Exception state rather than failing silently, enabling recovery workflows

## Overview

This library provides a production-ready state machine for tracking exam boxes through their logistics lifecycle:

- **Explicit state transitions**: Clearly defined allowed transitions prevent invalid state changes
- **Audit logging abstraction**: Pluggable logging interface for compliance and debugging
- **Validation**: Guards against illegal transitions and malformed events
- **Exception handling**: Configurable behavior for invalid state transitions
- **Deterministic**: No hidden state, fully testable

## States

```
Created → AtDepot → InTransitToScanner → Scanning → AwaitingMarkerDispatch → WithMarker → Completed
                                                                                              ↓
                                                                                          Exception
```

## Installation

```bash
dotnet add reference ExamBoxTracking.csproj
```

## Quick Start

```csharp
using ExamBoxTracking.Domain;
using ExamBoxTracking.Abstractions;

// 1. Create a box
var box = new ExamBox("BOX-2025-001");

// 2. Apply events as box moves through workflow
box.ApplyEvent(new BoxEvent("BOX-2025-001", "DEPOT_IN"));
box.ApplyEvent(new BoxEvent("BOX-2025-001", "LOAD_FOR_SCANNER"));
box.ApplyEvent(new BoxEvent("BOX-2025-001", "SCANNER_IN", weightKg: 15.5));
box.ApplyEvent(new BoxEvent("BOX-2025-001", "SCANNER_OUT"));
box.ApplyEvent(new BoxEvent("BOX-2025-001", "DISPATCH_TO_MARKER"));
box.ApplyEvent(new BoxEvent("BOX-2025-001", "BOX_RETURNED"));

Console.WriteLine(box.State); // Completed
Console.WriteLine(box.RecordedWeightKg); // 15.5
```

## Event Types

| Event                  | From State              | To State                |
|------------------------|-------------------------|-------------------------|
| `DEPOT_IN`             | Created                 | AtDepot                 |
| `LOAD_FOR_SCANNER`     | AtDepot                 | InTransitToScanner      |
| `SCANNER_IN`           | InTransitToScanner      | Scanning                |
| `SCANNER_OUT`          | Scanning                | AwaitingMarkerDispatch  |
| `DISPATCH_TO_MARKER`   | AwaitingMarkerDispatch  | WithMarker              |
| `BOX_RETURNED`         | WithMarker              | Completed               |

## Audit Logging

Implement `IAuditLogger` to persist state transitions:

```csharp
using ExamBoxTracking.Abstractions;

public class DatabaseAuditLogger : IAuditLogger
{
    // Inject your database context or repository via constructor
    
    public void LogTransition(
        string boxId,
        string fromState,
        string toState,
        string eventType,
        double? weightKg,
        DateTime timestamp,
        string? userId = null,
        string? location = null)
    {
        // Persist to TL_BatchLog or equivalent audit table
        // Example:
        // await _db.AuditLog.AddAsync(new AuditRecord {
        //     BoxId = boxId,
        //     FromState = fromState,
        //     ToState = toState,
        //     EventType = eventType,
        //     WeightKg = weightKg,
        //     Timestamp = timestamp,
        //     UserId = userId,
        //     Location = location
        // });
        // await _db.SaveChangesAsync();
    }

    public void LogException(
        string boxId,
        string currentState,
        string eventType,
        string reason,
        DateTime timestamp)
    {
        // Log to incident/exception tracking system
        // Example:
        // await _db.ExceptionLog.AddAsync(new ExceptionRecord {
        //     BoxId = boxId,
        //     State = currentState,
        //     EventType = eventType,
        //     Reason = reason,
        //     Timestamp = timestamp
        // });
    }
}

// Usage
var logger = new DatabaseAuditLogger();
var box = new ExamBox("BOX-001", logger);
box.ApplyEvent(new BoxEvent("BOX-001", "DEPOT_IN"));
// Transition is now logged to database
```

## Error Handling

### Default Behavior (Transition to Exception State)

```csharp
var box = new ExamBox("BOX-001");
box.ApplyEvent(new BoxEvent("BOX-001", "SCANNER_IN")); // Illegal: skip depot

Console.WriteLine(box.State); // Exception
```

### Throw on Illegal Transition

```csharp
var box = new ExamBox("BOX-001");

try
{
    box.ApplyEvent(
        new BoxEvent("BOX-001", "SCANNER_IN"),
        throwOnIllegalTransition: true
    );
}
catch (IllegalTransitionException ex)
{
    Console.WriteLine($"Illegal: {ex.EventType} from {ex.CurrentState}");
}
```

## Query Allowed Transitions

```csharp
var box = new ExamBox("BOX-001");
box.ApplyEvent(new BoxEvent("BOX-001", "DEPOT_IN"));

// Check if specific event is allowed
bool canLoad = box.CanApplyEvent("LOAD_FOR_SCANNER"); // true
bool canScan = box.CanApplyEvent("SCANNER_IN");        // false

// Get all allowed events
var allowed = box.GetAllowedEvents();
// Returns: ["LOAD_FOR_SCANNER"]
```

## Testing

```bash
dotnet test ExamBoxTracking.Tests
```

All tests use the in-memory `InMemoryAuditLogger` mock, so no database is required.

## Architecture

```
ExamBoxTracking/
├── Domain/
│   ├── BoxState.cs           # State enum
│   ├── ExamBox.cs            # Core state machine entity
│   ├── BoxEvent.cs           # Event value object
│   └── Exceptions.cs         # Domain exceptions
├── Abstractions/
│   └── IAuditLogger.cs       # Audit logging interface
└── ExamBoxTracking.csproj

ExamBoxTracking.Tests/
├── ExamBoxTests.cs           # Comprehensive unit tests
└── ExamBoxTracking.Tests.csproj
```

## Design Principles

1. **Explicit transitions**: All allowed transitions defined in `AllowedTransitions` dictionary
2. **Immutable events**: `BoxEvent` is immutable after creation
3. **Separation of concerns**: Domain logic separated from persistence (IAuditLogger)
4. **No hidden state**: All state is observable via public properties
5. **Deterministic**: Same sequence of events always produces same final state

## Integration with Hardware Events

```csharp
// Example: RFID reader event handler
public class RFIDEventHandler
{
    private readonly IExamBoxRepository _repository; // Define repository interface for your persistence layer
    private readonly IAuditLogger _auditLogger;

    public async Task HandleRFIDScan(string boxId, string readerId, DateTime scanTime)
    {
        // Load box from repository
        var box = await _repository.GetBoxAsync(boxId);
        
        // Determine event type based on reader location
        string eventType = DetermineEventType(readerId);
        
        var boxEvent = new BoxEvent(
            boxId: boxId,
            eventType: eventType,
            timestamp: scanTime,
            location: readerId
        );
        
        box.ApplyEvent(boxEvent);
        
        // Save updated box state
        await _repository.SaveAsync(box);
    }
    
    private string DetermineEventType(string readerId)
    {
        // Map reader IDs to event types based on your facility layout
        // Example:
        // - "DEPOT_GATE_IN" → "DEPOT_IN"
        // - "SCANNER_ROOM_1" → "SCANNER_IN"
        throw new NotImplementedException();
    }
}
```

## Integration Points

For production deployment, extend with:

- **Repository/Persistence**: Define `IExamBoxRepository` for loading and saving box state to your database
- **Hardware Integration**: Map RFID/QR reader IDs to event types in your scanning infrastructure
- **Weight Validation**: Add business rules for expected weight ranges based on box type
- **Notification Service**: Alert on exception states or delayed transitions
- **Reporting**: Query audit logs for box history, average transit times, and process analytics

## License

Internal use - AQA exam logistics platform.


using System;
using System.Collections.Generic;
using ExamBoxTracking.Abstractions;

namespace ExamBoxTracking.Domain
{
    /// <summary>
    /// Exam box domain entity with deterministic state machine logic.
    /// 
    /// Tracks the lifecycle of a physical exam box through scanning and marking workflow.
    /// State transitions are explicitly defined via AllowedTransitions dictionary, ensuring
    /// only valid state changes can occur. Invalid transitions move the box to Exception
    /// state rather than throwing exceptions, allowing manual intervention.
    /// 
    /// Innovation: Formalizes physical logistics workflow as a type-safe state machine with
    /// built-in audit trail, replacing error-prone conditional logic with explicit transition table.
    /// </summary>
    /// <remarks>
    /// This implementation demonstrates domain-driven design for safety-critical applications
    /// (national exam processing). The state machine pattern ensures compliance by making
    /// invalid states representationally impossible.
    /// </remarks>
    public class ExamBox
    {
        /// <summary>
        /// Dictionary defining all legal state transitions.
        /// Key: (current state, event type) → Value: new state
        /// 
        /// This explicit mapping makes the state graph visible and testable. Any transition
        /// not in this dictionary is automatically invalid.
        /// </summary>
        private static readonly Dictionary<(BoxState, string), BoxState> AllowedTransitions =
            new Dictionary<(BoxState, string), BoxState>
            {
                { (BoxState.Created, "DEPOT_IN"), BoxState.AtDepot },
                { (BoxState.AtDepot, "LOAD_FOR_SCANNER"), BoxState.InTransitToScanner },
                { (BoxState.InTransitToScanner, "SCANNER_IN"), BoxState.Scanning },
                { (BoxState.Scanning, "SCANNER_OUT"), BoxState.AwaitingMarkerDispatch },
                { (BoxState.AwaitingMarkerDispatch, "DISPATCH_TO_MARKER"), BoxState.WithMarker },
                { (BoxState.WithMarker, "BOX_RETURNED"), BoxState.Completed },
            };

        private readonly IAuditLogger? _auditLogger;

        public string BoxId { get; }
        public BoxState State { get; private set; }
        public double? RecordedWeightKg { get; private set; }
        public DateTime CreatedAt { get; }
        public DateTime LastModifiedAt { get; private set; }

        /// <summary>
        /// Create a new exam box in the Created state.
        /// </summary>
        /// <param name="boxId">Unique identifier for the box (required).</param>
        /// <param name="auditLogger">Optional audit logger for state transitions and exceptions.</param>
        /// <exception cref="ArgumentException">Thrown if boxId is null or whitespace.</exception>
        public ExamBox(string boxId, IAuditLogger? auditLogger = null)
        {
            if (string.IsNullOrWhiteSpace(boxId))
                throw new ArgumentException("BoxId cannot be null or empty", nameof(boxId));

            BoxId = boxId;
            State = BoxState.Created;
            _auditLogger = auditLogger;
            CreatedAt = DateTime.UtcNow;
            LastModifiedAt = CreatedAt;
        }

        /// <summary>
        /// Apply an event to transition the box to a new state.
        /// </summary>
        /// <param name="boxEvent">Event containing type, weight, and other metadata.</param>
        /// <param name="throwOnIllegalTransition">
        /// If true, throw IllegalTransitionException on invalid transitions.
        /// If false, transition to Exception state instead (original behavior).
        /// </param>
        /// <exception cref="IllegalTransitionException">
        /// Thrown when transition is illegal and throwOnIllegalTransition is true.
        /// </exception>
        public void ApplyEvent(BoxEvent boxEvent, bool throwOnIllegalTransition = false)
        {
            if (boxEvent == null)
                throw new ArgumentNullException(nameof(boxEvent));

            if (boxEvent.BoxId != BoxId)
                throw new EventValidationException(
                    $"Event BoxId '{boxEvent.BoxId}' does not match this box '{BoxId}'");

            var previousState = State;

            // Check if this is an allowed transition
            if (AllowedTransitions.TryGetValue((State, boxEvent.EventType), out var newState))
            {
                State = newState;

                // Capture weight if provided on SCANNER_IN event
                if (boxEvent.EventType == "SCANNER_IN" && boxEvent.WeightKg.HasValue)
                {
                    RecordedWeightKg = boxEvent.WeightKg.Value;
                }

                LastModifiedAt = boxEvent.Timestamp;

                _auditLogger?.LogTransition(
                    BoxId,
                    previousState.ToString(),
                    State.ToString(),
                    boxEvent.EventType,
                    boxEvent.WeightKg,
                    boxEvent.Timestamp,
                    boxEvent.UserId,
                    boxEvent.Location);
            }
            else
            {
                // Illegal transition
                if (throwOnIllegalTransition)
                {
                    throw new IllegalTransitionException(BoxId, State, boxEvent.EventType);
                }
                else
                {
                    // Original behavior: flag as Exception state
                    State = BoxState.Exception;
                    LastModifiedAt = boxEvent.Timestamp;

                    _auditLogger?.LogException(
                        BoxId,
                        previousState.ToString(),
                        boxEvent.EventType,
                        $"Illegal transition from {previousState}",
                        boxEvent.Timestamp);
                }
            }
        }

        /// <summary>
        /// Determine if a specific event type is allowed from the current state.
        /// </summary>
        public bool CanApplyEvent(string eventType)
        {
            return AllowedTransitions.ContainsKey((State, eventType));
        }

        /// <summary>
        /// Get all allowed event types from the current state.
        /// </summary>
        public IEnumerable<string> GetAllowedEvents()
        {
            var allowed = new List<string>();
            foreach (var key in AllowedTransitions.Keys)
            {
                if (key.Item1 == State)
                {
                    allowed.Add(key.Item2);
                }
            }
            return allowed;
        }

        /// <summary>
        /// Check if the box is in a terminal state (Completed or Exception).
        /// </summary>
        public bool IsTerminal => State == BoxState.Completed || State == BoxState.Exception;

        public override string ToString() =>
            $"ExamBox[{BoxId}]: State={State}, Weight={RecordedWeightKg?.ToString("F2") ?? "N/A"}kg";
    }
}




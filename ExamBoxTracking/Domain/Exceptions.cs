using System;

namespace ExamBoxTracking.Domain
{
    /// <summary>
    /// Base exception for exam box domain operations.
    /// </summary>
    public class ExamBoxException : Exception
    {
        public ExamBoxException(string message) : base(message) { }
        public ExamBoxException(string message, Exception innerException) : base(message, innerException) { }
    }

    /// <summary>
    /// Thrown when an illegal state transition is attempted.
    /// </summary>
    public class IllegalTransitionException : ExamBoxException
    {
        public string BoxId { get; }
        public BoxState CurrentState { get; }
        public string EventType { get; }

        public IllegalTransitionException(
            string boxId,
            BoxState currentState,
            string eventType)
            : base($"Illegal transition: BoxId={boxId}, State={currentState}, Event={eventType}")
        {
            BoxId = boxId;
            CurrentState = currentState;
            EventType = eventType;
        }
    }

    /// <summary>
    /// Thrown when validation of an event fails.
    /// </summary>
    public class EventValidationException : ExamBoxException
    {
        public EventValidationException(string message) : base(message) { }
    }
}



using System;
using System.Collections.Generic;

namespace ExamBoxTracking.Abstractions
{
    /// <summary>
    /// Abstraction for persisting and querying audit trail records.
    /// </summary>
    /// <remarks>
    /// Implementations should store event history to a database, message bus,
    /// or other durable storage.
    /// </remarks>
    public interface IAuditLogger
    {
        /// <summary>
        /// Record a state transition event for audit purposes.
        /// </summary>
        /// <param name="boxId">Unique identifier of the exam box.</param>
        /// <param name="fromState">State before transition.</param>
        /// <param name="toState">State after transition.</param>
        /// <param name="eventType">Event that triggered the transition.</param>
        /// <param name="weightKg">Optional weight measurement.</param>
        /// <param name="timestamp">Event timestamp.</param>
        /// <param name="userId">Optional user who triggered the event.</param>
        /// <param name="location">Optional location code where event occurred.</param>
        void LogTransition(
            string boxId,
            string fromState,
            string toState,
            string eventType,
            double? weightKg,
            DateTime timestamp,
            string? userId = null,
            string? location = null);

        /// <summary>
        /// Record an exception or illegal transition event.
        /// </summary>
        void LogException(
            string boxId,
            string currentState,
            string eventType,
            string reason,
            DateTime timestamp);
    }
}








using System;

namespace ExamBoxTracking.Domain
{
    /// <summary>
    /// Represents a state transition event in the exam box lifecycle.
    /// </summary>
    public class BoxEvent
    {
        public string BoxId { get; }
        public string EventType { get; }
        public double? WeightKg { get; }
        public DateTime Timestamp { get; }
        public string? UserId { get; }
        public string? Location { get; }

        public BoxEvent(
            string boxId,
            string eventType,
            double? weightKg = null,
            DateTime? timestamp = null,
            string? userId = null,
            string? location = null)
        {
            if (string.IsNullOrWhiteSpace(boxId))
                throw new ArgumentException("BoxId cannot be null or empty", nameof(boxId));

            if (string.IsNullOrWhiteSpace(eventType))
                throw new ArgumentException("EventType cannot be null or empty", nameof(eventType));

            BoxId = boxId;
            EventType = eventType;
            WeightKg = weightKg;
            Timestamp = timestamp ?? DateTime.UtcNow;
            UserId = userId;
            Location = location;
        }

        public override string ToString() =>
            $"BoxEvent[{BoxId}]: {EventType} at {Timestamp:u}" +
            (WeightKg.HasValue ? $", Weight={WeightKg:F2}kg" : "");
    }
}




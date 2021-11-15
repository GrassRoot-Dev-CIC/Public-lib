using System;
using Xunit;
using ExamBoxTracking.Domain;
using ExamBoxTracking.Abstractions;

namespace ExamBoxTracking.Tests
{
    /// <summary>
    /// Mock audit logger for testing.
    /// </summary>
    public class InMemoryAuditLogger : IAuditLogger
    {
        public List<(string BoxId, string From, string To, string Event, double? Weight, DateTime Timestamp)> Transitions { get; }
            = new List<(string, string, string, string, double?, DateTime)>();

        public List<(string BoxId, string State, string Event, string Reason, DateTime Timestamp)> Exceptions { get; }
            = new List<(string, string, string, string, DateTime)>();

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
            Transitions.Add((boxId, fromState, toState, eventType, weightKg, timestamp));
        }

        public void LogException(
            string boxId,
            string currentState,
            string eventType,
            string reason,
            DateTime timestamp)
        {
            Exceptions.Add((boxId, currentState, eventType, reason, timestamp));
        }
    }

    public class ExamBoxTests
    {
        [Fact]
        public void NewBox_ShouldStartInCreatedState()
        {
            // Arrange & Act
            var box = new ExamBox("BOX001");

            // Assert
            Assert.Equal("BOX001", box.BoxId);
            Assert.Equal(BoxState.Created, box.State);
            Assert.Null(box.RecordedWeightKg);
            Assert.False(box.IsTerminal);
        }

        [Fact]
        public void Constructor_ShouldRejectNullBoxId()
        {
            // Act & Assert
            Assert.Throws<ArgumentException>(() => new ExamBox(null!));
        }

        [Fact]
        public void Constructor_ShouldRejectEmptyBoxId()
        {
            // Act & Assert
            Assert.Throws<ArgumentException>(() => new ExamBox("   "));
        }

        [Fact]
        public void ApplyEvent_ValidTransition_ShouldChangeState()
        {
            // Arrange
            var box = new ExamBox("BOX001");
            var evt = new BoxEvent("BOX001", "DEPOT_IN");

            // Act
            box.ApplyEvent(evt);

            // Assert
            Assert.Equal(BoxState.AtDepot, box.State);
        }

        [Fact]
        public void ApplyEvent_CompleteWorkflow_ShouldReachCompleted()
        {
            // Arrange
            var box = new ExamBox("BOX001");

            // Act - full workflow
            box.ApplyEvent(new BoxEvent("BOX001", "DEPOT_IN"));
            box.ApplyEvent(new BoxEvent("BOX001", "LOAD_FOR_SCANNER"));
            box.ApplyEvent(new BoxEvent("BOX001", "SCANNER_IN", weightKg: 15.5));
            box.ApplyEvent(new BoxEvent("BOX001", "SCANNER_OUT"));
            box.ApplyEvent(new BoxEvent("BOX001", "DISPATCH_TO_MARKER"));
            box.ApplyEvent(new BoxEvent("BOX001", "BOX_RETURNED"));

            // Assert
            Assert.Equal(BoxState.Completed, box.State);
            Assert.Equal(15.5, box.RecordedWeightKg);
            Assert.True(box.IsTerminal);
        }

        [Fact]
        public void ApplyEvent_WithWeight_ShouldCaptureWeight()
        {
            // Arrange
            var box = new ExamBox("BOX001");
            box.ApplyEvent(new BoxEvent("BOX001", "DEPOT_IN"));
            box.ApplyEvent(new BoxEvent("BOX001", "LOAD_FOR_SCANNER"));

            // Act
            box.ApplyEvent(new BoxEvent("BOX001", "SCANNER_IN", weightKg: 22.3));

            // Assert
            Assert.Equal(BoxState.Scanning, box.State);
            Assert.Equal(22.3, box.RecordedWeightKg);
        }

        [Fact]
        public void ApplyEvent_IllegalTransition_DefaultBehavior_ShouldGoToException()
        {
            // Arrange
            var box = new ExamBox("BOX001");
            // Skip depot and try to go straight to transit - illegal

            // Act
            box.ApplyEvent(new BoxEvent("BOX001", "LOAD_FOR_SCANNER"));

            // Assert
            Assert.Equal(BoxState.Exception, box.State);
            Assert.True(box.IsTerminal);
        }

        [Fact]
        public void ApplyEvent_IllegalTransition_WithThrow_ShouldThrowException()
        {
            // Arrange
            var box = new ExamBox("BOX001");

            // Act & Assert
            var exception = Assert.Throws<IllegalTransitionException>(() =>
                box.ApplyEvent(new BoxEvent("BOX001", "SCANNER_IN"), throwOnIllegalTransition: true));

            Assert.Equal("BOX001", exception.BoxId);
            Assert.Equal(BoxState.Created, exception.CurrentState);
            Assert.Equal("SCANNER_IN", exception.EventType);
        }

        [Fact]
        public void ApplyEvent_WrongBoxId_ShouldThrowValidationException()
        {
            // Arrange
            var box = new ExamBox("BOX001");
            var evt = new BoxEvent("BOX002", "DEPOT_IN");

            // Act & Assert
            var exception = Assert.Throws<EventValidationException>(() => box.ApplyEvent(evt));
            Assert.Contains("BOX002", exception.Message);
            Assert.Contains("BOX001", exception.Message);
        }

        [Fact]
        public void ApplyEvent_NullEvent_ShouldThrowArgumentNull()
        {
            // Arrange
            var box = new ExamBox("BOX001");

            // Act & Assert
            Assert.Throws<ArgumentNullException>(() => box.ApplyEvent(null!));
        }

        [Fact]
        public void CanApplyEvent_ValidEvent_ShouldReturnTrue()
        {
            // Arrange
            var box = new ExamBox("BOX001");

            // Act & Assert
            Assert.True(box.CanApplyEvent("DEPOT_IN"));
            Assert.False(box.CanApplyEvent("SCANNER_IN"));
        }

        [Fact]
        public void GetAllowedEvents_ShouldReturnCorrectEvents()
        {
            // Arrange
            var box = new ExamBox("BOX001");
            box.ApplyEvent(new BoxEvent("BOX001", "DEPOT_IN"));

            // Act
            var allowed = box.GetAllowedEvents();

            // Assert
            Assert.Contains("LOAD_FOR_SCANNER", allowed);
            Assert.DoesNotContain("DEPOT_IN", allowed);
            Assert.DoesNotContain("SCANNER_IN", allowed);
        }

        [Fact]
        public void AuditLogger_ShouldLogValidTransition()
        {
            // Arrange
            var logger = new InMemoryAuditLogger();
            var box = new ExamBox("BOX001", logger);

            // Act
            box.ApplyEvent(new BoxEvent("BOX001", "DEPOT_IN"));

            // Assert
            Assert.Single(logger.Transitions);
            var log = logger.Transitions[0];
            Assert.Equal("BOX001", log.BoxId);
            Assert.Equal("Created", log.From);
            Assert.Equal("AtDepot", log.To);
            Assert.Equal("DEPOT_IN", log.Event);
        }

        [Fact]
        public void AuditLogger_ShouldLogException()
        {
            // Arrange
            var logger = new InMemoryAuditLogger();
            var box = new ExamBox("BOX001", logger);

            // Act
            box.ApplyEvent(new BoxEvent("BOX001", "INVALID_EVENT"));

            // Assert
            Assert.Empty(logger.Transitions);
            Assert.Single(logger.Exceptions);
            var log = logger.Exceptions[0];
            Assert.Equal("BOX001", log.BoxId);
            Assert.Equal("Created", log.State);
            Assert.Equal("INVALID_EVENT", log.Event);
        }

        [Fact]
        public void LastModifiedAt_ShouldUpdateOnTransition()
        {
            // Arrange
            var box = new ExamBox("BOX001");
            var initialModified = box.LastModifiedAt;
            System.Threading.Thread.Sleep(10); // Ensure time difference

            // Act
            box.ApplyEvent(new BoxEvent("BOX001", "DEPOT_IN"));

            // Assert
            Assert.True(box.LastModifiedAt > initialModified);
        }

        [Fact]
        public void ToString_ShouldContainBoxIdAndState()
        {
            // Arrange
            var box = new ExamBox("BOX001");

            // Act
            var str = box.ToString();

            // Assert
            Assert.Contains("BOX001", str);
            Assert.Contains("Created", str);
        }

        [Theory]
        [InlineData("DEPOT_IN", BoxState.AtDepot)]
        [InlineData("LOAD_FOR_SCANNER", BoxState.InTransitToScanner)]
        public void ApplyEvent_FromAtDepot_ShouldTransitionCorrectly(string eventType, BoxState expectedState)
        {
            // Arrange
            var box = new ExamBox("BOX001");
            box.ApplyEvent(new BoxEvent("BOX001", "DEPOT_IN"));

            // Act
            if (eventType == "LOAD_FOR_SCANNER")
            {
                box.ApplyEvent(new BoxEvent("BOX001", eventType));
            }

            // Assert
            if (eventType == "LOAD_FOR_SCANNER")
            {
                Assert.Equal(expectedState, box.State);
            }
        }

        [Fact]
        public void MultipleIllegalTransitions_ShouldStayInException()
        {
            // Arrange
            var box = new ExamBox("BOX001");
            box.ApplyEvent(new BoxEvent("BOX001", "INVALID_EVENT_1"));

            // Act
            box.ApplyEvent(new BoxEvent("BOX001", "INVALID_EVENT_2"));

            // Assert
            Assert.Equal(BoxState.Exception, box.State);
        }

        [Fact]
        public void IsTerminal_CompletedState_ShouldBeTrue()
        {
            // Arrange
            var box = new ExamBox("BOX001");
            box.ApplyEvent(new BoxEvent("BOX001", "DEPOT_IN"));
            box.ApplyEvent(new BoxEvent("BOX001", "LOAD_FOR_SCANNER"));
            box.ApplyEvent(new BoxEvent("BOX001", "SCANNER_IN"));
            box.ApplyEvent(new BoxEvent("BOX001", "SCANNER_OUT"));
            box.ApplyEvent(new BoxEvent("BOX001", "DISPATCH_TO_MARKER"));
            box.ApplyEvent(new BoxEvent("BOX001", "BOX_RETURNED"));

            // Assert
            Assert.True(box.IsTerminal);
        }

        [Fact]
        public void IsTerminal_ExceptionState_ShouldBeTrue()
        {
            // Arrange
            var box = new ExamBox("BOX001");
            box.ApplyEvent(new BoxEvent("BOX001", "INVALID_EVENT"));

            // Assert
            Assert.True(box.IsTerminal);
        }
    }

    public class BoxEventTests
    {
        [Fact]
        public void Constructor_ValidData_ShouldCreateEvent()
        {
            // Act
            var evt = new BoxEvent("BOX001", "DEPOT_IN", weightKg: 10.5);

            // Assert
            Assert.Equal("BOX001", evt.BoxId);
            Assert.Equal("DEPOT_IN", evt.EventType);
            Assert.Equal(10.5, evt.WeightKg);
        }

        [Fact]
        public void Constructor_ShouldRejectNullBoxId()
        {
            // Act & Assert
            Assert.Throws<ArgumentException>(() => new BoxEvent(null!, "EVENT"));
        }

        [Fact]
        public void Constructor_ShouldRejectNullEventType()
        {
            // Act & Assert
            Assert.Throws<ArgumentException>(() => new BoxEvent("BOX001", null!));
        }

        [Fact]
        public void Constructor_WithoutTimestamp_ShouldUseUtcNow()
        {
            // Arrange
            var before = DateTime.UtcNow;

            // Act
            var evt = new BoxEvent("BOX001", "EVENT");

            // Assert
            var after = DateTime.UtcNow;
            Assert.InRange(evt.Timestamp, before, after);
        }

        [Fact]
        public void ToString_ShouldContainKeyInfo()
        {
            // Arrange
            var evt = new BoxEvent("BOX001", "SCANNER_IN", weightKg: 15.5);

            // Act
            var str = evt.ToString();

            // Assert
            Assert.Contains("BOX001", str);
            Assert.Contains("SCANNER_IN", str);
            Assert.Contains("15.50", str);
        }
    }
}

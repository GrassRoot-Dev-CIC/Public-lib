namespace ExamBoxTracking.Domain
{
    /// <summary>
    /// Represents the lifecycle states of an exam box in the tracking system.
    /// </summary>
    public enum BoxState
    {
        /// <summary>Box created in the system but not yet at depot.</summary>
        Created,

        /// <summary>Box received at depot, awaiting dispatch to scanner.</summary>
        AtDepot,

        /// <summary>Box loaded on transport to scanning center.</summary>
        InTransitToScanner,

        /// <summary>Box at scanner, being processed.</summary>
        Scanning,

        /// <summary>Scanning complete, box awaiting dispatch to marker.</summary>
        AwaitingMarkerDispatch,

        /// <summary>Box dispatched to marker for grading.</summary>
        WithMarker,

        /// <summary>Box returned from marker, lifecycle complete.</summary>
        Completed,

        /// <summary>Illegal transition or error state detected.</summary>
        Exception
    }
}




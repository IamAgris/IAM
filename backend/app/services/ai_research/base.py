"""Shared errors for the autonomous research capability (OD-41)."""


class ResearchError(RuntimeError):
    """Base error for AI research operations."""


class InvalidResearchJob(ResearchError):
    """The job spec is malformed, unsafe or incomplete."""


class PaidUpgradeRequested(ResearchError):
    """A platform tried to require paid compute or an automatic upgrade."""


class IsolationViolation(ResearchError):
    """Untrusted code or data attempted to cross its isolation boundary."""


class PrivateDataLeak(ResearchError):
    """Private user data was detected in a payload destined for an external platform."""


class CredentialLeak(ResearchError):
    """A credential appeared in a job, log or result payload."""


class DigestMismatch(ResearchError):
    """A downloaded artifact failed integrity verification."""


class NoImprovement(ResearchError):
    """Post-training evaluation did not improve on the recorded baseline."""

"""Registration gating for free providers (Doc 22 §3.1, §5).

Automated account creation is prohibited by most providers and by Doc 19.
The default decision is therefore creator approval, never silent signup.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RegistrationDecision:
    provider: str
    action: str  # creator_approval | manual_permitted | prohibited
    reason: str
    creator_approval_required: bool = True


class RegistrationGate:
    """Decides whether IAM may register a provider without human intervention."""

    # No provider is approved for autonomous signup by default. Entries can be
    # added only after a documented terms review and creator authorisation.
    AUTONOMOUS_SIGNUP_PERMITTED: frozenset = frozenset()  # type: ignore[type-arg]

    def decide(self, provider: str) -> RegistrationDecision:
        if provider in self.AUTONOMOUS_SIGNUP_PERMITTED:
            return RegistrationDecision(
                provider,
                "manual_permitted",
                "provider terms reviewed and creator-authorised for automated signup",
                creator_approval_required=False,
            )
        return RegistrationDecision(
            provider,
            "creator_approval",
            "automated account creation is not permitted without a documented "
            "terms review and creator authorisation",
            creator_approval_required=True,
        )

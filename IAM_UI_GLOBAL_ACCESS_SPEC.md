# IAM — UI and Global Access Specification

**Status:** FROZEN — companion to IAM Master Architecture

---

## 1. Visual source of truth

The supplied Marlow HTML is the visual source of truth; the displayed identity is **IAM**,
never Marlow. Backend complexity (GeoIP, model routing, internet access, multi-user processing)
is invisible to visitors. No conventional chatbot dashboard redesign.

**Retain:** minimal immersive single-screen, animated particle sphere, orbiting memory nodes,
Focus/Recall/Create, animated responses, glass input, microphone, Space Grotesk typography,
dark/light theme, responsive mobile/desktop.

---

## 2. Element-to-capability mapping

| Element | IAM capability |
|---------|----------------|
| Particle sphere | IAM presence and real operating state (idle/listening/thinking/speaking/working) |
| Orbiting nodes | Real, permission-filtered memories and knowledge |
| Focus | Reasoning, research, problem-solving |
| Recall | Memory retrieval, previous experiences, epistemic status |
| Create | Writing, coding, ideas, project creation |
| Message input | Natural-language communication |
| Microphone | Real speech recognition and voice |
| Animated responses | Live response generation |
| Status text | Online, listening, thinking, speaking, working |
| Suggestions | Dynamic, capability-aware prompts |

Modes are genuinely functional with distinct system prompts — not colour changes.

---

## 3. Global multi-user access

One central IAM identity; many concurrent visitors.

- Anonymous access without registration; secure random session token.
- Independent conversation context per visitor; strict isolation.
- Different questions processed concurrently.
- Desktop, mobile and tablet; multiple languages.
- GeoIP provides coarse regional context only — never identity, nationality, language or trust.
- Visitors can correct location/language manually.
- Three memory levels: current session, anonymous visitor memory (opt-in), optional account.
- Optional accounts for cross-device continuity.
- No cross-visitor private memory leakage.
- Rate limits, abuse detection, overload protection, resource budgets.
- No invasive browser fingerprinting.

---

## 4. Privacy and abuse protection

Anonymous privacy notice; retention and expiry; ability to clear anonymous memory; secure
session cookies; encryption in transit and at rest; session hijacking protection; IP/session
abuse controls; bot detection; per-visitor compute budgets; prompt-injection protection;
regional privacy compliance; separate public/private data stores or strictly enforced boundaries.

---

## 5. Interface rules (official)

1. Supplied HTML is the visual source of truth.
2. Displayed identity is IAM, never Marlow.
3. Do not redesign into a conventional chatbot.
4. New capabilities integrate into the existing design language.
5. Complex settings are optional and unobtrusive; there is no Creator UI —
   authorization is email-based and signed.
6. Sphere reflects real IAM state.
7. Memory nodes represent real, permission-filtered information.
8. All visitors use the same interface.
9. Anonymous access works without registration.
10. Desktop and mobile support.
11. Frontend never exposes model-provider credentials or private services.
12. Multiple simultaneous conversations without context mixing.

---

## 6. Public vs private

Public visitors use IAM's public capability layer only. They cannot access private memories,
goals, computer, finances or admin functions. Owner controls are behind explicit authorization
and never shown in the public interface.

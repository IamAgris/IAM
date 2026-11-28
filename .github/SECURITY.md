# Security Policy

The maintainers of **IAM / AURA** take the security of this project seriously. This
policy explains which versions are supported and how to report a vulnerability
responsibly.

Please do **not** disclose security issues in public issues, pull requests, or
discussions.

---

## Supported Versions

IAM is under active development and has no released versions yet. Security fixes
are applied to the latest commit on the default branch.

| Version | Supported |
| ------- | --------- |
| Latest commit on the default branch | ✅ |
| Older commits / forks | ❌ |

If you find a vulnerability in an older commit, please check whether it still
exists on the default branch before reporting.

---

## Reporting a Vulnerability

**Primary channel — GitHub private vulnerability reporting**

Use GitHub's private reporting form for this repository:

<https://github.com/IamAgris/IAM/security/advisories/new>

This keeps your report visible only to the maintainers.

**Fallback — contact the maintainer on GitHub**

If private vulnerability reporting is unavailable, contact the repository owner
[@IamAgris](https://github.com/IamAgris) through GitHub and ask for a private
channel. Please do not post the details publicly.

**Please include, where possible:**

- A clear description of the vulnerability and its potential impact.
- The affected component (for example API auth, Skill Runtime, browser layer,
  storage, or infrastructure configuration).
- Steps to reproduce, including a proof of concept if you have one.
- The commit or version you tested.
- Any suggested fix or mitigation.

The more detail you provide, the faster we can triage and reproduce the issue.

---

## What to Expect

| Stage | Target timeframe |
| ----- | ---------------- |
| Acknowledgement of your report | Within 3 business days |
| Initial triage and severity assessment | Within 7 days |
| Status updates | At least every 7 days while the issue is open |
| Fix and coordinated disclosure | Depends on complexity; we will agree a timeline with you |

We ask that you keep the report confidential until a fix is available and a
disclosure date has been agreed, so that users are not left exposed. Once the
issue is resolved, we are happy to credit you in the advisory if you wish.

---

## Scope

**In scope:**

- Backend API and authentication (scoped credentials, rate limiting, visitor
  isolation, token handling).
- Frontend and any client-side secret or data exposure.
- IAM Skill Runtime sandboxed execution and authority checks.
- Browser automation, SSRF / DNS-rebinding protections and egress controls.
- Prompt-injection and untrusted-input handling at external boundaries.
- Encryption, secret storage and credential redaction.
- Infrastructure configuration (Docker Compose, deployment and CI workflows).
- The IAM SDK and public API contracts.

**Out of scope:**

- Vulnerabilities in third-party services or dependencies that are already
  publicly known — please report those to the upstream project.
- Theoretical issues without a demonstrable impact, or best-practice advice.
- Issues that require physical access to a user's device.
- Social engineering or attacks against people rather than the software.
- Denial-of-service-only reports with no other security impact.
- Issues already fixed on the default branch.

---

## Safe Harbour

We support good-faith security research. If you follow this policy, we will not
pursue legal action against you for accidental or unintentional damage caused
during your research. In return, please:

- Make every effort to avoid privacy violations, service disruption and
  destruction of data.
- Do not access, modify or exfiltrate data belonging to other users.
- Use test accounts and non-production environments wherever possible.
- Give us a reasonable time to investigate and fix the issue before any public
  disclosure.

If you are unsure whether your research is in scope, ask us first through one of
the channels above.

---

## Related Documentation

- [IAM Security and Internet Access Policy](../docs/IAM_SECURITY_AND_INTERNET_POLICY.md) — internet access rules, network and browser controls, isolation, incident response.
- Further design documents in the source tree cover privacy and secrets handling, scoped API authentication, and the sandboxed Skill Runtime. Consult those documents there when available.

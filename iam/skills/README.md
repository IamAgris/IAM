# IAM Skill Forge packages

This directory is the on-disk store for IAM Skill Forge. It is created and
managed by `app.services.skillforge.SkillForgeEngine` at runtime.

| Directory | Purpose |
| --- | --- |
| `native/` | IAM's own created skills, grouped by category |
| `imported/` | Verified skills from OpenAI, NVIDIA, Google, Anthropic, Microsoft or the community |
| `pending/` | Unverified imported candidates — never active |
| `quarantine/` | Failed, suspicious or revoked skills — never active |
| `archived/` | Immutable version snapshots used for rollback |

Every package contains `SKILL.md`, `manifest.json`, `permissions.json`, and
`resources/`, `scripts/` and `tests/` directories.

A manifest is descriptive metadata only. Permissions are enforced by
`PermissionManager` and owner-issued grants in the database, never by the
contents of a skill's files.

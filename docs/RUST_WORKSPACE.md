# IAM Rust workspace — conventions

**Status:** Scaffold only (action #1 of `IAM_IMPLEMENTATION_TECHNOLOGY_ADDENDUM.md`; acceptance A17).  
**Scope:** Establishes the toolchain, lint baseline, CI gates and one minimal contracts crate. It does **not** implement any IAM subsystem or replace any Python component.

---

## 1. Layout

| Path | Purpose |
|------|---------|
| `Cargo.toml` | Virtual workspace manifest, shared edition/MSRV and lint baseline |
| `rust-toolchain.toml` | Pinned toolchain: 1.90.0 with `rustfmt` and `clippy` |
| `rustfmt.toml`, `clippy.toml` | Formatting and MSRV settings |
| `crates/iam-contracts/` | Versioned, language-neutral envelope types for the Python–Rust boundary |
| `.github/workflows/rust.yml` | Format, lint, test and audit gates on x86-64 and ARM64 |

New infrastructure crates are added under `crates/` only when the measured-benefit gate (A19) has been satisfied. A crate must have exactly one responsibility and must be registered in the workspace `members` list.

---

## 2. Commands

Install the pinned toolchain via rustup (it reads `rust-toolchain.toml` automatically), then run from the repository root:

```powershell
cargo fmt --all -- --check
cargo clippy --workspace --all-targets -- -D warnings
cargo test --workspace
cargo generate-lockfile
cargo audit          # requires `cargo install cargo-audit`
cargo build --workspace --release
```

`cargo audit` needs `Cargo.lock`; CI generates it before auditing. Commit `Cargo.lock` once the lockfile has been generated locally.

---

## 3. Conventions

1. **Contracts, not logic.** Rust crates must not duplicate business rules from `backend/app/services/`. Shared types stay versioned and language-neutral (`iam-contracts`).
2. **One implementation per responsibility.** A capability is implemented once and exposed through its contract — never in both Python and Rust.
3. **No authority material.** Rust components never hold credentials or signing keys and never approve protected-core changes; those stay with the existing Python services (OD-03/OD-11).
4. **No locked-component replacement.** Python/FastAPI, Next.js/TypeScript and OD-08 ARQ are unchanged by this workspace.
5. **Unsafe code requires review.** `unsafe_code` is warned at workspace level and promoted to an error by CI's `-D warnings`. Any FFI boundary must be isolated in a dedicated crate with an explicit, reviewed allowance and a safety comment.
6. **Evidence before adoption.** Every crate intended to replace an incumbent Python implementation carries a recorded baseline and candidate measurement (A19), and preserves isolation/hash/redaction behaviour (A20).

---

## 4. Acceptance A17 mapping

| Requirement | Where satisfied |
|-------------|-----------------|
| Workspace builds on x86-64 and ARM64 | `.github/workflows/rust.yml` matrix (`ubuntu-latest`, `ubuntu-24.04-arm`) |
| Developer host build | Pinned toolchain file; commands in §2 are host-independent |
| `cargo fmt --check` | CI step, local command §2 |
| `cargo clippy -- -D warnings` | CI step, local command §2 |
| `cargo audit` | CI step (lockfile generated first), local command §2 |
| Toolchain pinned | `rust-toolchain.toml` (1.90.0) and `clippy.toml` MSRV |

---

## 5. Current limitation

No Rust toolchain is installed on the development host used to create this scaffold, so the A17 commands have **not** been executed locally. They must pass in CI before any further Rust work is built on this workspace.

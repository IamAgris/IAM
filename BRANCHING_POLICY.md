# Branching Policy

## The only permitted long-lived branches

IAM uses exactly two approved branches:

- `main` — stable, reviewed, release-ready code.
- `testing` — integration, testing, and pre-release work.

## Strict branch rules

1. Do not create any additional branches, including feature, fix, bugfix, hotfix, release, research, experiment, or temporary branches.
2. All new work must be committed directly to `testing`.
3. Changes move from `testing` to `main` through a pull request.
4. Never commit experimental or unverified changes directly to `main`.
5. Do not merge `testing` into `main` until tests and review are complete and the repository owner approves the merge.
6. Do not create branches automatically through scripts, bots, agents, IDEs, or deployment tools.
7. If a task appears to require another branch, stop and use `testing`; do not invent a third branch.
8. Existing non-approved branches must not be used for new work. Do not delete or rewrite existing branches without the repository owner's explicit approval.

## Pull request direction

The only permitted pull request direction for normal development is:

`testing` → `main`

Pull requests from any other source branch are outside the approved workflow and must not be created.

## Enforcement

This document defines the repository workflow. Repository administrators should also configure GitHub rulesets/branch protection so that:
- `main` accepts changes only through pull requests;
- force pushes and branch deletion are blocked on `main` and `testing`;
- direct pushes to `main` are restricted;
- only `testing` and `main` are permitted branch names for ongoing development.

A written policy alone cannot prevent a repository administrator or a sufficiently privileged integration from creating another branch. GitHub rulesets must be enabled separately for technical enforcement.

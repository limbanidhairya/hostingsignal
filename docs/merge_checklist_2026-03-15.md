---
title: Merge Checklist 2026-03-15
permalink: /merge_checklist_2026-03-15/
---

# Merge Checklist - 2026-03-15

This checklist enforces a strict merge order with pass/fail gates for each branch.

## Target Order

1. `release/2026-03-15-rc1`
2. `feature/backend-whmcs-2026-03-15`
3. `feature/installer-core-sandbox-2026-03-15`
4. `chore/misc-leftovers-2026-03-15`

---

## Global Rules (Apply To Every PR)

- Branch rebased on latest `origin/main` immediately before final review.
- CI pipeline green (or equivalent local checks attached in PR notes).
- No unresolved merge conflicts.
- No accidental secrets in committed files.
- Reviewer confirms scope matches PR title.

### Hard Stop Conditions

Fail and stop merge if any of the following are true:

- Runtime checks fail on required endpoints.
- Preflight reports critical failures.
- Branch contains out-of-scope file groups not listed in its scope section.
- Commit history includes unrelated WIP or artifact commits.

---

## PR 1 Gate: release/2026-03-15-rc1 -> main

### Expected Scope

- Devpanel runtime hardening and preflight resilience.
- 2086 daemon and template fixes.
- 3000 session/routing/responsive shell fixes.

### Required Verification

1. Merge preview has no unexpected files outside release scope.
2. Endpoint smoke checks:
   - `http://localhost:2083/health` returns 200.
   - `http://localhost:2086/` returns 200.
   - `http://localhost:2087/api/health` returns 200.
   - `http://localhost:3000/` returns 200.
3. Authenticated preflight on 2087:
   - `ready = true`
   - `critical_failures = 0`

### Decision

- PASS: merge PR 1.
- FAIL: block merge and fix on release branch.

---

## PR 2 Gate: feature/backend-whmcs-2026-03-15 -> main

### Precondition

- PR 1 already merged.

### Expected Scope

- Backend API and service-manager enhancements.
- WHMCS integration and related panel wiring.
- Related Perl module and template updates for those flows.

### Required Verification

1. Branch rebased onto latest `origin/main` after PR 1 merge.
2. Focused functional checks for backend/WHMCS paths succeed.
3. No installer/core sandbox directories included in this PR.

### Decision

- PASS: merge PR 2.
- FAIL: block merge and split out accidental scope.

---

## PR 3 Gate: feature/installer-core-sandbox-2026-03-15 -> main

### Precondition

- PR 1 merged.
- PR 2 may be merged before or after, but PR 3 must be rebased on current `main`.

### Expected Scope

- Installer entrypoint and local sandbox install flow.
- `configs`, `core`, `scripts`, `services`, systemd units, and related test/doc support.

### Required Verification

1. Branch rebased onto latest `origin/main`.
2. Python syntax sanity for key scripts/modules:
   - `scripts/local_installer.py`
   - `core/service-manager/service_manager.py`
   - `core/recovery-manager/recovery_manager.py`
   - `core/container-runner/container_runner.py`
   - `tests/panel_test.py`
3. No runtime release hardening regressions introduced.

### Decision

- PASS: merge PR 3.
- FAIL: block merge and fix installer/core branch.

---

## PR 4 Gate: chore/misc-leftovers-2026-03-15 -> main

### Precondition

- PR 3 merged.

### Expected Scope

- Remaining small docs/assets/dockerfile leftovers only.

### Required Verification

1. Branch rebased onto latest `origin/main`.
2. Diff contains only intended leftover files.
3. No runtime, backend, or installer behavior changes.

### Decision

- PASS: merge PR 4.
- FAIL: move accidental logic changes to proper feature branch.

---

## Suggested Command Sequence

```bash
git fetch origin

# PR 1
git checkout release/2026-03-15-rc1
git rebase origin/main
git push --force-with-lease

# PR 2
git checkout feature/backend-whmcs-2026-03-15
git rebase origin/main
git push --force-with-lease

# PR 3
git checkout feature/installer-core-sandbox-2026-03-15
git rebase origin/main
git push --force-with-lease

# PR 4
git checkout chore/misc-leftovers-2026-03-15
git rebase origin/main
git push --force-with-lease
```

---

## Final Release Gate (After PR 1 Merge Minimum)

Use this final go/no-go gate before tagging a release:

- Runtime endpoints pass all required checks.
- Devpanel preflight critical failures remain zero.
- Main branch is clean and tag points to reviewed merge commit.
- Release notes reference merged PR numbers and scope.

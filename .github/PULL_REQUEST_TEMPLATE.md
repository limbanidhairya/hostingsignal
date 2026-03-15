## Summary

- What does this PR change?
- Why is this needed?
- What is intentionally out of scope?

## Branch Scope

- [ ] `release/2026-03-15-rc1`
- [ ] `feature/backend-whmcs-2026-03-15`
- [ ] `feature/installer-core-sandbox-2026-03-15`
- [ ] `chore/misc-leftovers-2026-03-15`
- [ ] Other (describe below)

Scope notes:

## Validation Evidence

Attach command outputs or screenshots for checks you ran.

- [ ] Rebased on latest `origin/main`
- [ ] No unresolved merge conflicts
- [ ] No accidental secrets in committed files

Runtime checks (required for release-impacting PRs):

- [ ] `http://localhost:2083/health` returns 200
- [ ] `http://localhost:2086/` returns 200
- [ ] `http://localhost:2087/api/health` returns 200
- [ ] `http://localhost:3000/` returns 200

Preflight checks (required for devpanel/release PRs):

- [ ] `ready = true`
- [ ] `critical_failures = 0`

## File Scope Check

- [ ] PR includes only intended files for this branch scope
- [ ] No unrelated installer/core/backend/docs bundles mixed in

## Pass/Fail Gate

- [ ] PASS - merge allowed
- [ ] FAIL - blocked until issues are fixed

Blocking reason if FAIL:

## Reviewer Checklist

- [ ] Scope is correct and intentional
- [ ] Validation is reproducible from notes in this PR
- [ ] Merge order impact considered (if any)

---

Reference: [docs/merge_checklist_2026-03-15.md](docs/merge_checklist_2026-03-15.md)

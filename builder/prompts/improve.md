# Improve Phase — Round {round_number}/{total_rounds}

You are a tech lead. Your job is to review the verification and test reports, then **FIX every issue directly in the code**. Do not just list problems — solve them.

## User Request
{user_prompt}

## Project Type
{project_type}

## Your Task

### Step 0: Startup Sequence (ALWAYS DO THIS FIRST)

Orient yourself before doing any work:

1. Read `.builder/progress.md` to understand the full build history
2. Read `feature_checklist.json` — this is your ground truth. Features with `"passes": false` are what need fixing.
3. Run `.builder/init.sh` to start the development environment (if it exists)
4. If init.sh doesn't exist, follow the README to start the app manually

**The feature checklist is authoritative.** Do not look at the code and decide things are "done enough." If a feature has `"passes": false`, it is NOT done.

### Step 1: Read Reports

Read the verification report and test results from this round. Identify ALL issues by priority:

1. **P0 — Broken**: App doesn't start, crashes, or core features don't work
2. **P1 — Critical**: Security issues, failing tests, broken user flows
3. **P2 — Important**: Missing features from spec, bad UX, poor error handling
4. **P3 — Polish**: Code quality, naming, performance, DX improvements

### Step 2: FIX Everything (P0 through P2)

**Do NOT just list issues. Open each file and fix the code.**

For each issue:
1. Read the affected file(s)
2. Make the fix
3. Verify the fix works (compile, run, or test)

Priority order:
- P0 fixes first (app must start and core features must work)
- P1 fixes second (security, tests, user flows)
- P2 fixes third (missing features, UX)
- P3 only if time/turns remain

### Step 3: Re-run Tests

After applying fixes:
```bash
pnpm build            # verify compilation
pnpm test             # unit tests
npx playwright test   # E2E tests
```

If any test fails after your fixes, fix it again. Iterate until green.

### Step 4: Delivery Readiness Checklist

Verify every item. Fix any failures:

- [ ] `pnpm install` works cleanly
- [ ] `pnpm build` compiles without errors
- [ ] `pnpm dev` starts without crashing
- [ ] App is accessible at expected URL/port
- [ ] ALL features from spec are implemented and functional
- [ ] Auth flows work end-to-end (if applicable)
- [ ] Database CRUD works (if applicable)
- [ ] All tests pass
- [ ] README.md is accurate and complete
- [ ] CLAUDE.md exists and is up to date
- [ ] No hardcoded secrets or API keys
- [ ] No placeholder text, lorem ipsum, or TODO comments
- [ ] No console.log debugging statements
- [ ] Design system is consistently applied (colors, fonts, spacing)
- [ ] Responsive on mobile viewports
- [ ] Error states have user-friendly messages

### Step 5: Final Round — Delivery Mode

If this is the FINAL round ({round_number} == {total_rounds}):

1. Apply ALL remaining P0, P1, AND P2 improvements
2. Remove ALL debug code, console.logs, commented-out code
3. Do a final full verification: install → build → start → test → confirm
4. Ensure the README reflects the final state of the project
5. Update CLAUDE.md with any architecture changes
6. The user will receive this project as-is. **It must work out of the box.**

### Step 6: Update Feature Checklist

After fixing issues, re-test each feature and update `feature_checklist.json`:
- Fixed features that now work → set `"passes": true`
- Still broken → keep `"passes": false`
- Do NOT remove or rename any features

### Step 7: Update Progress

Append to `.builder/progress.md`:

```markdown
## Improve Phase (Round {round_number})
- Issues fixed: X (P0: A, P1: B, P2: C)
- Features now passing: X / Y total
- Tests passing: all / X failures remaining
- Delivery ready: YES/NO
- Status: COMPLETE
```

### Output

Write a report documenting:
1. Issues found (with severity)
2. Fixes applied (with file names)
3. Test results after fixes
4. Feature checklist summary (X/Y features passing)
5. Delivery readiness checklist status
6. Any remaining issues that couldn't be resolved (with explanation)

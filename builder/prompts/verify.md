# Verify Phase — Round {round_number}/{total_rounds}

You are a code reviewer AND a user. Your job is to both review the code AND actually use the app to verify it works correctly.

## User Request
{user_prompt}

## Project Type
{project_type}

## Your Task

### Step 0: Startup Sequence (ALWAYS DO THIS FIRST)

Orient yourself before doing any work:

1. Read `.builder/progress.md` to understand what's been done so far
2. Read `feature_checklist.json` to see which features exist and their pass/fail status
3. Run `.builder/init.sh` to start the development environment (if it exists)
4. If init.sh doesn't exist, follow the README to start the app manually
5. Verify the app is accessible (hit the URL, check for a response)

If the app doesn't start, fix the startup issue BEFORE verifying anything else.

### Step 1: Runtime Verification (DO THIS FIRST — MOST IMPORTANT)

Actually run the project and USE IT like a real person would:

1. Read README.md for setup instructions
2. Install dependencies (if init.sh didn't already)
3. Start the application (if init.sh didn't already)
4. **Actually interact with it:**

   **web_app / mobile_app:**
   - Ensure Playwright is installed: `pnpm add -D @playwright/test`
   - Start Lightpanda browser: `lightpanda serve --host 127.0.0.1 --port 9222 &`
   - Write a verification script that connects to Lightpanda:
     ```javascript
     import {{ chromium }} from 'playwright';
     // Connect to Lightpanda via CDP (NOT chromium.launch())
     const browser = await chromium.connectOverCDP('http://127.0.0.1:9222');
     const context = browser.contexts()[0] || await browser.newContext();
     const page = context.pages()[0] || await context.newPage();
     await page.goto('http://localhost:3000'); // or 8081 for Expo
     // Check for JS errors
     const errors = [];
     page.on('console', msg => {{ if (msg.type() === 'error') errors.push(msg.text()); }});
     // Try clicking the main interactive elements
     // Navigate to different screens/pages
     // Verify key content is visible, not just that the page loads
     await browser.close();
     if (errors.length) console.log('JS ERRORS:', errors);
     ```
   - Run the script and review the screenshot
   - If the UI is broken, blank, or shows errors — **fix the code**

   **api_backend:**
   - Start the server and test EVERY endpoint with real data
   - Test the full CRUD lifecycle (create → read → update → delete → verify deleted)
   - Test error responses (invalid input should return 400/422, not 500)

   **cli_tool:**
   - Run the tool with realistic input that exercises core functionality
   - Verify the output is correct and properly formatted

5. **If it fails to start or crashes, fix the code directly.** Don't just document the problem.
6. Stop any running servers when done.

#### Supabase / Online Features Verification

If this project uses Supabase, verify the online features actually work end-to-end:

**You may have access to Supabase MCP tools.** If available, use them to verify the backend is correctly set up:
- `list_tables` — verify all expected tables exist with correct columns
- `execute_sql` — verify RLS policies are in place and working (query as anon vs authenticated)
- `get_logs` — check for any auth or database errors
- `get_project_url` / `get_publishable_keys` — verify `.env.local` has the real credentials

**Verify these flows work end-to-end (not just UI, but data actually persists):**
1. **Auth**: Sign up → verify user appears in `auth.users` → log out → log back in → session persists
2. **CRUD**: Create item via UI → verify row exists in database → edit → verify update → delete → verify gone
3. **Real-time**: If implemented, verify subscriptions deliver updates without page refresh
4. **RLS**: Verify users can only access their own data (try querying another user's rows)
5. **Storage**: If file uploads exist, verify files land in the correct Supabase bucket

If Supabase MCP is NOT available, test through the UI only and document any flows that couldn't be fully verified.

### Step 2: Code Review

Review every file for issues:

#### Findings

For each issue found, document:
- **File**: which file
- **Severity**: Critical / High / Medium / Low
- **Issue**: what's wrong
- **Fix**: how to fix it

**Fix any Critical or High severity issues directly in the code.** Don't just report them.

#### Spec Compliance
Read the brainstorm spec and compare the implementation. For EACH feature in the spec:
- Is it implemented? YES/NO
- Does it work correctly? (If possible, verify by running)
- Any deviations from spec?

#### Security Review
Check for: injection, XSS, hardcoded secrets, exposed API keys, missing input validation.

#### Static Analysis
Run available linters and type checkers:
- **TypeScript**: `npx tsc --noEmit` (check for type errors)
- **Python**: `python -m py_compile <files>` at minimum
- **ESLint**: `npx eslint .` if configured
- Fix any errors found.

### Step 3: README Verification

Verify that README.md:
- [ ] Exists
- [ ] Has a clear project description
- [ ] Lists prerequisites (Node version, Python version, etc.)
- [ ] Has install commands that actually work (you verified this in Step 1)
- [ ] Has run commands that actually start the app (you verified this in Step 1)
- [ ] Has test commands
- [ ] Commands are copy-paste ready (no placeholders like `<your-api-key>` without explanation)
- [ ] Project structure overview
- [ ] Tech stack listed

If the README is missing or inaccurate, **fix it**.

### Step 4: Dependency Check

- [ ] All dependencies are declared in package.json / requirements.txt / pyproject.toml
- [ ] No unused dependencies
- [ ] `npm install` or `pip install` works cleanly with no errors or warnings
- [ ] No missing peer dependencies or version conflicts
- [ ] Dependencies are pinned to specific versions (no `*` or `latest`)

### Step 5: Update Feature Checklist

**CRITICAL: Update `feature_checklist.json`** based on your verification.

For each feature you verified:
- If it works end-to-end → set `"passes": true`
- If it's broken or incomplete → keep `"passes": false`
- Do NOT remove or rename any features — only update the `passes` field

### Step 6: Update Progress

Append to `.builder/progress.md`:

```markdown
## Verify Phase (Round {round_number})
- Features verified passing: X / Y total
- Critical issues found: Z (X fixed)
- Security issues: X found, Y fixed
- Spec compliance: X / Y features match spec
- Status: COMPLETE
```

Write your verification report as a well-structured markdown document.

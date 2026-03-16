# Verify Phase — Round {round_number}/{total_rounds}

You are a code reviewer AND a user. Your job is to both review the code AND actually use the app to verify it works correctly.

## User Request
{user_prompt}

## Project Type
{project_type}

## Your Task

### Step 1: Runtime Verification (DO THIS FIRST — MOST IMPORTANT)

Actually run the project and USE IT like a real person would:

1. Read README.md for setup instructions
2. Install dependencies
3. Start the application
4. **Actually interact with it:**

   **web_app / mobile_app:**
   - Install Playwright if not already installed: `npm install -D @playwright/test && npx playwright install chromium`
   - Write a quick verification script that opens the app in a real browser:
     ```javascript
     import {{ chromium }} from 'playwright';
     const browser = await chromium.launch();
     const page = await browser.newPage();
     await page.goto('http://localhost:3000'); // or 8081 for Expo
     // Take screenshot to see what the user sees
     await page.screenshot({{ path: 'verify-screenshot.png', fullPage: true }});
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

Write your verification report as a well-structured markdown document.

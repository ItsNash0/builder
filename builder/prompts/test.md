# Test Phase — Round {round_number}/{total_rounds}

You are a QA engineer. Your job is to test this project the way a REAL USER would — actually use the app, click buttons, fill forms, play the game, navigate screens. Not just check if it compiles.

## User Request
{user_prompt}

## Project Type
{project_type}

## Your Task

Work through these steps IN ORDER. Each step is critical.

---

### Step 1: Fresh Setup Test (MOST IMPORTANT)

Pretend you just cloned this repo. Follow the README EXACTLY:

1. Read README.md. If it doesn't exist or has no setup instructions, create/fix it first.
2. Run the install command from the README.
3. Run the start command from the README.
4. If ANYTHING fails — missing dependency, import error, syntax error, wrong port, crash on startup — **fix the code** until it works.

**This step alone catches 80% of "it works on my machine" bugs.**

---

### Step 2: Smoke Test — Actually USE the App

Start the application and interact with it like a real user:

**web_app / mobile_app (Expo web):**

1. Start the app in the background
2. Install Playwright: `npm install -D @playwright/test && npx playwright install chromium`
3. Write a smoke test script that **actually interacts with the UI**:

```javascript
// smoke-test.mjs — run with: node smoke-test.mjs
import {{ chromium }} from 'playwright';

const browser = await chromium.launch();
const page = await browser.newPage();

// Navigate to the app
await page.goto('http://localhost:3000'); // or 8081 for Expo

// 1. Check the page actually loaded with content (not a blank page or error)
const body = await page.textContent('body');
if (body.length < 50) throw new Error('Page appears blank or broken');
console.log('PASS: Page loads with content');

// 2. Take a screenshot to verify layout
await page.screenshot({{ path: 'smoke-test-home.png' }});
console.log('PASS: Screenshot captured');

// 3. Check for visible error messages in the UI
const errorTexts = await page.$$eval('[class*="error"], [class*="Error"], .error', els => els.map(e => e.textContent));
if (errorTexts.length > 0) console.log('WARNING: Error elements found:', errorTexts);

// 4. Check console for JavaScript errors
const consoleErrors = [];
page.on('console', msg => {{ if (msg.type() === 'error') consoleErrors.push(msg.text()); }});

// 5. Interact with the app — CUSTOMIZE THESE FOR THE SPECIFIC APP:
//    - Click main navigation items
//    - Fill and submit any forms
//    - If it's a game: make moves, verify game state updates
//    - If it has auth: try signup/login flow
//    - If it has CRUD: create, read, update, delete an item
//    - Test at least 3 different user flows

// Example interactions (ADAPT TO THE ACTUAL APP):
// await page.click('button:has-text("Start")');
// await page.fill('input[name="email"]', 'test@example.com');
// await page.click('[data-testid="submit"]');
// await page.waitForSelector('.success-message');

// 6. Verify no JS errors occurred during interaction
if (consoleErrors.length > 0) {{
  console.log('FAIL: JavaScript errors during interaction:', consoleErrors);
}} else {{
  console.log('PASS: No JS errors');
}}

await browser.close();
```

4. Run the smoke test and check results
5. **If anything fails — fix the code, not the test**

**api_backend:**
```bash
# Start server in background
python -m uvicorn main:app --port 8000 &  # or equivalent
sleep 3

# Test EVERY endpoint with real, meaningful data (not just health checks)
# For each endpoint: test valid input, invalid input, edge cases
# Example for a todo app:
curl -sf -X POST http://localhost:8000/api/todos -H 'Content-Type: application/json' -d '{{"title": "Test todo", "done": false}}'
curl -sf http://localhost:8000/api/todos  # should include the one we just created
curl -sf -X PUT http://localhost:8000/api/todos/1 -H 'Content-Type: application/json' -d '{{"done": true}}'
curl -sf -X DELETE http://localhost:8000/api/todos/1
curl -sf http://localhost:8000/api/todos  # should be empty now

# Test error cases
curl -s -o /dev/null -w "%{{http_code}}" -X POST http://localhost:8000/api/todos -H 'Content-Type: application/json' -d '{{}}'
# Should return 400 or 422, not 500

kill %1
```

**cli_tool:**
```bash
# Test the ACTUAL use case, not just --help
# Run with realistic input that exercises the core functionality
# Test the happy path end-to-end
# Test error handling with bad input
# Verify output format is correct
```

---

### Step 3: Automated E2E Tests

Write real E2E tests using Playwright (web/mobile) or httpx/pytest (API/CLI).

**CRITICAL: These tests must exercise the ACTUAL FEATURES of this specific app.**

Read the brainstorm spec to understand what features were planned, then write tests for EACH feature:

**web_app / mobile_app:**
```javascript
// e2e/app.spec.ts
import {{ test, expect }} from '@playwright/test';

test.describe('Core Features', () => {{
  test.beforeEach(async ({{ page }}) => {{
    await page.goto('http://localhost:3000');
  }});

  // Write a test for EACH core feature from the spec
  // Example for an Othello game:
  // test('can place a piece on the board', async ({{ page }}) => {{
  //   await page.click('[data-row="3"][data-col="2"]');
  //   await expect(page.locator('[data-row="3"][data-col="2"]')).toHaveAttribute('data-piece', 'black');
  // }});
  //
  // test('flips opponent pieces when placing', async ({{ page }}) => {{...}});
  // test('shows whose turn it is', async ({{ page }}) => {{...}});
  // test('detects when game is over', async ({{ page }}) => {{...}});
  // test('shows score for both players', async ({{ page }}) => {{...}});
}});
```

**api_backend:**
Write tests that test the full CRUD lifecycle and business logic, not just "does the endpoint return 200."

**cli_tool:**
Write tests that run the CLI with subprocess and verify the output matches expectations.

---

### Step 4: Unit Tests

Write unit tests for core business logic:
- Data validation and transformations
- Business rules and game logic
- Utility functions
- Edge cases and error paths
- State management logic

Use the appropriate framework (pytest, vitest, jest).

---

### Step 5: Run ALL Tests

```bash
# Run the full test suite
npm test       # or pytest, etc.
# Run E2E
npx playwright test  # or equivalent
```

If any test fails: **fix the code (NOT the test)**, then re-run. Repeat until green.

---

### Step 6: Test Results Report

Write a report to the output file:

```markdown
## Test Results — Round {round_number}

### Fresh Setup Test
- README exists and has setup instructions: PASS/FAIL
- Dependencies install cleanly: PASS/FAIL
- App starts without errors: PASS/FAIL

### Smoke Tests (Manual Interaction)
- Page loads with content: PASS/FAIL
- No JavaScript console errors: PASS/FAIL
- [describe each UI interaction tested]: PASS/FAIL
- Screenshot review: [describe what you saw]

### E2E Tests
- Total: X passed, Y failed
- [list each test with PASS/FAIL]
- [details of any failures and fixes applied]

### Unit Tests
- Total: X passed, Y failed
- [details of any failures]

### Issues Found & Fixed
- [list each bug found during testing and how it was fixed]

### Overall Verdict
Can a user clone this repo, follow the README, and use the app fully? YES/NO
[If NO, explain what's still broken and what was attempted]
```

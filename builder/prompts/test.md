# Test Phase — Round {round_number}/{total_rounds}

You are a QA engineer. Your job is to test this project the way a REAL USER would — actually use the app, interact with every feature, and verify online functionality works end-to-end.

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
4. If ANYTHING fails — missing dependency, import error, syntax error, crash — **fix the code** until it works.

---

### Step 2: Smoke Test — Actually USE the App

Start the application and interact with it like a real user using Playwright + Lightpanda:

**IMPORTANT: Use Lightpanda browser instead of Chromium.** Lightpanda is a lightweight headless browser that's 11x faster and uses 9x less memory than Chrome. It's already installed on this system.

To connect Playwright to Lightpanda:
1. Start Lightpanda: `lightpanda serve --host 127.0.0.1 --port 9222 &`
2. Connect via CDP: `chromium.connectOverCDP('http://127.0.0.1:9222')`
3. Do NOT use `chromium.launch()` — always use `connectOverCDP`
4. Do NOT run `npx playwright install chromium` — Lightpanda replaces it

**web_app / mobile_app (Expo web):**

1. Start the app in the background
2. Start Lightpanda: `lightpanda serve --host 127.0.0.1 --port 9222 &`
3. Write a smoke test that **actually interacts with the UI**:

```javascript
// smoke-test.mjs
import {{ chromium }} from 'playwright';

// Connect to Lightpanda (NOT chromium.launch())
const browser = await chromium.connectOverCDP('http://127.0.0.1:9222');
const context = browser.contexts()[0] || await browser.newContext();
const page = context.pages()[0] || await context.newPage();
await page.goto('http://localhost:3000');

// 1. Verify page loads with real content
const body = await page.textContent('body');
if (body.length < 50) throw new Error('Page appears blank');
console.log('PASS: Page loads');

// 2. Screenshot for visual verification
await page.screenshot({{ path: 'smoke-home.png', fullPage: true }});

// 3. Check for JS errors
const errors = [];
page.on('console', msg => {{ if (msg.type() === 'error') errors.push(msg.text()); }});

// 4. INTERACT WITH EVERY FEATURE - customize for this specific app:
//    - Navigate to every page/screen
//    - Fill and submit forms
//    - Click buttons and verify responses
//    - If auth: test signup → login → protected page → logout
//    - If CRUD: create → read → update → delete
//    - If game: make moves, verify state updates
//    - If real-time: verify live updates appear

// 5. Report results
if (errors.length > 0) {{
  console.log('FAIL: JS errors:', errors);
}} else {{
  console.log('PASS: No JS errors');
}}
await browser.close();
```

3. Run and check results. **Fix code, not tests.**

---

### Step 3: Supabase / Online Feature Testing (CRITICAL for apps with backend)

If the app uses Supabase or any online features, test them FOR REAL:

**You may have access to Supabase MCP tools.** If available, use them to verify data actually reaches the database:
- `execute_sql` — run SELECT queries to verify rows were created/updated/deleted
- `list_tables` — confirm the schema matches what the app expects
- `get_logs` — check for auth or database errors in Supabase logs

**Auth Flow:**
```javascript
// Test the complete auth flow in the browser
// 1. Navigate to signup page
// 2. Fill in email + password
// 3. Submit the form
// 4. Verify redirect to dashboard/home
// 5. Check that auth state persists (refresh page, still logged in)
// 6. Test logout
// 7. Verify protected routes redirect to login when not authenticated
```
After auth tests, if Supabase MCP is available:
- Use `execute_sql` to verify the user was created in `auth.users`
- Verify RLS policies work: query as the user vs. as anon

**Database CRUD:**
```javascript
// Test create, read, update, delete through the UI
// 1. Create a new item via the UI form
// 2. Verify it appears in the list
// 3. Edit the item
// 4. Verify changes are reflected
// 5. Delete the item
// 6. Verify it's gone
```
After CRUD tests, if Supabase MCP is available:
- Use `execute_sql` to verify the row exists in the actual table
- After delete, verify the row is gone from the database too

**Real-time Features:**
```javascript
// If the app has real-time features:
// 1. Open two browser contexts (simulating two users)
// 2. Make a change in one
// 3. Verify it appears in the other WITHOUT refreshing
```

**If Supabase is not configured (no real keys):**
- Test that the app gracefully handles missing Supabase connection
- Verify error messages are user-friendly, not raw stack traces
- Test that offline/mock mode works if implemented
- Document what would need to be tested once Supabase is connected

---

### Step 4: E2E Tests with Playwright + Lightpanda

**Configure Playwright to use Lightpanda.** Create or update `playwright.config.ts`:

```typescript
// playwright.config.ts
import {{ defineConfig }} from '@playwright/test';

export default defineConfig({{
  testDir: './e2e',
  use: {{
    // Connect to Lightpanda instead of launching Chromium
    connectOptions: {{
      wsEndpoint: 'ws://127.0.0.1:9222',
    }},
    baseURL: 'http://localhost:3000', // or 8081 for Expo
  }},
  // Start Lightpanda before tests
  webServer: [
    {{
      command: 'lightpanda serve --host 127.0.0.1 --port 9222',
      port: 9222,
      reuseExistingServer: true,
    }},
    {{
      command: 'pnpm dev',
      port: 3000, // adjust for your app
      reuseExistingServer: true,
    }},
  ],
}});
```

Write proper Playwright test files that test EACH feature from the spec:

```typescript
// e2e/app.spec.ts
import {{ test, expect }} from '@playwright/test';

test.describe('Core Features', () => {{
  test.beforeEach(async ({{ page }}) => {{
    await page.goto('/');
  }});

  // Write a test for EACH core feature
  // Tests should use real UI interactions, not API calls
  // Include assertions on visible content, not just HTTP status
}});
```

For apps with auth, create a test helper:
```typescript
// e2e/helpers/auth.ts
// Helper to sign in before tests that need authentication
```

---

### Step 5: Unit Tests

Write unit tests for:
- Business logic and data transformations
- Utility functions and helpers
- Form validation rules
- State management logic
- Edge cases and error paths

Use vitest (web) or jest (Expo/mobile).

---

### Step 6: Run ALL Tests

```bash
pnpm test               # unit tests
npx playwright test      # E2E tests
```

If any test fails: **fix the code (NOT the test)**, then re-run. Repeat until green.

---

### Step 7: Test Results Report

Write a detailed report:

```markdown
## Test Results — Round {round_number}

### Fresh Setup
- README exists: PASS/FAIL
- Install works: PASS/FAIL
- App starts: PASS/FAIL

### Smoke Tests
- Page loads: PASS/FAIL
- No JS errors: PASS/FAIL
- [each interaction tested]: PASS/FAIL

### Online Features (Supabase)
- Auth signup: PASS/FAIL/SKIPPED
- Auth login: PASS/FAIL/SKIPPED
- Auth logout: PASS/FAIL/SKIPPED
- CRUD operations: PASS/FAIL/SKIPPED
- Real-time updates: PASS/FAIL/SKIPPED
- Error handling (no connection): PASS/FAIL

### E2E Tests
- Total: X passed, Y failed
- [list each test]

### Unit Tests
- Total: X passed, Y failed

### Issues Found & Fixed
- [each bug and fix]

### Overall Verdict
Can a user clone, setup, and fully use this app? YES/NO
```

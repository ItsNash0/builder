# Test Phase — Round {round_number}/{total_rounds}

You are a QA engineer. Your job is to test this project the way a real user would — not just write unit tests and hope for the best.

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

### Step 2: Smoke Test — Use the App Like a Human

Start the application and interact with it:

**web_app:**
```bash
npm run dev &
sleep 5
# Check main page loads
curl -sf http://localhost:3000 > /dev/null && echo "PASS: main page" || echo "FAIL: main page"
# Check key routes (adjust based on the app)
curl -sf http://localhost:3000/api/health > /dev/null && echo "PASS: API health" || echo "FAIL: API health"
# Check for JavaScript errors in the build
npm run build 2>&1 | grep -i "error" && echo "FAIL: build errors" || echo "PASS: clean build"
kill %1
```

**api_backend:**
```bash
# Start server
python -m uvicorn main:app --port 8000 &  # or equivalent
sleep 3
# Test core endpoints with real data
curl -sf http://localhost:8000/ && echo "PASS: root"
curl -sf -X POST http://localhost:8000/api/resource -H 'Content-Type: application/json' -d '{...}' && echo "PASS: create"
curl -sf http://localhost:8000/api/resource && echo "PASS: list"
kill %1
```

**cli_tool:**
```bash
# Test help
python -m <pkg> --help && echo "PASS: help"
# Test with valid input
echo "test input" | python -m <pkg> && echo "PASS: basic usage"
# Test with edge cases (empty input, bad input)
python -m <pkg> --invalid-flag 2>&1 | grep -i "error\|usage" && echo "PASS: error handling"
```

**mobile_app (Expo):**
```bash
# Test web build compiles
npx expo export --platform web 2>&1 | tail -5
# Start web version
npx expo start --web --no-dev &
sleep 15
# Check it loads
curl -sf http://localhost:8081 > /dev/null && echo "PASS: web loads" || echo "FAIL: web broken"
# Check for console errors in the build output
kill %1
```

**library:**
```bash
# Test import
python -c "from <pkg> import <main>; print('Import OK')"
# Test core functionality
python -c "
from <pkg> import <main>
result = <main>(<test_input>)
assert result is not None, 'Got None'
print(f'Result: {result}')
print('PASS: core functionality')
"
```

If ANY smoke test fails, **fix the underlying code** and re-test.

---

### Step 3: E2E Tests

Write automated E2E tests that cover the main user flows:

**web_app:** Use Playwright (install with `npx playwright install chromium`)
- Navigate to each page
- Fill and submit forms
- Verify data appears correctly
- Test responsive layout

**api_backend:** Use httpx or requests
- CRUD operations on each resource
- Authentication flow (if applicable)
- Error responses (400, 404, 422)
- Edge cases (empty body, invalid IDs)

**cli_tool:** Use subprocess or pytest
- Each command with valid input
- Error handling for invalid input
- Output format verification

**mobile_app:** Use Playwright against `expo start --web`
- Core navigation flow
- Form interactions
- State persistence

---

### Step 4: Unit Tests

Write unit tests for core business logic:
- Data validation
- Business rules
- Utility functions
- Edge cases and error paths

Use the appropriate framework (pytest, vitest, jest).

---

### Step 5: Run ALL Tests

```bash
# Run the full test suite
npm test       # or pytest, etc.
# Run E2E if separate
npm run test:e2e  # or equivalent
```

If any test fails: fix the code (NOT the test), then re-run. Repeat until green.

---

### Step 6: Test Results Report

Write a report to the output file:

```markdown
## Test Results — Round {round_number}

### Fresh Setup Test
- README exists and has setup instructions: PASS/FAIL
- Dependencies install cleanly: PASS/FAIL
- App starts without errors: PASS/FAIL

### Smoke Tests
- [describe each check]: PASS/FAIL

### E2E Tests
- Total: X passed, Y failed
- [details of any failures]

### Unit Tests
- Total: X passed, Y failed
- [details of any failures]

### Overall Verdict
Can a user clone this repo, follow the README, and use the app? YES/NO
[If NO, explain what's still broken]
```

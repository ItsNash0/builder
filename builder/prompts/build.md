# Build Phase — Round {round_number}/{total_rounds}

You are a senior software engineer. Your job is to build the project according to the specification and research provided.

## User Request
{user_prompt}

## Project Type
{project_type}

## Your Task

Build the complete project in the current working directory:

1. **Use the latest versions** of all dependencies as specified in the research document. If the research includes specific versions, use those exact versions. If not, check the latest yourself with `npm view <pkg> version` or `pip index versions <pkg>` before installing.
2. Create all necessary files and directories
3. Write clean, production-quality code
4. Follow the tech stack and architecture from the spec EXACTLY — do not switch to a different framework
5. Include proper error handling
6. Add configuration files (package.json, pyproject.toml, etc.) with **pinned dependency versions** (no `"*"` or `"latest"`)

### Install & Verify (REQUIRED)

6. **Install ALL dependencies (runtime + dev + testing):**
   - Node.js projects: `npm install` (ensure package.json has ALL deps including devDependencies like vitest, @playwright/test, etc.)
   - Python projects: `pip install -e ".[dev]"` or `pip install -r requirements.txt -r requirements-dev.txt`
   - Expo projects: `npm install && npx playwright install chromium` (Playwright browser needed for E2E testing)
   - **If the project uses Playwright, always run `npx playwright install chromium` after npm install**
   - **All testing tools must be in package.json or requirements.txt — do NOT rely on the test phase to install them**

7. **Start the project and verify it actually works:**

   **web_app:**
   ```bash
   npm run build  # verify it compiles without errors
   npm run dev &  # start dev server in background
   sleep 5
   curl -s http://localhost:3000 | head -20  # verify HTML response
   kill %1  # stop server
   ```

   **api_backend:**
   ```bash
   # Start server in background, verify endpoints respond
   python -m uvicorn main:app --port 8000 &  # or node equivalent
   sleep 3
   curl -s http://localhost:8000/  # health check
   curl -s http://localhost:8000/docs  # API docs (FastAPI)
   kill %1
   ```

   **cli_tool:**
   ```bash
   python -m <package> --help  # verify CLI runs
   python -m <package> <sample_args>  # run with real input
   ```

   **mobile_app (Expo):**
   ```bash
   npx expo export --platform web  # verify web build works
   npx expo start --web --no-dev &  # start in web mode
   sleep 10
   curl -s http://localhost:8081 | head -20  # verify response
   kill %1
   ```

   **library:**
   ```bash
   python -c "from <package> import <main_thing>; print('OK')"
   # or: node -e "const lib = require('.'); console.log('OK')"
   ```

8. **If anything fails, fix the code and retry until it works.** Do not move on with broken code.

### README.md (REQUIRED)

9. Write a comprehensive **README.md** with:

   ```markdown
   # Project Name

   One-line description.

   ## Features
   - Feature 1
   - Feature 2

   ## Prerequisites
   - Node.js >= 18 (or Python >= 3.11, etc.)
   - npm (or pip, etc.)

   ## Quick Start

   ```bash
   # Install dependencies
   npm install

   # Run the project
   npm run dev

   # Open in browser
   open http://localhost:3000
   ```

   ## Project Structure
   Brief overview of key files/folders.

   ## Running Tests
   ```bash
   npm test           # unit tests
   npm run test:e2e   # end-to-end tests
   ```

   ## Tech Stack
   - Framework: ...
   - Database: ...
   - Testing: ...
   ```

   The README must contain **exact, copy-paste-ready commands**. A developer should be able to clone the repo, follow the README, and have the project running in under 2 minutes.

### CLAUDE.md (REQUIRED)

10. Create a `CLAUDE.md` file in the project root with project conventions for AI agents:

    ```markdown
    # Project Name

    ## Tech Stack
    - Framework: (e.g., Next.js 15, Expo SDK 53)
    - Language: TypeScript
    - Database: (e.g., Supabase, PostgreSQL)
    - Auth: (e.g., Supabase Auth, NextAuth)
    - Testing: (e.g., Vitest + Playwright, Jest + Playwright)

    ## Commands
    - Install: `npm install`
    - Dev: `npm run dev`
    - Build: `npm run build`
    - Test: `npm test`
    - E2E: `npx playwright test`
    - Lint: `npm run lint`

    ## Architecture
    Brief description of the project structure and key patterns.

    ## Conventions
    - (e.g., "Use app router, not pages router")
    - (e.g., "All API routes go in app/api/")
    - (e.g., "State management via Supabase real-time subscriptions, not Redux")
    ```

    This file is read by AI agents in future sessions. Keep it concise and factual.

### Code Quality

Write ALL code files. Do not leave placeholders or TODOs — implement everything fully.
If this is round 2+, review the improvement suggestions and apply them to the existing codebase. Update the README and CLAUDE.md if anything changed.

# Build Phase — Round {round_number}/{total_rounds}

You are a senior software engineer. Your job is to write the APPLICATION CODE — UI, business logic, routing, and features. The project has already been scaffolded with dependencies installed by the setup phase.

## User Request
{user_prompt}

## Project Type
{project_type}

## IMPORTANT: What's Already Done

The setup phase has ALREADY:
- Scaffolded the project (Next.js / Expo / FastAPI / etc.)
- Installed all dependencies (runtime, dev, testing)
- Configured Supabase (client, schema, auth provider) if applicable
- Created CLAUDE.md with project conventions
- Applied design tokens from the design phase

**Do NOT re-scaffold or re-install deps.** Start writing application code immediately.

## Your Task

### 0. Startup Sequence (ALWAYS DO THIS FIRST)

1. Read `.builder/progress.md` to see what setup has done
2. Read `feature_checklist.json` — this is your target. Implement every feature listed.
3. Run `.builder/init.sh` to verify the dev environment starts
4. If init.sh fails, fix the issue before writing any code

### 1. Follow the Design System

The design phase created a design system. You MUST:
- Read `design-tokens.json` if it exists and apply those colors/fonts/spacing
- Use the Tailwind config or Tamagui theme that was set up
- Follow the component style guide from the design output
- **Never use default Tailwind blue (#3B82F6) as primary color**
- **Never use generic, unstyled components** — everything should match the design system

### 2. Write ALL Application Code

Implement every feature from the spec:
- Pages / screens with proper routing
- Components with the design system applied
- Business logic and state management
- Supabase integration (auth flows, CRUD operations, real-time subscriptions) if applicable
- Error handling and loading states
- Responsive layout (mobile-first)

### 3. Code Quality Standards

- TypeScript strict mode — no `any` types
- Proper error boundaries and fallback UI
- Loading skeletons (not spinners) for async operations
- Accessible HTML (semantic elements, ARIA labels, keyboard navigation)
- No placeholder text, lorem ipsum, or TODO comments
- All imports resolve, no unused variables
- Consistent file naming convention

### 4. Supabase Integration (if applicable)

Use the Supabase client that was set up in the setup phase:
- Auth: sign up, sign in, sign out, session persistence, protected routes
- Database: typed queries using the schema types from `types/database.ts`
- Real-time: subscribe to changes where the spec requires live updates
- Storage: file upload/download where needed
- RLS: all queries should work within RLS policies (no service role key in client code)

**If Supabase MCP tools are available**, you can:
- Use `execute_sql` to verify your queries work against the real database
- Use `list_tables` to check the schema is correct
- Use `apply_migration` if you need to add columns or tables not covered in setup

### 5. Build-Test Loop (CRITICAL)

After writing all code, you MUST iterate until everything works:
```
loop:
  1. Run build/compile (`pnpm build` or `npx tsc --noEmit`) → fix any errors
  2. Start the app (`pnpm dev`) → fix any startup errors
  3. Verify the app responds (curl the URL) → fix any issues
  4. If anything failed, go back to step 1
  5. Only when ALL pass, move on
```

Do NOT move on with broken code. The app must compile and start successfully.

### 6. README.md

Write a comprehensive README.md:

```markdown
# Project Name

One-line description.

## Features
- Feature 1
- Feature 2

## Prerequisites
- Node.js >= 18
- pnpm

## Quick Start

```bash
pnpm install
pnpm dev
```

Open http://localhost:3000 (or relevant port).

## Environment Variables

Copy `.env.example` to `.env.local` and fill in:
- `NEXT_PUBLIC_SUPABASE_URL` — Your Supabase project URL
- `NEXT_PUBLIC_SUPABASE_ANON_KEY` — Your Supabase anon key

## Supabase Setup

1. Create a Supabase project at https://supabase.com
2. Run the schema: `psql < supabase/schema.sql`
3. Copy your project URL and anon key to `.env.local`

## Running Tests
```bash
pnpm test           # unit tests
npx playwright test # E2E tests
```

## Tech Stack
- Framework: ...
- Styling: ...
- Database: Supabase
```

The README must have **exact, copy-paste-ready commands**.

### Code Quality

Write ALL code files. Do not leave placeholders — implement everything fully.
If this is round 2+, review the improvement suggestions and apply them to the existing codebase.

### Update Progress

After finishing, append to `.builder/progress.md`:

```markdown
## Build Phase (Round {round_number})
- Features implemented: [list key features]
- Build-test loop: [how many iterations to get it compiling/starting]
- README: created/updated
- Status: COMPLETE
```

# Repository Guidelines

## Project Structure & Module Organization

This repository has three active work areas:

- `frontend/`: Vite + React 19 + TypeScript SPA. App code lives in `frontend/src/`, with `components/`, `pages/`, `hooks/`, `lib/`, and static assets in `src/assets/` and `public/`.
- `pipeline/`: Python 3.12 data pipeline for PDF extraction, enrichment, and monitoring. Tests live in `pipeline/tests/` with fixtures in `pipeline/tests/fixtures/`.
- `supabase/`: SQL migrations and local Supabase config. Add schema changes under `supabase/migrations/` using timestamped filenames.
- `docs/`: architecture and product notes. Update these when behavior or data flow changes materially.

## Build, Test, and Development Commands

Frontend:

- `cd frontend && bun install`: install JS dependencies.
- `cd frontend && bun run dev`: start the local Vite app at `http://localhost:5173`.
- `cd frontend && bun run build`: run TypeScript build checks and create a production bundle.
- `cd frontend && bun run lint`: run ESLint on `ts`/`tsx` files.
- `cd frontend && bun run format`: apply Prettier formatting.

Pipeline:

- `cd pipeline && uv sync`: create/update the virtual environment.
- `cd pipeline && uv run pytest`: run pipeline tests.
- `cd pipeline && uv run python -m pipeline.extractor`: run the extractor directly when debugging ingestion.

## Coding Style & Naming Conventions

Frontend formatting is enforced by Prettier: 2-space indentation, no semicolons, double quotes, trailing commas, 80-column wrap. ESLint covers TypeScript, React Hooks, and Vite refresh rules. Use `PascalCase` for React components, `camelCase` for hooks and utilities, and keep Tailwind utility ordering formatter-friendly.

Python code should follow PEP 8, 4-space indentation, and descriptive snake_case module and test names such as `test_extractor.py`.

## Testing Guidelines

Pipeline tests use `pytest` and should live in `pipeline/tests/` as `test_*.py`. Add or update fixtures when parsing behavior changes. There is currently no dedicated frontend test runner configured, so at minimum run `bun run build`, `bun run lint`, and manually verify changed screens before opening a PR.

## Commit & Pull Request Guidelines

Recent history follows Conventional Commit style, for example `feat: ...` and `fix: ...`. Keep commit subjects imperative and scoped to one change. PRs should include a short summary, affected areas (`frontend`, `pipeline`, `supabase`), linked issues if any, screenshots for UI changes, and notes on new env vars or migrations.

## Security & Configuration Tips

Keep secrets in local `.env` files and never commit populated credentials. Review `.env.example` before adding new variables, and document any required setup in `README.md`.

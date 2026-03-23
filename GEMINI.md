# TCU-TIME (Take It More Easily) - Gemini Context

This document provides essential information for Gemini to understand and work effectively within the TCU-TIME project.

## Project Overview

**TCU-TIME** is a modern course registration support application designed for graduate students at the Tokyo City University (TCU) Graduate School of Integrative Science and Engineering (総合理工学研究科). It replaces a legacy Flutter-based tool with a robust, automated system for searching courses, building timetables, and tracking credits.

### Core Tech Stack

- **Frontend:** React 19, Vite, TypeScript, Tailwind CSS 4, shadcn/ui.
- **Backend:** Supabase (PostgreSQL, PostgREST, Auth).
- **Data Pipeline:** Python 3.12 (uv), pdfplumber, Gemini (LLM-based extraction), BeautifulSoup4.
- **Infrastructure:** Cloudflare Pages (Hosting), GitHub Actions (Daily cron for data updates).

---

## Project Structure

```
TIME/
├── frontend/        # React SPA (Vite + TypeScript + Tailwind 4)
│   ├── src/
│   │   ├── components/  # UI components (shadcn/ui, layout, course, timetable, admin)
│   │   ├── hooks/       # Custom React hooks (use-courses, use-auth, etc.)
│   │   ├── lib/         # Utility functions and Supabase client
│   │   └── pages/       # Main page components
│   └── components.json  # shadcn/ui configuration
├── pipeline/        # Python data processing pipeline
│   ├── main.py      # Orchestrator
│   ├── extractor.py # PDF to structured JSON (pdfplumber + Gemini)
│   ├── enricher.py  # Syllabus scraping (BeautifulSoup)
│   ├── monitor.py   # Web monitoring for PDF updates
│   └── tests/       # Pytest suite
├── supabase/        # Database configuration
│   └── migrations/  # SQL migration files
├── docs/            # Design and architecture documentation
└── .github/         # CI/CD workflows (GitHub Actions)
```

---

## Building and Running

### Frontend (Bun)

```bash
cd frontend
bun install           # Install dependencies
bun run dev           # Start development server (http://localhost:5173)
bun run build         # Build for production
bun run lint          # Run ESLint
bun run typecheck     # Run TypeScript compiler checks
bun run format        # Format code with Prettier
```

### Data Pipeline (uv)

```bash
cd pipeline
uv sync               # Install dependencies and sync environment
uv run pytest         # Run tests
uv run python -m pipeline.main  # Run the full pipeline
uv run python -m pipeline.extractor  # Run extraction only
```

---

## Development Conventions

### General
- **Surgical Changes:** Favor precise edits over full-file rewrites.
- **Validation:** Always verify changes by running relevant build/test commands.
- **Environment Variables:** Use `.env` (root), `frontend/.env.local`, and `pipeline/.env` for secrets.

### Frontend (React/TypeScript)
- **Styling:** Use **Tailwind CSS 4** utility classes. Adhere to **shadcn/ui** patterns for components.
- **Components:** Functional components with TypeScript interfaces for props.
- **State Management:** Leverage React Hooks and Supabase's real-time/PostgREST capabilities.
- **Imports:** Use absolute paths where configured (e.g., `@/components/...`).

### Pipeline (Python)
- **Package Manager:** Strictly use **uv**.
- **Data Models:** Use **Pydantic** for structured data validation.
- **LLM Integration:** Use Gemini (via `google-genai`) for complex PDF table structure extraction.
- **Scraping:** Respect rate limits (default ~3s) when scraping TCU syllabus pages.

### Database (Supabase)
- **Migrations:** All schema changes must be documented in `supabase/migrations/`.
- **RLS:** Row Level Security (RLS) is used to protect user data; ensure policies are updated if new tables are added.

---

## Key Files for Reference

- `README.md`: High-level project summary.
- `docs/00_overview.md`: Detailed architectural vision.
- `docs/05_project_structure.md`: Folder-by-folder breakdown and roadmap.
- `frontend/package.json`: Frontend scripts and dependencies.
- `pipeline/pyproject.toml`: Pipeline dependencies and test configuration.
- `supabase/migrations/`: Source of truth for the database schema.

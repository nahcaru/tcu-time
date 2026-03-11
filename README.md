# TCU-TIME (Take It More Easily)

Tokyo City University graduate school (総合理工学研究科) course registration support app.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Vite + React 19 + TypeScript + Tailwind CSS 4 + shadcn/ui |
| Backend | Supabase (PostgreSQL + PostgREST + Auth) |
| Data Pipeline | Python 3.12 (pdfplumber + Gemini + BeautifulSoup) |
| Hosting | Cloudflare Pages |
| CI/CD | GitHub Actions (daily pipeline cron) |

## Project Structure

```
TIME/
├── frontend/        # Vite + React SPA
├── pipeline/        # Python data extraction pipeline
├── supabase/        # Database migrations & RLS policies
├── Docs/            # Design documents
├── References/      # Legacy code reference (read-only)
└── .github/         # CI/CD workflows
```

## Development

### Frontend

```bash
cd frontend
bun install
bun run dev          # http://localhost:5173
bun run build        # Production build
bun run typecheck    # Type checking
bun run lint         # ESLint
```

### Pipeline

```bash
cd pipeline
uv sync
uv run pytest        # Run tests
uv run python -m pipeline.extractor   # Run extractor
```

### Environment Variables

Copy the example files and fill in your credentials:

```bash
cp .env.example .env
cp frontend/.env.local.example frontend/.env.local
```

## License

Private project - Tokyo City University internal use.

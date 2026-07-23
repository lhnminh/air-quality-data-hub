# AirTrace frontend

This folder contains the dashboard that people see in their browser.

## Files your team will edit

| File | What it does |
|---|---|
| `app/page.tsx` | Builds the dashboard and requests DuckDB rows from the Python API. |
| `app/mock-data.ts` | Provides clearly labeled sample data when the API is unavailable. |
| `app/globals.css` | Controls colors, spacing, desktop layout, and mobile layout. |
| `app/layout.tsx` | Sets the browser tab title and page description. |

The remaining files are build settings used by Next.js. You normally do not
need to change them.

## Run the dashboard locally

The dashboard and Python API run in two separate terminal windows.

### Terminal 1: start the Python API

From the main project folder:

```bash
uv run uvicorn api:app --reload --port 8000
```

The API reads existing rows from `data/airtrace.duckdb`. It does not make a new
IQAir request.

### Terminal 2: start the frontend

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:3000>.

- **Reading DuckDB** means the Python API returned real database rows.
- **Demo data** means the API was unavailable or the database was empty.

## Check the frontend

```bash
npm run lint
npm test
```

`npm test` creates a production build and checks that the important dashboard
content appears in the generated page.

## Later deployment note

The frontend is intended for Vercel. DuckDB is suitable for this local demo,
but Vercel does not provide persistent disk storage for collected data. Before
deployment, the project will need a hosted database and a deployed API URL.

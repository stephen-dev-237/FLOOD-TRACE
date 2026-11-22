# FloodTrace V2 — Complete Combined Build

The package contains the latest V2 frontend and the complete Python backend.

## One-click run (Windows)
Extract the ZIP and double-click `START_FLOODTRACE.bat`.

- Dashboard: http://127.0.0.1:5500/
- API health: http://127.0.0.1:8000/api/health

The launcher checks dependencies, starts FastAPI, waits for its health endpoint, starts the dashboard server, and opens the browser.

Stop both services with `STOP_FLOODTRACE.bat`.

Keep the entire `FloodTrace_V2` directory structure intact.

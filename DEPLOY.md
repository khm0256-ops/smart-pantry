# Deploy Smart Home Flask App

This app is a Flask server. Static hosts like Cloudflare Pages only serve files, not Python servers. Use a platform that runs Python (Render, Railway, Fly.io, Azure Web Apps, etc.).

## Files added
- `requirements.txt`: Flask, requests, gunicorn
- `Procfile`: starts the app via gunicorn and binds to `$PORT`

## Render (recommended)
1. Push this folder to a repo (GitHub/GitLab).
2. Create a new **Web Service** on Render and connect the repo.
3. Set:
   - **Build Command**: `pip install -r Home/requirements.txt`
   - **Start Command**: `cd Home && gunicorn home_app:app --bind 0.0.0.0:$PORT`
   - **Environment**: `PYTHON_VERSION=3.11` (optional)
4. Deploy. Render sets `$PORT` automatically.

## Railway
1. Create a new project, add the repo.
2. Service -> **Start Command**: `gunicorn home_app:app --bind 0.0.0.0:$PORT`
3. Install deps: `pip install -r requirements.txt` (or specify in build step).

## Notes
- Database path: the app saves SQLite at `~\\smart_pantry.db`. On most platforms this is ephemeral; for persistence use a managed DB (e.g., Postgres) or configure a persistent volume.
- Local run: `python Home/run.py` opens `http://127.0.0.1:5002`.
- Static `index.html` exists in `Home/templates/index.html`, but it needs the Flask server to render and provide features.

## Cloudflare Pages
Cloudflare Pages is **static-only** (unless using Pages Functions with Node). It cannot host Flask. You can deploy a landing page there that links to your Render/Railway backend URL.

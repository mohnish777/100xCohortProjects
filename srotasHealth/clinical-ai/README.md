# Srotas Health Backend

FastAPI backend for trial uploads, patient creation, matching, AI-assisted matching, and voice summaries.

## Local run

1. Create a virtual environment and install dependencies:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2. Copy `.env.example` to `.env` and fill in the real keys.

3. Start the API:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

4. Open `http://localhost:8000/docs` to test the endpoints.

## Docker run

```bash
docker build -t srotas-health-api .
docker run --env-file .env -p 8000:8000 srotas-health-api
```

## Deploy

This backend is ready for container-based deployment on platforms like Render, Railway, Fly.io, or an EC2/Droplet VM.

Use these settings:

- Root directory: `srotasHealth/clinical-ai`
- Build: Dockerfile
- Port: provided by the platform as `PORT`
- Start command: already defined in the Docker image

Set these environment variables on the platform:

- `GEMINI_API_KEY`
- `ELEVENLABS_API_KEY`
- `SUPABASE_URL`
- `SUPABASE_KEY`
- `ALLOWED_ORIGINS`

## API base URL for Android

After deployment, your Android app should use a base URL like:

```text
https://your-backend-domain.com
```

Example endpoints:

- `GET /health`
- `POST /trial/upload`
- `POST /patient/add`
- `POST /match`
- `POST /match-ai`
- `POST /agent/run`
- `POST /voice/run`

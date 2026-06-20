# Srotas Agentic Trials POC

Mixed-oncology adaptive trial matching POC for Srotas Health.

The demo story:

1. A patient speaks to an AI intake agent.
2. The agent extracts structured oncology facts from the conversation.
3. A coordinator uploads or selects a trial protocol.
4. The protocol agent discovers required clinical facts.
5. The fact registry stores new requirements without changing the database schema.
6. The matching agent ranks patients, explains eligibility, and flags missing facts.
7. The voice follow-up agent prepares outreach tasks for missing data.

## Project Shape

```text
backend/   FastAPI API, OpenAI/ElevenLabs/Supabase integrations
frontend/  React + Vite dashboard and patient intake UI
supabase/  SQL schema and seed data
docs/      Step-by-step implementation notes
```

## Founder Diagram

- Excalidraw board: `docs/srotas-adaptive-trial-agent.excalidraw`
- Notes: `docs/DIAGRAM_NOTES.md`

## Implementation Reviews

- Step 1: `docs/STEP_1_REVIEW.md`
- Step 2: `docs/STEP_2_REVIEW.md`
- Step 3: `docs/STEP_3_REVIEW.md`
- Step 4: `docs/STEP_4_REVIEW.md`

## Model Defaults

Use `gpt-5.5` with `medium` reasoning effort for normal development and fast demo paths.
Use `high` only for demo-critical extraction or mapping tasks, such as protocol criteria extraction.

## Local Run

Backend:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Frontend:

```bash
cd frontend
nvm use
npm install
npm run dev
```

If your shell still picks `/usr/local/bin/node` v14, run with Node 18 first in PATH:

```bash
PATH=/Users/mchittoory_1/.nvm/versions/node/v18.20.8/bin:$PATH npm run dev
```

Demo API:

```bash
curl http://localhost:8000/api/demo/clinical-memory
```

Protocol-learning simulation:

```bash
curl -X POST http://localhost:8000/api/demo/run-protocol-learning
```

PDF protocol upload:

```bash
curl -X POST \
  -F "file=@/path/to/protocol.pdf" \
  http://localhost:8000/api/demo/upload-protocol
```

# Step 1 Review: Project Scaffold

This step creates a clean project instead of extending the older `srotasHealth/clinical-ai` backend.

## What Exists Now

- `frontend/`: React + Vite app for the patient intake and coordinator cockpit UI.
- `backend/`: FastAPI app with CORS and a health endpoint.
- `supabase/`: placeholder for the next step, where the database schema and seed data will live.
- `.env.example`: shared environment variable reference for OpenAI, ElevenLabs, Supabase, and frontend API URL.
- `.nvmrc`: pins the frontend to Node 18.20.8 because `/usr/local/bin/node` is Node 14 on this machine.

## Why This Shape

- React is best for the polished founder-facing dashboard.
- FastAPI keeps the AI, PDF, voice, and database logic in Python.
- Supabase/Postgres will store real demo data.
- The app will use a flexible fact model instead of changing patient-table columns for every new medical field.

## Next Step

Step 2 will add the Supabase schema:

- `patients`
- `intake_sessions`
- `clinical_facts`
- `patient_fact_values`
- `trials`
- `trial_criteria`
- `match_runs`
- `follow_up_tasks`

# Step 9 Review: Supabase Persistence Wiring

This step adds the durable storage path behind the working demo flow.

## What Changed

- Added `backend/app/data/supabase_persistence.py`.
- Added `GET /api/demo/storage-status`.
- Added frontend storage badge:
  - `Memory storage`
  - `Supabase dual-write`
- Demo patient and trial IDs now use stable UUIDs to match the Supabase schema.
- Reset, intake extraction, protocol extraction, matching, and follow-up task changes now attempt to
  persist to Supabase when credentials are configured.
- If Supabase is not configured or a DB write fails, the POC continues using the in-memory state.

## Current Local Status

Supabase is not configured in the local `.env` yet, so the app reports:

```text
storage_mode = memory_only
```

Once these are added:

```text
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
```

the app reports:

```text
storage_mode = supabase_dual_write
```

## What Gets Persisted

The persistence adapter writes:

- `patients`
- `clinical_facts`
- `patient_fact_values`
- `trials`
- `trial_criteria`
- `protocol_extractions`
- `follow_up_tasks`
- `match_runs`
- `match_run_patients`

## Why Dual-Write

The UI still reads from the fast demo session, but every state transition writes to Supabase when
available. That keeps the founder demo responsive while giving us a real database record behind it.

This is a good POC compromise:

- demo does not break if Supabase is unavailable
- database tables get populated when credentials exist
- next step can switch reads from memory to Supabase

## Setup Needed Before Real DB Test

Run `supabase/schema.sql` in the Supabase SQL editor.

Then add to `backend/.env`:

```text
SUPABASE_URL=...
SUPABASE_SERVICE_ROLE_KEY=...
```

Restart the backend and check:

```bash
curl http://localhost:8000/api/demo/storage-status
```

Expected:

```json
{
  "storage_mode": "supabase_dual_write",
  "supabase_url_configured": true,
  "supabase_service_role_key_configured": true
}
```

## Next Step

Step 10 should switch read paths to Supabase for:

- loading the active patient
- loading stored patient facts
- loading stored protocol criteria by `protocol_hash`

At that point, protocol reuse will survive backend restarts.

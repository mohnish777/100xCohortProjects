# Step 2 Review: Clinical Memory Schema

This step adds the storage shape behind the demo idea.

## What Exists Now

- `supabase/schema.sql`: real Postgres tables for patients, intake sessions, fact definitions, patient fact values, trials, criteria, match runs, and follow-up tasks.
- `supabase/seed.sql`: synthetic oncology demo rows for lung, breast, and prostate patients.
- `backend/app/domain/models.py`: typed API contracts that mirror the database shape.
- `backend/app/data/demo_repository.py`: in-memory demo data using the same shape as Supabase.
- `backend/app/api/demo.py`: `GET /api/demo/clinical-memory` for the frontend dashboard.
- `frontend/src/App.tsx`: data-driven dashboard that reads the clinical-memory snapshot.

## The Key Logic

The patient table stays stable. New clinical variables are stored as rows:

- `clinical_facts.key = pd_l1_tps`
- `patient_fact_values.patient_id = p_lung_014`
- `patient_fact_values.fact_key = pd_l1_tps`
- `patient_fact_values.value_numeric = 70`

That is how the same table can store future facts without the agent running `ALTER TABLE`.

## Demo Behavior

The synthetic lung protocol requires:

- lung cancer
- NSCLC histology
- metastatic disease
- PD-L1 TPS >= 50

The dashboard now shows:

- one eligible lung patient
- one possible lung match missing `pd_l1_tps`
- two excluded mixed-oncology patients
- one follow-up task asking for PD-L1 TPS
- the generated SQL preview for the selected protocol

## Next Step

Step 3 should add the first real workflow action: protocol extraction simulation. The user should be
able to click a demo protocol, see extracted criteria register a new fact, and watch follow-up tasks
appear.

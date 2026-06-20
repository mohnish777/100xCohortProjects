# Step 10 Review: Supabase Reads And Persistent Protocol Reuse

This step makes Supabase useful after backend restarts.

## What Changed

- Dashboard state can hydrate from Supabase on a fresh backend process.
- Stored patient facts and trial criteria are loaded back into the in-memory matcher.
- Protocol upload checks Supabase `protocol_extractions` by `protocol_hash` before calling OpenAI.
- If a PDF was already extracted and stored, the backend can reuse the saved criteria after restart.

## Read Flow

When `/api/demo/clinical-memory` is called and memory is empty:

1. Load active patient from `patients`.
2. Load fact registry from `clinical_facts`.
3. Load patient facts from `patient_fact_values`.
4. Load active trial from `trials`.
5. Load criteria from `trial_criteria`.
6. Recompute matching in memory for fast dashboard rendering.

## Persistent Protocol Reuse

On upload:

1. Compute SHA-256 hash of the PDF bytes.
2. Check in-memory protocol cache.
3. Check Supabase `protocol_extractions`.
4. If found, reuse extracted facts/criteria.
5. If not found, extract with the Protocol Agent and store the result.

## Migration Note

If you ran `supabase/schema.sql` before Step 10, run this SQL once:

```sql
alter table protocol_extractions
  add column if not exists trial_title text,
  add column if not exists cancer_track text,
  add column if not exists protocol_summary text;
```

The backend has a compatibility fallback if these optional columns are missing, but adding them makes
stored protocol reuse cleaner.

## Verified

Fresh-process hydration was tested:

```text
written_facts = 4
written_criteria = 3
hydrated_facts = 4
hydrated_criteria = 3
matches = eligible
```

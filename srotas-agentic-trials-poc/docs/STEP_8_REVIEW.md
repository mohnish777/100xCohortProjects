# Step 8 Review: Reactive Matching And Protocol Reuse

This step fixes two founder-demo issues.

## What Changed

- Follow-up answers now refresh the live dashboard match state.
- The visible protocol run is patched with the latest `matches` and `follow_up_tasks`.
- Uploaded PDFs are fingerprinted with a SHA-256 `protocol_hash`.
- If the same PDF is uploaded again, the backend reuses the already extracted facts and criteria.
- The UI shows whether the protocol was a new extraction or reused stored criteria.
- Supabase schema now includes:
  - `trials.protocol_hash`
  - `protocol_extractions`

## Reactive Match Flow

1. Patient gives partial intake.
2. Intake Agent stores known facts.
3. Protocol Agent extracts criteria.
4. Matching Agent marks patient as `possible_match`.
5. Follow-up task appears for the required missing fact.
6. Patient answers the follow-up.
7. Intake Agent stores the new fact.
8. Dashboard refreshes and the match updates immediately.

## Protocol Reuse Flow

1. Coordinator uploads a PDF.
2. Backend computes `protocol_hash`.
3. If hash is new, Protocol Agent extracts facts and criteria.
4. Extracted protocol data is cached in the demo protocol store.
5. If the same PDF is uploaded again, the backend skips the model call and reuses the stored
   extraction.

For the 24-hour POC, runtime reuse is powered by a backend cache. The Supabase schema is now ready
for the permanent version where `protocol_extractions`, `trials`, and `trial_criteria` hold this data
across server restarts.

## What Founders Should See

First upload:

```text
New extraction stored
```

Second upload of the same PDF:

```text
Reused stored criteria
```

The patient match should update without manually refreshing the page.

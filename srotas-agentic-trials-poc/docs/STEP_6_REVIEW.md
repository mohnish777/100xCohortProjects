# Step 6 Review: Patient Intake Agent

This step adds the patient-side agent loop.

## What Changed

- Added intake-specific domain models in `backend/app/domain/models.py`.
- Added `backend/app/services/intake_agent.py`.
- Added `POST /api/demo/run-intake-agent`.
- The frontend Patient Voice Intake panel now supports guided browser voice input.
- The avatar asks intake questions using browser text-to-speech.
- Browser speech recognition captures patient answers into the transcript.
- The dashboard shows:
  - agent mode
  - inferred cancer track
  - extracted patient facts
  - evidence quotes
  - missing facts
  - follow-up questions

## What The Intake Agent Does

The frontend first builds a transcript from avatar/patient turns:

```text
Avatar: What type of cancer were you diagnosed with?
Patient: I have lung cancer.
```

Then the backend agent reads that patient or caregiver history and extracts facts like:

- `cancer_type`
- `histology`
- `metastatic`
- `pd_l1_tps`
- `egfr_mutation`
- `prior_immunotherapy`
- `her2_status`
- `psa`

It uses OpenAI structured extraction when `OPENAI_API_KEY` is configured. If OpenAI is unavailable
or slow, it falls back to deterministic extraction so the demo still works.

## Why This Is Not Persisting Yet

Step 6 previews the extracted values but does not write them to Supabase yet.

That is intentional. The flow is easier to understand in two pieces:

1. Extract structured facts from free text.
2. Store approved facts as rows in `patient_fact_values`.

Step 7 should add the write path.

## Where The Values Will Go

When persistence is enabled, each extracted fact becomes one row:

```text
patient_fact_values
- patient_id
- fact_key
- value
- display_value
- evidence
- confidence
```

Example:

```text
patient_id: p_lung_014
fact_key: histology
value: NSCLC
display_value: NSCLC
evidence: "My report says NSCLC"
confidence: 0.98
```

If a fact is missing, it does not become a fake value. It becomes a follow-up question that can later
be stored in `follow_up_tasks`.

## Code Path

1. User clicks Ask question:

```text
frontend/src/App.tsx -> askAvatarQuestion()
```

2. Browser speaks the question and captures the answer:

```text
frontend/src/App.tsx -> speakAvatarQuestion()
frontend/src/App.tsx -> startVoiceCapture()
```

3. User clicks Extract facts:

```text
frontend/src/App.tsx -> runIntakeAgent()
```

4. FastAPI receives the transcript:

```text
backend/app/api/demo.py -> run_intake_agent()
```

5. Intake Agent extracts structured values:

```text
backend/app/services/intake_agent.py -> extract_intake_with_agent()
```

6. Frontend renders:

```text
extracted_facts
missing_facts
follow_up_questions
trace_notes
```

## Next Step

Step 7 should persist intake results:

- write extracted facts into `patient_fact_values`
- create missing-data rows in `follow_up_tasks`
- refresh match results after intake

# Step 7 Review: Stateful Demo Session And Follow-Up Loop

This step turns the demo from fixed sample data into a resettable patient session.

## What Changed

- The live backend now starts with one active demo patient instead of several synthetic patients.
- The patient name entered in the UI is stored as the active patient's display name.
- `Clear demo data` resets the backend session, transcript, protocol run, intake run, and follow-up UI.
- Intake extraction now stores facts in the backend session as `patient_fact_values`.
- Protocol extraction stores trial criteria in the backend session.
- Matching runs against the real stored patient facts and real extracted protocol criteria.
- Follow-up tasks are created only when required protocol facts are missing.
- The Follow-up Queue can simulate a call back to the patient.

## Demo Flow

1. Clear demo data.
2. Enter the patient name.
3. Avatar asks intake questions.
4. Patient answers but intentionally misses a required detail.
5. Intake Agent stores the facts it can prove.
6. Coordinator uploads or runs a protocol.
7. Matching Agent compares stored patient facts to protocol criteria.
8. If a required fact is missing, the patient appears as a possible match.
9. Voice Follow-up Agent creates a call task.
10. User clicks Call patient.
11. Patient answers the follow-up question.
12. Intake Agent extracts the new value and matching refreshes.

## What Is Real

The match status is not mocked. It is computed from:

```text
patient_fact_values
trial_criteria
```

If a required criterion fails, the patient is excluded. If a required value is missing, the patient is
a possible match. If all required criteria pass, the patient is eligible.

## What Is Simulated

The callback is an in-app browser simulation. It proves the agent loop, but it is not a real phone
call yet.

Real outbound calls should be a later integration with a calling provider such as Twilio, Retell,
Vapi, or ElevenLabs Conversational AI.

## Code Path

Reset session:

```text
frontend/src/App.tsx -> resetDemoSession()
backend/app/api/demo.py -> reset_session()
backend/app/data/demo_repository.py -> reset_demo_session()
```

Store intake facts:

```text
frontend/src/App.tsx -> runIntakeAgent()
backend/app/api/demo.py -> run_intake_agent()
backend/app/data/demo_repository.py -> store_patient_intake()
```

Run matching:

```text
backend/app/data/demo_repository.py -> _match_patients()
```

Simulate callback:

```text
frontend/src/App.tsx -> startFollowUpCall()
frontend/src/App.tsx -> answerFollowUpCall()
frontend/src/App.tsx -> speakAvatarQuestion()
frontend/src/App.tsx -> startVoiceCapture()
```

## Next Step

Step 8 should persist this session into Supabase tables instead of in-memory backend state.

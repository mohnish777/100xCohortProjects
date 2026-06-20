# Step 3 Review: Protocol Learning Simulation

This step makes the main POC idea visible in the app.

## What Changed

- Added `POST /api/demo/run-protocol-learning`.
- Added `ProtocolLearningRun` response models.
- Added a `Run protocol` button in the Coordinator Cockpit.
- When clicked, the frontend shows the simulated protocol-learning workflow.

## What The Button Represents

In the real product, the coordinator uploads a protocol PDF.

For this step, we simulate that PDF with this excerpt:

```text
Eligible participants must have metastatic non-small cell lung cancer.
Tumor PD-L1 expression must be documented with tumor proportion score
of at least 50 percent.
```

The backend then returns the same result the future LLM should produce:

- extracted facts:
  - `histology`
  - `metastatic`
  - `pd_l1_tps`
- extracted criteria:
  - histology = NSCLC
  - metastatic = true
  - PD-L1 TPS >= 50
- one follow-up task:
  - ask Patient L-014 for PD-L1 TPS

## Why This Matters

This is the first visible version of:

```text
Every new protocol teaches the system what facts matter.
```

The protocol does not change the patient table. It teaches the system by adding or reusing rows in
`clinical_facts`, then looking for missing answers in `patient_fact_values`.

## Code Path

1. Frontend button calls:

```text
POST /api/demo/run-protocol-learning
```

2. FastAPI route:

```text
backend/app/api/demo.py
```

3. Demo workflow function:

```text
backend/app/data/demo_repository.py -> get_protocol_learning_run()
```

4. Response shape:

```text
backend/app/domain/models.py -> ProtocolLearningRun
```

## Next Step

Step 4 should replace the simulated protocol excerpt with real text extraction from an uploaded PDF,
then use OpenAI structured extraction to return the same `ProtocolLearningRun` shape.

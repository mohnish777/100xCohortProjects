# Step 4 Review: PDF Protocol Upload

This step adds the first real protocol input.

## What Changed

- Added `POST /api/demo/upload-protocol`.
- Added a PDF text extraction helper using `pypdf`.
- Added an `Upload PDF` control in the Coordinator Cockpit.
- The uploaded PDF returns the same `ProtocolLearningRun` shape as the simulated demo.

## What Happens Now

1. Coordinator uploads a selectable-text PDF.
2. Backend extracts text from the PDF.
3. Backend creates a protocol excerpt from the extracted text.
4. Backend returns the current deterministic extraction result:
   - `histology`
   - `metastatic`
   - `pd_l1_tps`
5. Frontend shows the uploaded filename, extraction mode, excerpt, facts, and workflow steps.

## Important Limitation

This step reads real PDF text, but the medical fact extraction is still deterministic demo logic.

Scanned PDFs are not supported yet because they require OCR.

## Why We Did It This Way

This separates two hard problems:

- Step 4: Can the app upload and read protocol PDFs?
- Step 5: Can an LLM/agent convert protocol text into structured facts and criteria?

Keeping those separate makes the POC easier to debug and easier to explain.

## Remaining Roadmap

I expect the founder-ready POC to finish in about 7 steps:

1. Project scaffold and diagram.
2. Clinical memory schema and demo data.
3. Protocol-learning simulation.
4. PDF upload and text extraction.
5. LLM protocol extraction agent.
6. Intake agent that extracts patient facts from text/voice.
7. Demo polish: simpler guided UI, seeded data, and final walkthrough script.

## When Agent Capabilities Start

Step 5 is where true agent behavior begins.

In Steps 2-4, the app has agent-shaped workflow boxes, but the decisions are controlled and
deterministic. In Step 5, the Protocol Agent will actually inspect protocol text and produce
structured JSON for facts and criteria.

Step 6 adds the Intake Agent, which takes patient/caregiver history and stores patient facts.

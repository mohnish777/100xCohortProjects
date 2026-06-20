# Step 5 Review: Protocol Agent With Structured Extraction

This step adds the first real agent capability.

## What Changed

- Added `backend/app/services/protocol_agent.py`.
- PDF upload now runs the Protocol Agent after extracting PDF text.
- The Protocol Agent uses OpenAI structured extraction when `OPENAI_API_KEY` is configured.
- If no API key or model call fails, it falls back to deterministic extraction so the demo still works.
- The frontend now shows:
  - extraction mode
  - agent mode
  - filename
  - protocol excerpt
  - agent trace notes
  - extracted facts

## Why Prompt Engineering Is Needed

Yes, prompt engineering is useful here, but only in a focused way.

We are not writing a giant prompt. We are giving the agent:

- a role: Protocol Agent
- a task: extract oncology eligibility facts
- hard rules: do not invent criteria, cite source quotes
- known fact registry keys
- a strict Pydantic output schema

The schema is the real guardrail. The prompt teaches intent; the schema enforces shape.

## Multi-Agent-Deep-RAG Concepts We Reused

From `Multi-Agent-Deep-RAG`, we reused these concepts:

- role-specific prompts
- narrow specialist agents
- structured outputs
- traceable workflow steps
- bounded tool/model behavior

We did not add RAG, LangChain, or LangSmith yet because this step does not need retrieval or a large
agent graph. Direct PDF text extraction plus structured protocol extraction is enough for the MVP.

## LangSmith Plan

LangSmith is useful for tracing prompts, model calls, tools, and outputs. For this step, the UI shows
our own simplified trace notes.

Later, we can add LangSmith observability when:

- Protocol Agent
- Intake Agent
- Matching Agent
- Follow-up Agent

are all making real model/tool calls.

## Code Path

1. Frontend uploads PDF:

```text
frontend/src/App.tsx -> uploadProtocol()
```

2. Backend extracts PDF text:

```text
backend/app/services/protocol_pdf.py
```

3. Backend runs Protocol Agent:

```text
backend/app/services/protocol_agent.py
```

4. Backend maps agent output into the dashboard response:

```text
backend/app/data/demo_repository.py -> get_protocol_learning_run()
```

5. Frontend shows the result.

## Next Step

Step 6 should add the Patient Intake Agent:

- user enters free-text patient history
- agent extracts patient facts
- backend stores or previews values in `patient_fact_values`
- matching refreshes using the updated facts

# Diagram Notes: Srotas Adaptive Trial Agent

File: `docs/srotas-adaptive-trial-agent.excalidraw`

## What The Diagram Is Showing

The system is one closed loop:

1. Patient voice intake captures clinical history.
2. Specialized agents turn history and trial protocols into structured clinical facts.
3. Supabase stores durable patient memory and adaptive facts.
4. The coordinator cockpit shows trial readiness, safe SQL preview, ranked matches, and missing facts.
5. Missing facts create follow-up outreach and feed back into the same fact store.

## 100X Notes Used

- Tool calling: agents use backend tools for execution instead of pretending the LLM can directly access databases or APIs.
- Memory without RAG in the MVP: patient facts and protocol-derived facts are stored in Supabase and fetched directly by key/query.
- Direct protocol extraction: the LLM reads uploaded protocol text and returns structured criteria/fact specs; no protocol RAG layer for the first build.
- Workflows and chains: the demo follows a controlled sequence from intake to extraction to matching to follow-up.
- Multi-agent systems: each agent has a narrow job, such as intake, protocol extraction, fact registration, matching, SQL preview, and voice follow-up.

## Design Choice

The diagram deliberately avoids table-by-table implementation detail. For founders, the key idea is:

> Every new protocol teaches the system what patient facts matter, then agents close missing-data gaps.

The right-side mini-flow expands that sentence: protocol upload, direct LLM extraction, fact registration, patient missing-data scan, follow-up task creation, voice answer, and storage back into `patient_fact_values`.

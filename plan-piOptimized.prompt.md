## Plan: End-to-End Project Documentation

Create a business-style, mixed-audience, detailed technical document that explains what this project does end-to-end (UI to MCP to Snowflake), how it is built, how it is operated, and what has already been delivered. The recommended approach is to produce one comprehensive document in a new docs directory, plus a short pointer section in README for discoverability.

**Steps**
1. Finalize document outline and acceptance criteria based on confirmed preferences (mixed audience, detailed depth, business style, new doc location).
2. Build a "Project Story" section: problem solved, scope, delivered capabilities, and user journey from skill selection to query execution.
3. Build "Architecture" sections in order of dependency:
   1) System context and component map (Frontend, MCP backend, Snowflake).
   2) Frontend architecture and state model.
   3) Backend tool architecture and execution flow. *depends on 3.1*
4. Build "Technology Deep Dive" sections in parallel once architecture baseline is written:
   - Frontend stack and major libraries (React/Vite/Zustand/Recharts/Motion).
   - Backend stack and runtime model (FastAPI, Snowflake connector, sqlglot).
   - Security and governance model (validation, SQL safety modes, row limits, CORS, env validation).
5. Add "Operational Guide" content:
   - Local run commands and environment configuration.
   - Health checks and core MCP endpoints.
   - Troubleshooting and known constraints (Python version constraints, StrictMode duplicate effects, connection/logging caveats).
6. Add "Delivery Summary" and "What’s Next":
   - What has been implemented and verified.
   - Known gaps/risks and prioritized roadmap.
7. Create concise README pointer update referencing the new end-to-end document for discoverability. *parallel with step 6 once main doc is drafted*
8. Perform document QA pass:
   - Consistency of terminology.
   - Accuracy of endpoint/tool names against source files.
   - Business readability for non-engineering audience.

**Relevant files**
- `c:/Users/Dipak.Mandlik/Desktop/π-optimized/README.md` — add a short "Detailed Documentation" pointer section.
- `c:/Users/Dipak.Mandlik/Desktop/π-optimized/src/App.tsx` — confirm panel composition and app shell narrative.
- `c:/Users/Dipak.Mandlik/Desktop/π-optimized/src/components/CenterPanel.tsx` — document generation/orchestration behavior and intent handling.
- `c:/Users/Dipak.Mandlik/Desktop/π-optimized/src/components/RightPanel.tsx` — document explorer hydration, query execution, and result rendering.
- `c:/Users/Dipak.Mandlik/Desktop/π-optimized/src/components/LeftPanel.tsx` — document skills selection and context-setting flow.
- `c:/Users/Dipak.Mandlik/Desktop/π-optimized/src/store.ts` — state model and key app-level entities.
- `c:/Users/Dipak.Mandlik/Desktop/π-optimized/src/api/mcpClient.ts` — frontend-to-backend contract and timeout behavior.
- `c:/Users/Dipak.Mandlik/Desktop/π-optimized/server/main.py` — FastAPI endpoints and request lifecycle.
- `c:/Users/Dipak.Mandlik/Desktop/π-optimized/server/tool_registry.py` — tool catalog, dispatch pattern, and handlers.
- `c:/Users/Dipak.Mandlik/Desktop/π-optimized/server/security.py` — safety enforcement and validation model.
- `c:/Users/Dipak.Mandlik/Desktop/π-optimized/server/config.py` — configuration model and required environment strategy.
- `c:/Users/Dipak.Mandlik/Desktop/π-optimized/server/snowflake_client.py` — connection management, retries, and list caching behavior.
- `c:/Users/Dipak.Mandlik/Desktop/π-optimized/src/skills/data-architect.skill.md` — role-specific capability documentation.
- `c:/Users/Dipak.Mandlik/Desktop/π-optimized/src/skills/sql-generation.skill.md` — SQL generation standards and guardrails.
- `c:/Users/Dipak.Mandlik/Desktop/π-optimized/src/skills/snowflake-stored-procedures.skill.md` — stored procedure authoring guidance.
- `c:/Users/Dipak.Mandlik/Desktop/π-optimized/src/skills/analytics-engineer.skill.md` — analytics engineering workflow guidance.
- `c:/Users/Dipak.Mandlik/Desktop/π-optimized/src/skills/snowflake-query-optimizer.skill.md` — optimization guidance and heuristics.

**Verification**
1. Validate all endpoint and tool names in the document against backend definitions in `server/main.py` and `server/tool_registry.py`.
2. Validate described environment variables against `server/config.py`, `.env.example`, and frontend MCP config usage.
3. Validate user workflow narrative by tracing from `LeftPanel` and `CenterPanel` to `RightPanel` execution path.
4. Run readability pass for business style: short section intros, outcome-focused summaries, minimized code-level jargon.
5. Confirm README pointer accuracy and navigability to the new detailed document.

**Decisions**
- Include: end-to-end flow, architecture, technology stack, security, operations, troubleshooting, delivered scope, and next steps.
- Exclude: implementation/code changes unrelated to documentation and any new runtime features.
- Output format: one detailed standalone project document in a new docs directory, plus concise README pointer.

**Further Considerations**
1. Diagram format recommendation: Option A (ASCII architecture diagram in markdown) vs Option B (embedded PNG/PDF architecture image). Recommendation: Option A for maintainability in git.
2. Delivery format recommendation: Option A (single long document) vs Option B (single document + appendix sections). Recommendation: Option B for mixed audience readability.
3. Governance detail depth recommendation: Option A (brief policy summary) vs Option B (explicit control matrix). Recommendation: Option A now, Option B in future compliance-oriented revision.
# π-Optimized End-to-End Project Document

## 1. Executive Summary

π-Optimized is an AI-assisted Snowflake analytics workspace composed of:
- A React + Vite frontend for skill-based SQL workflows
- A Python FastAPI MCP bridge that exposes Snowflake operations as controlled tools
- A Snowflake execution layer with validation, safety modes, and operational constraints

This project enables users to move from business intent to executable SQL faster, while preserving control through:
- Input and identifier validation
- SQL safety mode controls (dev and prod)
- Enforced row limits and timeout boundaries
- Explicit tool contracts over HTTP

## 2. What Has Been Delivered

### 2.1 Product Capabilities

Delivered capabilities in the current implementation:
- Skill-driven workflow in the left panel (Data Architect, Analytics Engineer, SQL Writer, Stored Procedure Writer, Query Optimizer, and others)
- Chat-based prompt handling with guided feedback and SQL draft generation
- SQL editor and execution panel with result table/chart visualization
- Snowflake explorer (databases, schemas, tables) loaded via MCP tools
- Query execution metadata display (runtime, row count, executed query)
- Health monitoring of MCP bridge from frontend

### 2.2 Backend MCP Tooling

Implemented MCP tools:
1. run_query
2. list_databases
3. list_schemas
4. list_tables
5. describe_table
6. list_warehouses
7. warehouse_usage

Each tool has a structured schema (input and output) and server-side validation.

### 2.3 Operational Delivery

Delivered runtime model:
- Local full-stack run with one command (frontend + backend)
- CORS support for local frontend origins
- Snowflake connector warmup on startup
- Metadata list caching in backend for repeated list operations
- Retry-on-failure behavior for Snowflake connection failures

## 3. Business Problem and Value

### 3.1 Problem Solved

Typical analytics teams lose time in:
- Translating business questions into valid Snowflake SQL
- Discovering relevant schemas and tables quickly
- Maintaining consistency in SQL safety and query boundaries
- Iterating on query quality, readability, and performance

### 3.2 Value Delivered

This project reduces those gaps by:
- Combining guided intent capture with SQL generation assistance
- Providing fast metadata exploration through tool APIs
- Enforcing guardrails before query execution
- Keeping execution centralized through one MCP bridge

## 4. End-to-End User Journey

1. User selects one or more skills from the left panel.
2. User enters a request in the center panel.
3. Frontend interprets intent:
   - SQL passthrough
   - SQL generation
   - Stored procedure workflow
   - Query optimization workflow
4. SQL draft is prepared and shown in the right panel.
5. User runs query from SQL editor.
6. Frontend calls MCP tool run_query.
7. Backend validates input and SQL safety rules.
8. Backend executes against Snowflake and returns structured result.
9. Frontend renders results (table or chart) and execution metadata.
10. User refines prompt or SQL and repeats.

## 5. System Architecture

### 5.1 Logical Architecture

```text
[React Frontend]
  - LeftPanel (skills and context)
  - CenterPanel (prompt orchestration)
  - RightPanel (SQL editor, explorer, execution, results)
          |
          | HTTP (GET/POST)
          v
[FastAPI MCP Bridge]
  - /health
  - /mcp/tools
  - /mcp/call
  - /mcp/events
  - ToolRegistry + Security + SnowflakeClient
          |
          | Snowflake Connector
          v
[Snowflake]
  - Query execution
  - Metadata discovery (SHOW/DESC)
  - Warehouse usage analytics
```

### 5.2 Core Component Responsibilities

Frontend:
- App shell composes the three-panel layout and monitoring modal.
- Global state is managed in Zustand.
- MCPClient encapsulates request timeout and error handling.

Backend:
- FastAPI exposes health, tool listing, and tool invocation endpoints.
- ToolRegistry dispatches tool handlers.
- Security layer validates identifiers and SQL statement safety.
- SnowflakeClient manages connection, retries, and list-cache behavior.

## 6. Technology Deep Dive

### 6.1 Frontend Stack

Primary technologies:
- React 19
- Vite 6
- TypeScript
- Zustand (state)
- Recharts (visualization)
- Motion (UI animation)
- Lucide React (icons)
- Tailwind CSS (styling)

Frontend architectural notes:
- Panelized layout for clear separation of responsibilities.
- Global state includes selected skills, selected tables, generated SQL, query results, execution metadata, MCP status, and composer draft.
- Right panel hydrates data explorer using concurrency-limited metadata calls and local cache fallback.
- Center panel runs health checks on interval and orchestrates guided workflows.

### 6.2 Backend Stack

Primary technologies:
- Python 3.10+ (3.12 prioritized in scripts)
- FastAPI
- Uvicorn
- snowflake-connector-python
- sqlglot (statement parsing/classification)
- python-dotenv

Backend architectural notes:
- Immutable settings model loaded from environment with defaults.
- CORS middleware configured via MCP_CORS_ORIGINS.
- Background warmup query on startup.
- All tool invocation goes through one registry dispatch path.

### 6.3 Contract-Driven Integration

Frontend and backend integrate through explicit endpoints:
- GET /health
- GET /mcp/tools
- POST /mcp/call
- GET /mcp/events

Tool invocation payload shape:
- name
- arguments

Tool response shape:
- ok
- name
- result

Error handling behavior:
- Validation errors return HTTP 400
- Unexpected runtime errors return HTTP 500
- Sanitized error payload is returned to avoid leaking internals

## 7. Security, Safety, and Governance

### 7.1 Input Validation

Validation controls include:
- Identifier validation (database/schema/table/warehouse) with strict regex
- Day-range validation for warehouse usage requests
- max_rows clamping to configured hard cap

### 7.2 SQL Safety Controls

SQL statement classification uses sqlglot.

Allowed statements by mode:
- prod mode: SELECT, SHOW, DESCRIBE
- dev mode: SELECT, SHOW, DESCRIBE, WITH, CREATE, CREATE_PROCEDURE, CALL

Query limiter behavior:
- SELECT and WITH queries without LIMIT receive an automatic LIMIT using configured default.

### 7.3 Operational Security Controls

- Required Snowflake credentials are validated via health model.
- Third-party logging level for Snowflake connector is configurable.
- Cloud metadata probe suppression is supported for cleaner local runtime behavior.
- CORS origin allow-list is configurable and should be restricted in production.

## 8. Performance and Reliability

### 8.1 Backend Reliability

- Lazy, reusable Snowflake connection management
- Thread locks around connection/query/cache state
- Query retry pattern with connection reset on failure
- Metadata list caching (TTL: 300 seconds)

### 8.2 Frontend Performance

- Explorer hydration with controlled concurrency for schemas and tables
- Local storage cache for explorer data
- Timeout-aware MCP requests with abort handling
- Long-running query timeout override support in execution calls

### 8.3 Known Runtime Considerations

- Python 3.12 is prioritized in scripts to avoid connector compatibility issues in newer runtimes.
- StrictMode in development can trigger effect duplication and additional health/explorer calls.

## 9. DevOps and Operations Guide

### 9.1 Prerequisites

- Node.js 20+
- Python 3.10+
- pip

### 9.2 Setup

1. Install frontend packages:
   - npm install
2. Create environment file:
   - copy .env.example .env.local
3. Add required secrets for frontend and Snowflake.
4. Install backend dependencies:
   - npm run mcp:install

### 9.3 Run Options

Option A (recommended):
- npm run dev:full

Option B (separate processes):
- Terminal 1: npm run dev
- Terminal 2: npm run mcp:dev

Expected local endpoints:
- Frontend: http://127.0.0.1:3000
- Backend health: http://127.0.0.1:5000/health

### 9.4 Key Environment Variables

Frontend:
- GEMINI_API_KEY
- VITE_MCP_BASE_URL
- VITE_MCP_REQUEST_TIMEOUT_MS
- VITE_EXPLORER_DATABASE (optional)

Backend:
- SNOWFLAKE_ACCOUNT
- SNOWFLAKE_USER
- SNOWFLAKE_PASSWORD
- SNOWFLAKE_ROLE
- SNOWFLAKE_WAREHOUSE
- SNOWFLAKE_DATABASE
- SNOWFLAKE_SCHEMA
- MCP_HOST
- MCP_PORT
- MCP_LOG_LEVEL
- MCP_CORS_ORIGINS
- SQL_SAFETY_MODE
- SQL_DEFAULT_ROW_LIMIT
- SQL_MAX_ROWS
- SQL_TIMEOUT_SECONDS
- SNOWFLAKE_LOG_LEVEL
- SUPPRESS_CLOUD_METADATA_PROBES

## 10. API and Tool Catalog

### 10.1 Health Endpoint

GET /health returns:
- status
- missing_env
- sql_safety_mode
- snowflake_connector_ready
- snowflake_connector_message

### 10.2 Tool Discovery

GET /mcp/tools returns tool metadata:
- name
- description
- inputSchema
- outputSchema

### 10.3 Tool Execution

POST /mcp/call executes tool handlers through registry dispatch.

Example operation types:
- Metadata operations (list_databases, list_schemas, list_tables)
- Table metadata details (describe_table)
- Query execution (run_query)
- Warehouse utilization summary (warehouse_usage)

## 11. Current Limitations and Risks

1. SQL generation logic in frontend is largely heuristic and pattern-driven.
2. Skill template behavior is mostly hardcoded in frontend runtime.
3. Explorer hydration can be heavy in very large Snowflake estates.
4. Error remediation UX can be expanded for clearer next-step suggestions.
5. No full compliance-grade audit trail is currently described in backend APIs.

## 12. Roadmap Recommendations

Priority 1:
- Add standardized audit/event logging for tool calls.
- Add lazy-loading/pagination strategy in explorer for large accounts.
- Expand retries and user-facing remediation hints for timeout classes.

Priority 2:
- Move skill and guided-flow definitions to external config for easier governance.
- Add richer chart configurability and semantic result rendering controls.
- Introduce integration tests for endpoint contracts and tool responses.

Priority 3:
- Add role-aware UI capabilities and access-level governance.
- Add deployment profile documentation for cloud environments.

## 13. Success Metrics (Suggested)

1. Time to first correct SQL draft
2. Query success rate on first execution
3. Average result turnaround time
4. Explorer load completion time
5. Credit efficiency improvements after optimizer use

## 14. Document Ownership and Update Policy

Recommended owners:
- Product owner for scope and value narrative
- Platform/backend owner for MCP and Snowflake controls
- Frontend owner for UI and workflow sections

Recommended cadence:
- Update this document at the end of each major release or architecture change.

---

This document represents the current implemented architecture and delivery state of the π-Optimized project as of March 23, 2026.

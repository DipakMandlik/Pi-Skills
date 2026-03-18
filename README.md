<div align="center">
<img width="1200" height="475" alt="GHBanner" src="https://github.com/user-attachments/assets/0aa67016-6eaf-458a-adb2-6e31a0763ed6" />
</div>

# π-Optimized: Frontend + Snowflake MCP Bridge

This repository now includes:

- A React/Vite frontend for AI-assisted SQL workflows.
- A Python MCP bridge service that exposes Snowflake tools over HTTP.

View your app in AI Studio: https://ai.studio/apps/978c3c8d-5b8b-4493-816e-34e52b5d2d88

## Prerequisites

- Node.js 20+
- Python 3.10+
- pip

## Local Setup

1. Install frontend dependencies:
   npm install

2. Create your local env file:
   copy .env.example .env.local

3. Fill secrets in .env.local:
   - GEMINI_API_KEY
   - SNOWFLAKE_ACCOUNT
   - SNOWFLAKE_USER
   - SNOWFLAKE_PASSWORD
   - SNOWFLAKE_ROLE
   - SNOWFLAKE_WAREHOUSE
   - SNOWFLAKE_DATABASE
   - SNOWFLAKE_SCHEMA
   - VITE_MCP_BASE_URL (default: http://localhost:5000)

4. Install MCP backend dependencies:
   npm run mcp:install

## Run Locally

### Option A: Run both services together

npm run dev:full

- Frontend: http://localhost:3000
- MCP server: http://localhost:5000

### Option B: Run separately

Terminal 1:

npm run dev

Terminal 2:

npm run mcp:dev

## MCP Server Endpoints

- Health: GET /health
- Tool discovery: GET /mcp/tools
- Tool invocation: POST /mcp/call
- SSE status stream: GET /mcp/events

## Implemented Snowflake Tools

- run_query
- list_databases
- list_schemas
- list_tables
- describe_table
- list_warehouses
- warehouse_usage

All tools are schema-described by the MCP bridge and enforce input validation.

## Security Notes

- Use a least-privilege Snowflake role (recommended: MCP_AI_ROLE).
- Keep SQL_SAFETY_MODE=prod in production to enforce strict read-only statements.
- Set MCP_CORS_ORIGINS to only trusted frontend origins.
- Do not commit .env.local.

## Example Tool Call

POST /mcp/call

{
  "name": "list_tables",
  "arguments": {
    "database": "ANALYTICS_PROD",
    "schema": "PUBLIC"
  }
}


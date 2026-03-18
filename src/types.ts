export interface Skill {
  id: string;
  name: string;
  description: string;
  iconName: string;
  isCustom?: boolean;
}

export type ChatModel =
  | 'gemini-2.0-flash'
  | 'gemini-1.5-flash'
  | 'gemini-1.5-pro'
  | 'gpt-4o-mini'
  | 'gpt-4.1'
  | 'gpt-4.1-mini'
  | 'o3-mini';

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  sql?: string;
  thinking?: string;
}

export interface ExecutionMetadata {
  timeMs: number;
  rows: number;
  warehouse: string;
  executedQuery?: string;
}

export interface MCPToolDefinition {
  name: string;
  description: string;
  inputSchema: Record<string, unknown>;
  outputSchema: Record<string, unknown>;
}

export interface MCPToolCallResponse<T = unknown> {
  ok: boolean;
  name: string;
  result: T;
}

export interface QueryResultPayload {
  query_id: string;
  executed_query?: string;
  columns: string[];
  rows: Array<Array<string | number | boolean | null>>;
  row_count: number;
}

export interface ListDatabasesPayload {
  databases: string[];
  query_id: string;
}

export interface ListSchemasPayload {
  schemas: string[];
  query_id: string;
}

export interface ListTablesPayload {
  tables: string[];
  query_id: string;
}

export interface ExplorerSchema {
  name: string;
  tables: string[];
}

export interface ExplorerDatabase {
  name: string;
  schemas: ExplorerSchema[];
}

export interface MCPHealthResponse {
  status: 'ok' | 'degraded';
  missing_env: string[];
  sql_safety_mode: string;
}

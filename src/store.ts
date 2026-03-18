import { create } from 'zustand';
import { Message, ExecutionMetadata, Skill, ChatModel } from './types';

const DEFAULT_SKILLS: Skill[] = [
  { id: 'data-architect', name: 'Data Architect', description: 'Design scalable data models and warehouse architecture.', iconName: 'Network' },
  { id: 'analytics-engineer', name: 'Analytics Engineer', description: 'Transform data and manage dbt models.', iconName: 'Workflow' },
  { id: 'ml-engineer', name: 'ML Engineer', description: 'Build and deploy predictive models.', iconName: 'Brain' },
  { id: 'sql-writer', name: 'SQL Writer', description: 'Generate optimized SQL queries.', iconName: 'Code2' },
  { id: 'stored-procedure-writer', name: 'Stored Procedure Writer', description: 'Create, debug, and enhance Snowflake stored procedures.', iconName: 'FileCode2' },
  { id: 'query-optimizer', name: 'Query Optimizer', description: 'Improve performance & rewrite SQL.', iconName: 'Zap' },
  { id: 'data-explorer', name: 'Data Explorer', description: 'Discover schemas, tables, and columns.', iconName: 'Search' },
  { id: 'warehouse-monitor', name: 'Warehouse Monitor', description: 'Analyze usage and query costs.', iconName: 'Activity' },
  { id: 'metadata-inspector', name: 'Metadata Inspector', description: 'Explore metadata and structure.', iconName: 'Database' },
];

interface AppState {
  skills: Skill[];
  addSkill: (skill: Skill) => void;
  updateSkill: (id: string, skill: Partial<Skill>) => void;
  deleteSkill: (id: string) => void;
  activeSkills: string[];
  setActiveSkills: (skills: string[]) => void;
  toggleSkill: (skill: string) => void;
  selectedTables: string[];
  toggleTable: (table: string) => void;
  selectedSchema: string;
  setSelectedSchema: (schema: string) => void;
  chatHistory: Message[];
  addMessage: (message: Message) => void;
  updateMessage: (id: string, patch: Partial<Message>) => void;
  generatedSQL: string | null;
  setGeneratedSQL: (sql: string | null) => void;
  queryResults: any[] | null;
  setQueryResults: (results: any[] | null) => void;
  executionMetadata: ExecutionMetadata | null;
  setExecutionMetadata: (metadata: ExecutionMetadata | null) => void;
  isExecuting: boolean;
  setIsExecuting: (isExecuting: boolean) => void;
  isMonitorOpen: boolean;
  setIsMonitorOpen: (isOpen: boolean) => void;
  mcpServerStatus: 'unknown' | 'ok' | 'degraded' | 'error';
  setMcpServerStatus: (status: 'unknown' | 'ok' | 'degraded' | 'error') => void;
  mcpError: string | null;
  setMcpError: (message: string | null) => void;
  selectedModel: ChatModel;
  setSelectedModel: (model: ChatModel) => void;
  thinkingEnabled: boolean;
  setThinkingEnabled: (enabled: boolean) => void;
  composerDraft: string | null;
  setComposerDraft: (draft: string | null) => void;
}

export const useStore = create<AppState>((set) => ({
  skills: DEFAULT_SKILLS,
  addSkill: (skill) => set((state) => ({ skills: [...state.skills, skill] })),
  updateSkill: (id, updatedSkill) => set((state) => ({
    skills: state.skills.map(s => s.id === id ? { ...s, ...updatedSkill } : s)
  })),
  deleteSkill: (id) => set((state) => ({
    skills: state.skills.filter(s => s.id !== id),
    activeSkills: state.activeSkills.filter(s => s !== id)
  })),
  activeSkills: [],
  setActiveSkills: (skills) => set({ activeSkills: skills }),
  toggleSkill: (skill) => set((state) => {
    if (state.activeSkills.includes(skill)) {
      return { activeSkills: state.activeSkills.filter(s => s !== skill) };
    }
    if (state.activeSkills.length >= 3) {
      return { activeSkills: [...state.activeSkills.slice(1), skill] };
    }
    return { activeSkills: [...state.activeSkills, skill] };
  }),
  selectedTables: [],
  toggleTable: (table) => set((state) => {
    if (state.selectedTables.includes(table)) {
      return { selectedTables: state.selectedTables.filter(t => t !== table) };
    }
    return { selectedTables: [...state.selectedTables, table] };
  }),
  selectedSchema: 'AUTO',
  setSelectedSchema: (schema) => set({ selectedSchema: schema }),
  chatHistory: [
    {
      id: '1',
      role: 'assistant',
      content: 'Welcome to π-Optimized. Select a skill from the left panel or ask me anything about your data.',
    }
  ],
  addMessage: (message) => set((state) => ({ chatHistory: [...state.chatHistory, message] })),
  updateMessage: (id, patch) => set((state) => ({
    chatHistory: state.chatHistory.map((message) => (
      message.id === id ? { ...message, ...patch } : message
    )),
  })),
  generatedSQL: null,
  setGeneratedSQL: (sql) => set({ generatedSQL: sql }),
  queryResults: null,
  setQueryResults: (results) => set({ queryResults: results }),
  executionMetadata: null,
  setExecutionMetadata: (metadata) => set({ executionMetadata: metadata }),
  isExecuting: false,
  setIsExecuting: (isExecuting) => set({ isExecuting }),
  isMonitorOpen: false,
  setIsMonitorOpen: (isOpen) => set({ isMonitorOpen: isOpen }),
  mcpServerStatus: 'unknown',
  setMcpServerStatus: (status) => set({ mcpServerStatus: status }),
  mcpError: null,
  setMcpError: (message) => set({ mcpError: message }),
  selectedModel: 'gemini-2.0-flash',
  setSelectedModel: (model) => set({ selectedModel: model }),
  thinkingEnabled: true,
  setThinkingEnabled: (enabled) => set({ thinkingEnabled: enabled }),
  composerDraft: null,
  setComposerDraft: (draft) => set({ composerDraft: draft }),
}));

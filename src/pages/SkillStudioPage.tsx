import { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion } from 'motion/react';
import {
  ArrowLeft, Save, Eye, Code, Sparkles, Send, Play,
  FileText, Settings, Paperclip, History, Download,
  Upload, X, Plus, ChevronDown, Check, AlertCircle,
  Loader2, MessageSquare, Bot, Zap,
} from 'lucide-react';
import { Button, Badge, Card, Tabs, Textarea, Input, useToast, Modal, Dropdown, DropdownItem, DropdownSeparator } from '../components/ui';
import { ROUTES } from '../constants/routes';

interface SkillFrontmatter {
  name: string;
  description: string;
  category: string;
  version: string;
  compatibility: string[];
}

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

interface Attachment {
  id: string;
  name: string;
  type: string;
  size: string;
}

const MOCK_SKILL_DATA = {
  frontmatter: {
    name: 'SQL Optimizer',
    description: 'Analyze and optimize complex SQL queries for Snowflake',
    category: 'SQL',
    version: '2.3.0',
    compatibility: ['Snowflake', 'BigQuery', 'Redshift'],
  },
  content: `## Overview

The SQL Optimizer skill analyzes your Snowflake queries and provides actionable recommendations for improving performance.

### Features

- **Query Analysis**: Deep inspection of execution plans
- **Bottleneck Detection**: Identifies slow joins, missing indexes
- **Auto-Rewrite**: Suggests optimized query alternatives
- **Cost Estimation**: Predicts warehouse compute costs

### Usage

\`\`\`sql
-- Before: Inefficient query
SELECT * FROM orders o
JOIN customers c ON o.customer_id = c.id
WHERE o.created_at > '2025-01-01';

-- After: Optimized query
SELECT o.order_id, o.total, c.name
FROM orders o
INNER JOIN customers c ON o.customer_id = c.id
WHERE o.created_at >= '2025-01-01'
  AND o.status = 'completed';
\`\`\`

### Best Practices

1. Always use explicit column selection
2. Leverage clustering keys for large tables
3. Use EXPLAIN to review execution plans
4. Monitor warehouse sizing for query patterns`,
  attachments: [
    { id: '1', name: 'optimization_rules.json', type: 'json', size: '2.4 KB' },
    { id: '2', name: 'query_patterns.md', type: 'md', size: '1.8 KB' },
  ],
};

export function SkillStudioPage() {
  const { skillId } = useParams<{ skillId: string }>();
  const navigate = useNavigate();
  const { toast } = useToast();
  const isNew = !skillId || skillId === 'new';

  const [frontmatter, setFrontmatter] = useState<SkillFrontmatter>(MOCK_SKILL_DATA.frontmatter);
  const [content, setContent] = useState(MOCK_SKILL_DATA.content);
  const [attachments, setAttachments] = useState<Attachment[]>(MOCK_SKILL_DATA.attachments);
  const [activeTab, setActiveTab] = useState('editor');
  const [aiPanelOpen, setAiPanelOpen] = useState(false);
  const [aiInput, setAiInput] = useState('');
  const [aiMessages, setAiMessages] = useState<ChatMessage[]>([]);
  const [aiLoading, setAiLoading] = useState(false);
  const [saveStatus, setSaveStatus] = useState<'saved' | 'saving' | 'unsaved' | 'error'>('saved');
  const [publishModalOpen, setPublishModalOpen] = useState(false);
  const [publishStatus, setPublishStatus] = useState<'draft' | 'published' | 'archived'>('draft');
  const editorRef = useRef<HTMLTextAreaElement>(null);
  const saveTimerRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  // Auto-save
  useEffect(() => {
    if (saveStatus === 'saved') return;
    if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
    setSaveStatus('unsaved');
    saveTimerRef.current = setTimeout(() => {
      setSaveStatus('saving');
      setTimeout(() => {
        setSaveStatus('saved');
        toast('success', 'Auto-saved');
      }, 500);
    }, 2000);
    return () => { if (saveTimerRef.current) clearTimeout(saveTimerRef.current); };
  }, [content, frontmatter]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 's') {
        e.preventDefault();
        handleSave();
      }
      if ((e.metaKey || e.ctrlKey) && e.key === 'n') {
        e.preventDefault();
        navigate(ROUTES.SKILL_STUDIO_NEW);
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [content, frontmatter]);

  const handleSave = useCallback(() => {
    setSaveStatus('saving');
    setTimeout(() => {
      setSaveStatus('saved');
      toast('success', 'Skill saved successfully');
    }, 600);
  }, [toast]);

  const handlePublish = useCallback((status: 'draft' | 'published' | 'archived') => {
    setPublishStatus(status);
    setPublishModalOpen(false);
    toast('success', `Skill ${status === 'published' ? 'published' : status === 'draft' ? 'saved as draft' : 'archived'}`);
  }, [toast]);

  const handleAiSend = useCallback(() => {
    if (!aiInput.trim()) return;
    const userMsg: ChatMessage = { role: 'user', content: aiInput.trim(), timestamp: new Date() };
    setAiMessages((prev) => [...prev, userMsg]);
    const prompt = aiInput.trim();
    setAiInput('');
    setAiLoading(true);

    setTimeout(() => {
      let response = '';
      if (prompt.toLowerCase().includes('description')) {
        response = `Here's a suggested description:\n\n"Advanced SQL optimization engine that analyzes query execution plans, identifies performance bottlenecks, and provides actionable recommendations for Snowflake environments. Supports automatic query rewriting and cost estimation."`;
      } else if (prompt.toLowerCase().includes('test')) {
        response = `Here are some test cases for this skill:\n\n1. **Complex JOIN optimization** — Test with 5+ table joins\n2. **Subquery flattening** — Test correlated subqueries\n3. **Window function optimization** — Test ROW_NUMBER, RANK, etc.\n4. **CTE materialization** — Test WITH clause performance\n5. **Partition pruning** — Test date-range queries`;
      } else {
        response = `I can help you improve this skill. Try asking me to:\n\n- **Write a description** — "Help me write the description"\n- **Suggest test cases** — "Suggest test cases for this skill"\n- **Improve content** — "Make this more detailed"\n- **Add examples** — "Add SQL examples"\n\nWhat would you like to work on?`;
      }
      setAiMessages((prev) => [...prev, { role: 'assistant', content: response, timestamp: new Date() }]);
      setAiLoading(false);
    }, 1000);
  }, [aiInput]);

  const handleInsertAiSuggestion = useCallback((text: string) => {
    setContent((prev) => prev + '\n\n' + text);
    toast('success', 'Inserted into editor');
  }, [toast]);

  const handleRemoveAttachment = (id: string) => {
    setAttachments((prev) => prev.filter((a) => a.id !== id));
    toast('success', 'Attachment removed');
  };

  const statusBadge = saveStatus === 'saved'
    ? <Badge variant="success" size="sm" dot>Saved</Badge>
    : saveStatus === 'saving'
    ? <Badge variant="info" size="sm"><Loader2 className="w-3 h-3 animate-spin mr-1" />Saving</Badge>
    : saveStatus === 'unsaved'
    ? <Badge variant="warning" size="sm" dot>Unsaved</Badge>
    : <Badge variant="error" size="sm" dot>Error</Badge>;

  return (
    <div className="h-[calc(100vh-7rem)] flex flex-col animate-fade-in-up">
      {/* Studio Header */}
      <div className="flex items-center justify-between mb-4 shrink-0">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate(ROUTES.SKILLS)}
            className="p-2 rounded-lg text-muted hover:text-foreground hover:bg-surface transition-colors"
            aria-label="Back to skills"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-bold text-foreground">
                {isNew ? 'Create Skill' : frontmatter.name}
              </h1>
              {statusBadge}
            </div>
            <p className="text-xs text-muted mt-0.5">
              {isNew ? 'Building a new AI skill' : `Editing v${frontmatter.version}`}
              <span className="mx-1">·</span>
              <kbd className="px-1 py-0.5 bg-surface rounded text-[10px] border border-border">⌘S</kbd> to save
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="secondary"
            size="sm"
            icon={aiPanelOpen ? <X className="w-4 h-4" /> : <Sparkles className="w-4 h-4" />}
            onClick={() => setAiPanelOpen(!aiPanelOpen)}
          >
            AI Assistant
          </Button>
          <Dropdown
            trigger={
              <Button size="sm" iconRight={<ChevronDown className="w-3.5 h-3.5" />}>
                Publish
              </Button>
            }
            align="end"
          >
            <DropdownItem icon={<FileText className="w-4 h-4" />} onClick={() => handlePublish('draft')}>
              Save as Draft
            </DropdownItem>
            <DropdownItem icon={<Check className="w-4 h-4" />} onClick={() => handlePublish('published')}>
              Publish
            </DropdownItem>
            <DropdownSeparator />
            <DropdownItem icon={<AlertCircle className="w-4 h-4" />} destructive onClick={() => handlePublish('archived')}>
              Archive
            </DropdownItem>
          </Dropdown>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex gap-4 min-h-0">
        {/* Editor Pane */}
        <div className="flex-1 flex flex-col min-w-0">
          <Card padding="none" className="flex-1 flex flex-col overflow-hidden">
            {/* Frontmatter */}
            <div className="border-b border-border p-4 shrink-0">
              <div className="flex items-center gap-2 mb-3">
                <Settings className="w-4 h-4 text-muted" />
                <span className="text-xs font-semibold text-foreground uppercase tracking-wider">Properties</span>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <Input
                  label="Name"
                  value={frontmatter.name}
                  onChange={(e) => setFrontmatter((prev) => ({ ...prev, name: e.target.value }))}
                  placeholder="Skill name"
                />
                <Input
                  label="Category"
                  value={frontmatter.category}
                  onChange={(e) => setFrontmatter((prev) => ({ ...prev, category: e.target.value }))}
                  placeholder="e.g., SQL, ML, Analytics"
                />
                <Input
                  label="Version"
                  value={frontmatter.version}
                  onChange={(e) => setFrontmatter((prev) => ({ ...prev, version: e.target.value }))}
                  placeholder="1.0.0"
                />
                <Input
                  label="Description"
                  value={frontmatter.description}
                  onChange={(e) => setFrontmatter((prev) => ({ ...prev, description: e.target.value }))}
                  placeholder="Brief description"
                />
              </div>
            </div>

            {/* Tabs */}
            <div className="flex items-center justify-between border-b border-border px-4 shrink-0">
              <Tabs
                tabs={[
                  { key: 'editor', label: 'Editor', icon: <Code className="w-3.5 h-3.5" /> },
                  { key: 'preview', label: 'Preview', icon: <Eye className="w-3.5 h-3.5" /> },
                  { key: 'attachments', label: 'Files', icon: <Paperclip className="w-3.5 h-3.5" />, badge: attachments.length },
                ]}
                activeKey={activeTab}
                onChange={setActiveTab}
                size="sm"
              />
              <div className="flex items-center gap-1">
                <Button size="xs" variant="ghost" icon={<Download className="w-3.5 h-3.5" />}>Export</Button>
                <Button size="xs" variant="ghost" icon={<Upload className="w-3.5 h-3.5" />}>Import</Button>
              </div>
            </div>

            {/* Editor Content */}
            <div className="flex-1 overflow-hidden">
              {activeTab === 'editor' && (
                <textarea
                  ref={editorRef}
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                  className="w-full h-full p-4 text-sm font-mono text-foreground bg-background resize-none outline-none"
                  spellCheck={false}
                  aria-label="Skill content editor"
                />
              )}

              {activeTab === 'preview' && (
                <div className="h-full overflow-y-auto p-6 prose prose-sm max-w-none">
                  {content.split('\n').map((line, i) => {
                    if (line.startsWith('## ')) return <h2 key={i} className="text-lg font-bold text-foreground mt-4 mb-2">{line.replace('## ', '')}</h2>;
                    if (line.startsWith('### ')) return <h3 key={i} className="text-base font-semibold text-foreground mt-3 mb-1.5">{line.replace('### ', '')}</h3>;
                    if (line.startsWith('- **')) {
                      const match = line.match(/- \*\*(.+?)\*\*: (.+)/);
                      if (match) return <li key={i} className="text-sm text-muted"><strong className="text-foreground">{match[1]}</strong>: {match[2]}</li>;
                    }
                    if (line.startsWith('- ')) return <li key={i} className="text-sm text-muted">{line.replace('- ', '')}</li>;
                    if (/^\d+\./.test(line)) {
                      const match = line.match(/^\d+\.\s+(.+)/);
                      if (match) return <li key={i} className="text-sm text-muted ml-4">{match[1]}</li>;
                    }
                    if (line.startsWith('```')) return null;
                    if (line.trim() === '') return <br key={i} />;
                    if (line.startsWith('SELECT') || line.startsWith('--') || line.includes('FROM ') || line.includes('JOIN ')) {
                      return <code key={i} className="block bg-surface px-3 py-1.5 rounded text-xs font-mono text-foreground my-1">{line}</code>;
                    }
                    return <p key={i} className="text-sm text-muted leading-relaxed">{line}</p>;
                  })}
                </div>
              )}

              {activeTab === 'attachments' && (
                <div className="p-4">
                  {attachments.length === 0 ? (
                    <div className="text-center py-8">
                      <Paperclip className="w-8 h-8 text-muted mx-auto mb-2" />
                      <p className="text-sm text-muted">No attachments yet</p>
                      <p className="text-xs text-muted mt-1">Add scripts, reference docs, or assets</p>
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {attachments.map((file) => (
                        <div key={file.id} className="flex items-center justify-between px-3 py-2 rounded-lg border border-border bg-surface">
                          <div className="flex items-center gap-2">
                            <FileText className="w-4 h-4 text-muted" />
                            <div>
                              <p className="text-sm font-medium text-foreground">{file.name}</p>
                              <p className="text-xs text-muted">{file.size} · {file.type}</p>
                            </div>
                          </div>
                          <button
                            onClick={() => handleRemoveAttachment(file.id)}
                            className="p-1 rounded text-muted hover:text-error hover:bg-error-light/50 transition-colors"
                            aria-label={`Remove ${file.name}`}
                          >
                            <X className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      ))}
                      <Button variant="secondary" size="sm" className="w-full" icon={<Plus className="w-4 h-4" />}>
                        Add Attachment
                      </Button>
                    </div>
                  )}
                </div>
              )}
            </div>
          </Card>
        </div>

        {/* AI Assistant Panel */}
        {aiPanelOpen && (
          <motion.div
            initial={{ opacity: 0, x: 16, width: 0 }}
            animate={{ opacity: 1, x: 0, width: 360 }}
            exit={{ opacity: 0, x: 16, width: 0 }}
            transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
            className="shrink-0"
          >
            <Card padding="none" className="h-full flex flex-col overflow-hidden">
              <div className="flex items-center justify-between px-4 py-3 border-b border-border shrink-0">
                <div className="flex items-center gap-2">
                  <div className="p-1.5 rounded-lg bg-primary/10">
                    <Bot className="w-4 h-4 text-primary" />
                  </div>
                  <span className="text-sm font-semibold text-foreground">AI Assistant</span>
                </div>
                <button
                  onClick={() => setAiPanelOpen(false)}
                  className="p-1 rounded text-muted hover:text-foreground hover:bg-surface transition-colors"
                  aria-label="Close AI assistant"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              <div className="flex-1 overflow-y-auto p-4 space-y-3">
                {aiMessages.length === 0 && (
                  <div className="text-center py-6">
                    <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center mx-auto mb-3">
                      <Sparkles className="w-5 h-5 text-primary" />
                    </div>
                    <p className="text-sm font-medium text-foreground">How can I help?</p>
                    <p className="text-xs text-muted mt-1">Ask me to improve your skill content</p>
                  </div>
                )}
                {aiMessages.map((msg, i) => (
                  <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                    <div className={`max-w-[90%] rounded-xl px-3 py-2 text-sm ${
                      msg.role === 'user'
                        ? 'bg-primary text-primary-foreground'
                        : 'bg-surface text-foreground'
                    }`}>
                      <p className="whitespace-pre-wrap">{msg.content}</p>
                      {msg.role === 'assistant' && (
                        <div className="flex items-center gap-1 mt-2">
                          <Button
                            size="xs"
                            variant="ghost"
                            icon={<Zap className="w-3 h-3" />}
                            onClick={() => handleInsertAiSuggestion(msg.content)}
                          >
                            Insert
                          </Button>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
                {aiLoading && (
                  <div className="flex justify-start">
                    <div className="bg-surface rounded-xl px-3 py-2">
                      <div className="flex items-center gap-1.5">
                        <span className="h-1.5 w-1.5 rounded-full bg-muted animate-bounce" style={{ animationDelay: '0ms' }} />
                        <span className="h-1.5 w-1.5 rounded-full bg-muted animate-bounce" style={{ animationDelay: '150ms' }} />
                        <span className="h-1.5 w-1.5 rounded-full bg-muted animate-bounce" style={{ animationDelay: '300ms' }} />
                      </div>
                    </div>
                  </div>
                )}
              </div>

              <div className="border-t border-border p-3 shrink-0">
                <div className="flex items-center gap-2">
                  <input
                    type="text"
                    value={aiInput}
                    onChange={(e) => setAiInput(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleAiSend()}
                    placeholder="Ask AI for help..."
                    className="flex-1 h-8 px-3 rounded-lg border border-border bg-background text-xs text-foreground placeholder:text-muted focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary/40"
                    aria-label="AI assistant input"
                  />
                  <Button size="icon-sm" onClick={handleAiSend} disabled={!aiInput.trim() || aiLoading}>
                    <Send className="w-3.5 h-3.5" />
                  </Button>
                </div>
                <div className="flex flex-wrap gap-1 mt-2">
                  {['Write description', 'Suggest tests', 'Improve content', 'Add examples'].map((suggestion) => (
                    <button
                      key={suggestion}
                      onClick={() => { setAiInput(suggestion); }}
                      className="text-[10px] px-2 py-1 rounded-full bg-surface text-muted hover:text-foreground hover:bg-surface-hover transition-colors"
                    >
                      {suggestion}
                    </button>
                  ))}
                </div>
              </div>
            </Card>
          </motion.div>
        )}
      </div>
    </div>
  );
}

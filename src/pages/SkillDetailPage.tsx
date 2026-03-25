import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion } from 'motion/react';
import {
  ArrowLeft, Edit3, Users, Calendar, Tag, GitBranch,
  MessageSquare, Send, Copy, Check, Eye, Code, History,
  Settings, Shield, Download, MoreVertical, Play,
} from 'lucide-react';
import { Button, Badge, Card, Tabs, EmptyState, useToast, Avatar, Dropdown, DropdownItem, DropdownSeparator } from '../components/ui';
import { ROUTES } from '../constants/routes';

const MOCK_SKILL_DETAIL = {
  id: 'sql-optimizer',
  name: 'SQL Optimizer',
  description: 'Analyze and optimize complex SQL queries for Snowflake. Identifies bottlenecks, suggests index strategies, and rewrites inefficient patterns for maximum performance.',
  category: 'SQL',
  status: 'active' as const,
  version: '2.3.0',
  creator: 'Admin',
  createdDate: '2025-11-15',
  lastModified: '2026-04-02',
  usageCount: 1247,
  assignedUsers: 23,
  content: `## Overview

The SQL Optimizer skill analyzes your Snowflake queries and provides actionable recommendations for improving performance.

### Features

- **Query Analysis**: Deep inspection of execution plans
- **Bottleneck Detection**: Identifies slow joins, missing indexes, and inefficient patterns
- **Auto-Rewrite**: Suggests optimized query alternatives
- **Cost Estimation**: Predicts warehouse compute costs before execution

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
3. Use \`EXPLAIN\` to review execution plans
4. Monitor warehouse sizing for query patterns`,
  assignees: [
    { name: 'Sarah Chen', email: 'sarah@example.com', role: 'Admin' },
    { name: 'Mike Johnson', email: 'mike@example.com', role: 'Member' },
    { name: 'Emily Davis', email: 'emily@example.com', role: 'Member' },
    { name: 'Alex Rivera', email: 'alex@example.com', role: 'Viewer' },
  ],
  versions: [
    { version: '2.3.0', date: '2026-04-02', author: 'Admin', changes: 'Added cost estimation feature' },
    { version: '2.2.0', date: '2026-03-15', author: 'Admin', changes: 'Improved join optimization' },
    { version: '2.1.0', date: '2026-02-20', author: 'Admin', changes: 'Added EXPLAIN plan analysis' },
    { version: '2.0.0', date: '2026-01-10', author: 'Admin', changes: 'Major rewrite with new analysis engine' },
    { version: '1.0.0', date: '2025-11-15', author: 'Admin', changes: 'Initial release' },
  ],
};

export function SkillDetailPage() {
  const { skillId } = useParams<{ skillId: string }>();
  const navigate = useNavigate();
  const { toast } = useToast();
  const [activeTab, setActiveTab] = useState('overview');
  const [chatMessages, setChatMessages] = useState<Array<{ role: 'user' | 'assistant'; content: string }>>([]);
  const [chatInput, setChatInput] = useState('');
  const [chatLoading, setChatLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  const skill = MOCK_SKILL_DETAIL;

  const handleSendChat = () => {
    if (!chatInput.trim()) return;
    const userMsg = chatInput.trim();
    setChatMessages((prev) => [...prev, { role: 'user', content: userMsg }]);
    setChatInput('');
    setChatLoading(true);
    setTimeout(() => {
      setChatMessages((prev) => [...prev, { role: 'assistant', content: `Based on the SQL Optimizer skill, I'd recommend reviewing the query execution plan using EXPLAIN. The skill identifies join patterns, filter selectivity, and warehouse sizing to suggest optimizations.` }]);
      setChatLoading(false);
    }, 1200);
  };

  const handleCopyContent = async () => {
    await navigator.clipboard.writeText(skill.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
    toast('success', 'Skill content copied');
  };

  return (
    <div className="space-y-6 animate-fade-in-up">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
        <div className="flex items-start gap-4">
          <button
            onClick={() => navigate(ROUTES.SKILLS)}
            className="p-2 rounded-lg text-muted hover:text-foreground hover:bg-surface transition-colors shrink-0"
            aria-label="Back to skills"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-bold text-foreground">{skill.name}</h1>
              <Badge variant="success" dot>Active</Badge>
            </div>
            <p className="text-sm text-muted mt-1 max-w-2xl">{skill.description}</p>
            <div className="flex flex-wrap items-center gap-3 mt-3">
              <span className="flex items-center gap-1 text-xs text-muted">
                <Tag className="w-3.5 h-3.5" /> {skill.category}
              </span>
              <span className="flex items-center gap-1 text-xs text-muted">
                <GitBranch className="w-3.5 h-3.5" /> v{skill.version}
              </span>
              <span className="flex items-center gap-1 text-xs text-muted">
                <Users className="w-3.5 h-3.5" /> {skill.assignedUsers} assigned
              </span>
              <span className="flex items-center gap-1 text-xs text-muted">
                <Calendar className="w-3.5 h-3.5" /> Updated {new Date(skill.lastModified).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
              </span>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <Button variant="secondary" icon={<Play className="w-4 h-4" />} onClick={() => setActiveTab('preview')}>Test</Button>
          <Button variant="secondary" icon={<Edit3 className="w-4 h-4" />} onClick={() => navigate(`/skills/${skillId}/edit`)}>Edit</Button>
          <Dropdown
            trigger={
              <Button variant="secondary" size="icon"><MoreVertical className="w-4 h-4" /></Button>
            }
            align="end"
          >
            <DropdownItem icon={<Download className="w-4 h-4" />}>Export Skill</DropdownItem>
            <DropdownItem icon={<Shield className="w-4 h-4" />}>View Permissions</DropdownItem>
            <DropdownSeparator />
            <DropdownItem icon={<Settings className="w-4 h-4" />}>Skill Settings</DropdownItem>
          </Dropdown>
        </div>
      </div>

      {/* Tabs */}
      <Tabs
        tabs={[
          { key: 'overview', label: 'Overview', icon: <Eye className="w-4 h-4" /> },
          { key: 'preview', label: 'Preview', icon: <MessageSquare className="w-4 h-4" /> },
          { key: 'versions', label: 'Versions', icon: <GitBranch className="w-4 h-4" />, badge: skill.versions.length },
          { key: 'assignments', label: 'Assignments', icon: <Users className="w-4 h-4" />, badge: skill.assignees.length },
        ]}
        activeKey={activeTab}
        onChange={setActiveTab}
      />

      {/* Tab Content */}
      {activeTab === 'overview' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-4">
            <Card>
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-semibold text-foreground">Skill Content</h3>
                <Button size="sm" variant="ghost" icon={copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />} onClick={handleCopyContent}>
                  {copied ? 'Copied' : 'Copy'}
                </Button>
              </div>
              <div className="prose prose-sm max-w-none text-foreground">
                {skill.content.split('\n').map((line, i) => {
                  if (line.startsWith('## ')) return <h2 key={i} className="text-lg font-bold text-foreground mt-4 mb-2">{line.replace('## ', '')}</h2>;
                  if (line.startsWith('### ')) return <h3 key={i} className="text-base font-semibold text-foreground mt-3 mb-1.5">{line.replace('### ', '')}</h3>;
                  if (line.startsWith('- **')) {
                    const match = line.match(/- \*\*(.+?)\*\*: (.+)/);
                    if (match) return <li key={i} className="text-sm text-muted"><strong className="text-foreground">{match[1]}</strong>: {match[2]}</li>;
                  }
                  if (line.startsWith('- ')) return <li key={i} className="text-sm text-muted">{line.replace('- ', '')}</li>;
                  if (/^\d+\./.test(line)) {
                    const match = line.match(/^\d+\.\s+(.+)/);
                    if (match) return <li key={i} className="text-sm text-muted list-decimal ml-4">{match[1]}</li>;
                  }
                  if (line.startsWith('```')) return null;
                  if (line.trim() === '') return <br key={i} />;
                  if (line.startsWith('SELECT') || line.startsWith('--') || line.includes('FROM ') || line.includes('JOIN ') || line.includes('WHERE')) {
                    return <code key={i} className="block bg-surface px-3 py-1 rounded text-xs font-mono text-foreground my-0.5">{line}</code>;
                  }
                  return <p key={i} className="text-sm text-muted leading-relaxed">{line}</p>;
                })}
              </div>
            </Card>
          </div>

          {/* Sidebar */}
          <div className="space-y-4">
            <Card>
              <h3 className="text-sm font-semibold text-foreground mb-3">Metadata</h3>
              <dl className="space-y-3">
                {[
                  { label: 'Creator', value: skill.creator },
                  { label: 'Created', value: new Date(skill.createdDate).toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' }) },
                  { label: 'Last Modified', value: new Date(skill.lastModified).toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' }) },
                  { label: 'Version', value: `v${skill.version}` },
                  { label: 'Category', value: skill.category },
                  { label: 'Total Usage', value: skill.usageCount.toLocaleString() },
                  { label: 'Assigned Users', value: skill.assignedUsers.toString() },
                ].map(({ label, value }) => (
                  <div key={label} className="flex items-center justify-between">
                    <dt className="text-xs text-muted">{label}</dt>
                    <dd className="text-sm font-medium text-foreground">{value}</dd>
                  </div>
                ))}
              </dl>
            </Card>

            <Card>
              <h3 className="text-sm font-semibold text-foreground mb-3">Quick Assign</h3>
              <p className="text-xs text-muted mb-3">Assign this skill to users or teams</p>
              <Button size="sm" className="w-full" icon={<Users className="w-4 h-4" />}>Assign to Users</Button>
            </Card>
          </div>
        </div>
      )}

      {activeTab === 'preview' && (
        <Card padding="none" className="overflow-hidden">
          <div className="flex flex-col h-[500px]">
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {chatMessages.length === 0 && (
                <EmptyState
                  icon={<MessageSquare className="w-8 h-8" />}
                  title="Test this skill"
                  description="Send a message to see how the SQL Optimizer responds in real time."
                />
              )}
              {chatMessages.map((msg, i) => (
                <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-[80%] rounded-xl px-4 py-2.5 text-sm ${
                    msg.role === 'user'
                      ? 'bg-primary text-primary-foreground'
                      : 'bg-surface text-foreground'
                  }`}>
                    {msg.content}
                  </div>
                </div>
              ))}
              {chatLoading && (
                <div className="flex justify-start">
                  <div className="bg-surface rounded-xl px-4 py-2.5">
                    <div className="flex items-center gap-1.5">
                      <span className="h-1.5 w-1.5 rounded-full bg-muted animate-bounce" style={{ animationDelay: '0ms' }} />
                      <span className="h-1.5 w-1.5 rounded-full bg-muted animate-bounce" style={{ animationDelay: '150ms' }} />
                      <span className="h-1.5 w-1.5 rounded-full bg-muted animate-bounce" style={{ animationDelay: '300ms' }} />
                    </div>
                  </div>
                </div>
              )}
            </div>
            <div className="border-t border-border p-3">
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSendChat()}
                  placeholder="Ask the skill a question..."
                  className="flex-1 h-9 px-3 rounded-lg border border-border bg-background text-sm text-foreground placeholder:text-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
                  aria-label="Chat input"
                />
                <Button size="sm" icon={<Send className="w-4 h-4" />} onClick={handleSendChat} disabled={!chatInput.trim() || chatLoading}>
                  Send
                </Button>
              </div>
            </div>
          </div>
        </Card>
      )}

      {activeTab === 'versions' && (
        <Card>
          <div className="space-y-0">
            {skill.versions.map((v, i) => (
              <div key={v.version} className="flex items-start gap-4 py-4 relative">
                {i < skill.versions.length - 1 && (
                  <div className="absolute left-[11px] top-10 bottom-0 w-px bg-border" />
                )}
                <div className="h-6 w-6 rounded-full bg-primary flex items-center justify-center shrink-0">
                  <span className="text-[10px] font-bold text-primary-foreground">{v.version.split('.')[0]}</span>
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-foreground">v{v.version}</span>
                    {i === 0 && <Badge variant="success" size="sm">Latest</Badge>}
                  </div>
                  <p className="text-xs text-muted mt-0.5">{v.changes}</p>
                  <div className="flex items-center gap-3 mt-1">
                    <span className="text-[10px] text-muted">{v.author}</span>
                    <span className="text-[10px] text-muted">{new Date(v.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {activeTab === 'assignments' && (
        <Card padding="none">
          {skill.assignees.length === 0 ? (
            <EmptyState
              icon={<Users className="w-8 h-8" />}
              title="No assignments"
              description="Assign this skill to users or teams to get started."
              action={<Button icon={<Users className="w-4 h-4" />}>Assign Users</Button>}
            />
          ) : (
            <div className="divide-y divide-border">
              {skill.assignees.map((user) => (
                <div key={user.email} className="flex items-center justify-between px-5 py-3.5">
                  <div className="flex items-center gap-3">
                    <Avatar initials={user.name.split(' ').map(n => n[0]).join('')} alt={user.name} size="md" />
                    <div>
                      <p className="text-sm font-medium text-foreground">{user.name}</p>
                      <p className="text-xs text-muted">{user.email}</p>
                    </div>
                  </div>
                  <Badge variant={user.role === 'Admin' ? 'default' : user.role === 'Member' ? 'info' : 'secondary'} size="sm">{user.role}</Badge>
                </div>
              ))}
            </div>
          )}
        </Card>
      )}
    </div>
  );
}

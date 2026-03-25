import { useState, useMemo, useCallback, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'motion/react';
import {
  Plus, Search, LayoutGrid, List, Filter, Brain, Code2, Database,
  Zap, Shield, BarChart3, Users, ArrowUpRight, MoreVertical,
  Edit3, Trash2, Copy, Check, Power, Loader2, X, Sparkles,
  AlertTriangle, FileCode, Workflow, Network, Search as SearchIcon,
} from 'lucide-react';
import { Button, Badge, Card, EmptyState, Skeleton, PageSkeleton, useToast, Modal, Dropdown, DropdownItem, DropdownSeparator } from '../components/ui';
import { cn } from '../lib/cn';
import { useAuth } from '../auth';
import { ROUTES } from '../constants/routes';

interface Skill {
  id: string;
  name: string;
  description: string;
  category: string;
  status: 'active' | 'draft' | 'archived';
  usageCount: number;
  assignedUsers: number;
  lastModified: string;
  creator: string;
  version: string;
  icon: string;
}

const MOCK_SKILLS: Skill[] = [
  { id: 'sql-optimizer', name: 'SQL Optimizer', description: 'Analyze and optimize complex SQL queries for Snowflake. Identifies bottlenecks, suggests index strategies, and rewrites inefficient patterns.', category: 'SQL', status: 'active', usageCount: 1247, assignedUsers: 23, lastModified: '2026-04-02', creator: 'Admin', version: '2.3.0', icon: 'Zap' },
  { id: 'data-architect', name: 'Data Architect', description: 'Design scalable data models and warehouse architecture. Generates DDL, defines relationships, and ensures normalization best practices.', category: 'Design', status: 'active', usageCount: 892, assignedUsers: 15, lastModified: '2026-04-01', creator: 'Admin', version: '1.8.0', icon: 'Network' },
  { id: 'ml-engineer', name: 'ML Engineer', description: 'Build and deploy machine learning pipelines. Handles feature engineering, model training, and inference setup within Snowflake.', category: 'ML', status: 'active', usageCount: 634, assignedUsers: 8, lastModified: '2026-03-28', creator: 'Admin', version: '3.1.0', icon: 'Brain' },
  { id: 'stored-proc-writer', name: 'Stored Procedure Writer', description: 'Create, debug, and enhance Snowflake stored procedures with JavaScript and Python handlers.', category: 'SQL', status: 'active', usageCount: 456, assignedUsers: 12, lastModified: '2026-03-25', creator: 'Admin', version: '1.5.0', icon: 'FileCode' },
  { id: 'data-explorer', name: 'Data Explorer', description: 'Discover schemas, tables, and columns across your data warehouse. Auto-generates data dictionaries.', category: 'Discovery', status: 'active', usageCount: 2103, assignedUsers: 45, lastModified: '2026-04-03', creator: 'Admin', version: '4.0.0', icon: 'SearchIcon' },
  { id: 'warehouse-monitor', name: 'Warehouse Monitor', description: 'Analyze warehouse usage, query costs, and performance metrics. Provides optimization recommendations.', category: 'Analytics', status: 'active', usageCount: 378, assignedUsers: 7, lastModified: '2026-03-20', creator: 'Admin', version: '2.0.0', icon: 'BarChart3' },
  { id: 'data-quality', name: 'Data Quality Engineer', description: 'Define and enforce data quality rules. Creates automated validation checks and anomaly detection.', category: 'Analytics', status: 'draft', usageCount: 0, assignedUsers: 0, lastModified: '2026-04-03', creator: 'Admin', version: '0.1.0', icon: 'Shield' },
  { id: 'etl-builder', name: 'ETL Pipeline Builder', description: 'Design and orchestrate ETL workflows. Generates dbt models, Airflow DAGs, and Snowpipe configurations.', category: 'SQL', status: 'active', usageCount: 567, assignedUsers: 11, lastModified: '2026-03-15', creator: 'Admin', version: '2.1.0', icon: 'Workflow' },
  { id: 'security-auditor', name: 'Security Auditor', description: 'Audit access controls, PII detection, and compliance policies. Generates security reports.', category: 'Security', status: 'active', usageCount: 189, assignedUsers: 4, lastModified: '2026-03-10', creator: 'Admin', version: '1.2.0', icon: 'Shield' },
  { id: 'analytics-engineer', name: 'Analytics Engineer', description: 'Transform data and manage dbt models. Creates semantic layers and metric definitions.', category: 'Analytics', status: 'active', usageCount: 923, assignedUsers: 19, lastModified: '2026-03-30', creator: 'Admin', version: '3.0.0', icon: 'BarChart3' },
  { id: 'api-integration', name: 'API Integration', description: 'Build and manage external API integrations with Snowflake. Handles authentication, rate limiting, and data mapping.', category: 'AI', status: 'draft', usageCount: 0, assignedUsers: 0, lastModified: '2026-04-01', creator: 'Admin', version: '0.2.0', icon: 'Code2' },
  { id: 'metadata-inspector', name: 'Metadata Inspector', description: 'Explore metadata, lineage, and data governance information across the organization.', category: 'Discovery', status: 'active', usageCount: 445, assignedUsers: 9, lastModified: '2026-03-22', creator: 'Admin', version: '1.4.0', icon: 'Database' },
];

const categoryColors: Record<string, { bg: string; text: string; dot: string }> = {
  SQL: { bg: 'bg-blue-100 dark:bg-blue-900/30', text: 'text-blue-700 dark:text-blue-300', dot: 'bg-blue-500' },
  Discovery: { bg: 'bg-cyan-100 dark:bg-cyan-900/30', text: 'text-cyan-700 dark:text-cyan-300', dot: 'bg-cyan-500' },
  Design: { bg: 'bg-purple-100 dark:bg-purple-900/30', text: 'text-purple-700 dark:text-purple-300', dot: 'bg-purple-500' },
  ML: { bg: 'bg-rose-100 dark:bg-rose-900/30', text: 'text-rose-700 dark:text-rose-300', dot: 'bg-rose-500' },
  Analytics: { bg: 'bg-emerald-100 dark:bg-emerald-900/30', text: 'text-emerald-700 dark:text-emerald-300', dot: 'bg-emerald-500' },
  AI: { bg: 'bg-violet-100 dark:bg-violet-900/30', text: 'text-violet-700 dark:text-violet-300', dot: 'bg-violet-500' },
  Security: { bg: 'bg-amber-100 dark:bg-amber-900/30', text: 'text-amber-700 dark:text-amber-300', dot: 'bg-amber-500' },
};

const iconMap: Record<string, React.ReactNode> = {
  Zap: <Zap className="w-5 h-5" />,
  Network: <Network className="w-5 h-5" />,
  Brain: <Brain className="w-5 h-5" />,
  FileCode: <FileCode className="w-5 h-5" />,
  SearchIcon: <SearchIcon className="w-5 h-5" />,
  BarChart3: <BarChart3 className="w-5 h-5" />,
  Shield: <Shield className="w-5 h-5" />,
  Workflow: <Workflow className="w-5 h-5" />,
  Code2: <Code2 className="w-5 h-5" />,
  Database: <Database className="w-5 h-5" />,
};

const statusConfig: Record<string, { variant: 'success' | 'warning' | 'secondary'; label: string }> = {
  active: { variant: 'success', label: 'Active' },
  draft: { variant: 'warning', label: 'Draft' },
  archived: { variant: 'secondary', label: 'Archived' },
};

export function SkillsPage() {
  const { permissions } = useAuth();
  const { toast } = useToast();
  const navigate = useNavigate();
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [search, setSearch] = useState('');
  const [filterCategory, setFilterCategory] = useState<string>('all');
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [skills, setSkills] = useState<Skill[]>([]);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [selectedSkill, setSelectedSkill] = useState<Skill | null>(null);

  useEffect(() => {
    const timer = setTimeout(() => {
      setSkills(MOCK_SKILLS);
      setLoading(false);
    }, 600);
    return () => clearTimeout(timer);
  }, []);

  const filteredSkills = useMemo(() => {
    return skills.filter((skill) => {
      const matchesSearch = search === '' ||
        skill.name.toLowerCase().includes(search.toLowerCase()) ||
        skill.description.toLowerCase().includes(search.toLowerCase());
      const matchesCategory = filterCategory === 'all' || skill.category === filterCategory;
      const matchesStatus = filterStatus === 'all' || skill.status === filterStatus;
      return matchesSearch && matchesCategory && matchesStatus;
    });
  }, [skills, search, filterCategory, filterStatus]);

  const categories = useMemo(() => [...new Set(skills.map((s) => s.category))], [skills]);

  const toggleSelect = useCallback((id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const toggleSelectAll = useCallback(() => {
    if (selectedIds.size === filteredSkills.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(filteredSkills.map((s) => s.id)));
    }
  }, [filteredSkills, selectedIds.size]);

  const handleBulkAction = (action: string) => {
    toast('success', `${action} applied to ${selectedIds.size} skill${selectedIds.size > 1 ? 's' : ''}`);
    setSelectedIds(new Set());
  };

  const handleDelete = () => {
    if (!selectedSkill) return;
    setSkills((prev) => prev.filter((s) => s.id !== selectedSkill.id));
    setDeleteModalOpen(false);
    setSelectedSkill(null);
    toast('success', `Skill "${selectedSkill.name}" deleted`);
  };

  const handleCopyId = async (id: string) => {
    await navigator.clipboard.writeText(id);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
    toast('success', 'Skill ID copied to clipboard');
  };

  const allCategories = ['all', ...categories];
  const allStatuses = ['all', 'active', 'draft', 'archived'];

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <Skeleton variant="text" width={200} height={28} />
            <Skeleton variant="text" width={300} height={16} className="mt-2" />
          </div>
          <Skeleton variant="rectangular" width={120} height={36} />
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} variant="rectangular" height={80} className="rounded-xl" />)}
        </div>
        <div className="flex gap-3">
          <Skeleton variant="rectangular" width={240} height={36} />
          <Skeleton variant="rectangular" width={160} height={36} />
          <Skeleton variant="rectangular" width={100} height={36} />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} variant="rectangular" height={200} className="rounded-xl" />)}
        </div>
      </div>
    );
  }

  const stats = [
    { label: 'Total Skills', value: skills.length, change: '+2 this week', icon: <Brain className="w-4 h-4" />, color: 'text-primary' },
    { label: 'Active', value: skills.filter((s) => s.status === 'active').length, change: 'Running', icon: <Zap className="w-4 h-4" />, color: 'text-success' },
    { label: 'Total Usage', value: skills.reduce((a, s) => a + s.usageCount, 0).toLocaleString(), change: '+12% this month', icon: <ArrowUpRight className="w-4 h-4" />, color: 'text-info' },
    { label: 'Assigned Users', value: skills.reduce((a, s) => a + s.assignedUsers, 0), change: 'Across org', icon: <Users className="w-4 h-4" />, color: 'text-accent' },
  ];

  return (
    <div className="space-y-6 animate-fade-in-up">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Skill Library</h1>
          <p className="text-sm text-muted mt-1">Manage and organize AI skills across your organization</p>
        </div>
        <div className="flex items-center gap-2">
          {selectedIds.size > 0 && (
            <div className="flex items-center gap-2">
              <span className="text-sm text-muted">{selectedIds.size} selected</span>
              <Button size="sm" variant="secondary" onClick={() => handleBulkAction('Archive')}>Archive</Button>
              <Button size="sm" variant="danger" onClick={() => handleBulkAction('Delete')}>Delete</Button>
              <Button size="sm" variant="ghost" icon={<X className="w-3.5 h-3.5" />} onClick={() => setSelectedIds(new Set())} />
            </div>
          )}
          <Button
            icon={<Plus className="w-4 h-4" />}
            onClick={() => navigate(ROUTES.SKILL_STUDIO_NEW)}
          >
            Create Skill
          </Button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {stats.map((stat) => (
          <Card key={stat.label} padding="sm" hover>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-muted font-medium">{stat.label}</p>
                <p className="text-2xl font-bold text-foreground mt-1">{stat.value}</p>
                <p className="text-xs text-muted mt-0.5">{stat.change}</p>
              </div>
              <div className={cn('p-2 rounded-lg bg-surface', stat.color)}>{stat.icon}</div>
            </div>
          </Card>
        ))}
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted pointer-events-none" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search skills by name or description..."
            className="w-full h-9 pl-9 pr-3 rounded-lg border border-border bg-background text-sm text-foreground placeholder:text-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 focus-visible:border-primary transition-colors"
            aria-label="Search skills"
          />
        </div>
        <div className="flex items-center gap-2">
          <select
            value={filterCategory}
            onChange={(e) => setFilterCategory(e.target.value)}
            className="h-9 px-3 rounded-lg border border-border bg-background text-sm text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 appearance-none pr-8"
            aria-label="Filter by category"
          >
            {allCategories.map((cat) => (
              <option key={cat} value={cat}>{cat === 'all' ? 'All Categories' : cat}</option>
            ))}
          </select>
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="h-9 px-3 rounded-lg border border-border bg-background text-sm text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 appearance-none pr-8"
            aria-label="Filter by status"
          >
            {allStatuses.map((s) => (
              <option key={s} value={s}>{s === 'all' ? 'All Statuses' : s.charAt(0).toUpperCase() + s.slice(1)}</option>
            ))}
          </select>
          <div className="flex items-center gap-0.5 bg-surface border border-border rounded-lg p-0.5">
            <button
              onClick={() => setViewMode('grid')}
              className={cn(
                'p-1.5 rounded-md transition-colors',
                viewMode === 'grid' ? 'bg-background shadow-sm text-foreground' : 'text-muted hover:text-foreground',
              )}
              aria-label="Grid view"
            >
              <LayoutGrid className="w-4 h-4" />
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={cn(
                'p-1.5 rounded-md transition-colors',
                viewMode === 'list' ? 'bg-background shadow-sm text-foreground' : 'text-muted hover:text-foreground',
              )}
              aria-label="List view"
            >
              <List className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Results count */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted">
          Showing <span className="font-medium text-foreground">{filteredSkills.length}</span> of {skills.length} skills
        </p>
        {selectedIds.size === 0 && (
          <button
            onClick={toggleSelectAll}
            className="text-sm text-primary hover:underline"
          >
            Select all
          </button>
        )}
      </div>

      {/* Content */}
      {filteredSkills.length === 0 ? (
        <EmptyState
          icon={<Brain className="w-8 h-8" />}
          title="No skills found"
          description="Try adjusting your search or filters, or create a new skill."
          action={
            <Button icon={<Plus className="w-4 h-4" />} onClick={() => navigate(ROUTES.SKILL_STUDIO_NEW)}>
              Create Skill
            </Button>
          }
        />
      ) : viewMode === 'grid' ? (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          <AnimatePresence>
            {filteredSkills.map((skill, i) => (
              <motion.div
                key={skill.id}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ delay: i * 0.04, duration: 0.3 }}
              >
                <SkillCard
                  skill={skill}
                  selected={selectedIds.has(skill.id)}
                  onSelect={() => toggleSelect(skill.id)}
                  onNavigate={() => navigate(`/skills/${skill.id}`)}
                  onEdit={() => navigate(`/skills/${skill.id}/edit`)}
                  onDelete={() => { setSelectedSkill(skill); setDeleteModalOpen(true); }}
                  onCopyId={() => handleCopyId(skill.id)}
                  copiedId={copiedId}
                />
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      ) : (
        <div className="space-y-2">
          <AnimatePresence>
            {filteredSkills.map((skill, i) => (
              <motion.div
                key={skill.id}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ delay: i * 0.03, duration: 0.25 }}
              >
                <SkillRow
                  skill={skill}
                  selected={selectedIds.has(skill.id)}
                  onSelect={() => toggleSelect(skill.id)}
                  onNavigate={() => navigate(`/skills/${skill.id}`)}
                  onEdit={() => navigate(`/skills/${skill.id}/edit`)}
                  onDelete={() => { setSelectedSkill(skill); setDeleteModalOpen(true); }}
                  onCopyId={() => handleCopyId(skill.id)}
                  copiedId={copiedId}
                />
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      )}

      {/* Delete Modal */}
      <Modal
        isOpen={deleteModalOpen}
        onClose={() => { setDeleteModalOpen(false); setSelectedSkill(null); }}
        title="Delete Skill"
        subtitle={`This will permanently delete "${selectedSkill?.name}"`}
        footer={
          <>
            <Button variant="secondary" onClick={() => { setDeleteModalOpen(false); setSelectedSkill(null); }}>Cancel</Button>
            <Button variant="danger" onClick={handleDelete}>Delete</Button>
          </>
        }
      >
        <p className="text-sm text-muted">This action cannot be undone. All assignments and version history will be lost.</p>
      </Modal>
    </div>
  );
}

function SkillCard({ skill, selected, onSelect, onNavigate, onEdit, onDelete, onCopyId, copiedId }: {
  skill: Skill;
  selected: boolean;
  onSelect: () => void;
  onNavigate: () => void;
  onEdit: () => void;
  onDelete: () => void;
  onCopyId: () => void;
  copiedId: string | null;
}) {
  const catColors = categoryColors[skill.category] || categoryColors.SQL;
  const statusConf = statusConfig[skill.status];
  const icon = iconMap[skill.icon] || <Brain className="w-5 h-5" />;

  return (
    <Card
      padding="none"
      hover
      interactive
      className="group cursor-pointer"
      onClick={onNavigate}
    >
      <div className="p-4">
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-3">
            <div className={cn('p-2 rounded-lg', catColors.bg, catColors.text)}>
              {icon}
            </div>
            <div className="min-w-0">
              <h3 className="text-sm font-semibold text-foreground truncate group-hover:text-primary transition-colors">{skill.name}</h3>
              <div className="flex items-center gap-1.5 mt-0.5">
                <Badge variant={statusConf.variant} size="sm" dot>{statusConf.label}</Badge>
                <span className="text-[10px] text-muted">v{skill.version}</span>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
            <input
              type="checkbox"
              checked={selected}
              onChange={onSelect}
              className="h-4 w-4 rounded border-border text-primary focus:ring-primary/40"
              aria-label={`Select ${skill.name}`}
              onClick={(e) => e.stopPropagation()}
            />
            <Dropdown
              trigger={
                <button className="p-1 rounded-md text-muted hover:text-foreground hover:bg-surface transition-colors" aria-label="More actions">
                  <MoreVertical className="w-4 h-4" />
                </button>
              }
              align="end"
            >
              <DropdownItem icon={<Edit3 className="w-4 h-4" />} onClick={onEdit}>Edit</DropdownItem>
              <DropdownItem icon={copiedId === skill.id ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />} onClick={onCopyId}>
                {copiedId === skill.id ? 'Copied' : 'Copy ID'}
              </DropdownItem>
              <DropdownSeparator />
              <DropdownItem icon={<Trash2 className="w-4 h-4" />} destructive onClick={onDelete}>Delete</DropdownItem>
            </Dropdown>
          </div>
        </div>

        <p className="text-xs text-muted leading-relaxed line-clamp-2 mb-3">{skill.description}</p>

        <div className="flex items-center justify-between pt-3 border-t border-border">
          <div className="flex items-center gap-3">
            <span className="flex items-center gap-1 text-xs text-muted">
              <Users className="w-3.5 h-3.5" />
              {skill.assignedUsers}
            </span>
            <span className="flex items-center gap-1 text-xs text-muted">
              <Zap className="w-3.5 h-3.5" />
              {skill.usageCount.toLocaleString()}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="outline" size="sm">{skill.category}</Badge>
            <span className="text-[10px] text-muted">
              {new Date(skill.lastModified).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
            </span>
          </div>
        </div>
      </div>
    </Card>
  );
}

function SkillRow({ skill, selected, onSelect, onNavigate, onEdit, onDelete, onCopyId, copiedId }: {
  skill: Skill;
  selected: boolean;
  onSelect: () => void;
  onNavigate: () => void;
  onEdit: () => void;
  onDelete: () => void;
  onCopyId: () => void;
  copiedId: string | null;
}) {
  const catColors = categoryColors[skill.category] || categoryColors.SQL;
  const statusConf = statusConfig[skill.status];
  const icon = iconMap[skill.icon] || <Brain className="w-5 h-5" />;

  return (
    <div
      className={cn(
        'flex items-center gap-4 px-4 py-3 rounded-xl border border-border bg-surface-elevated hover:border-border-hover hover:shadow-sm transition-all cursor-pointer',
        selected && 'border-primary/40 bg-primary-lighter/30',
      )}
      onClick={onNavigate}
    >
      <input
        type="checkbox"
        checked={selected}
        onChange={onSelect}
        className="h-4 w-4 rounded border-border text-primary focus:ring-primary/40 shrink-0"
        aria-label={`Select ${skill.name}`}
        onClick={(e) => e.stopPropagation()}
      />
      <div className={cn('p-2 rounded-lg shrink-0', catColors.bg, catColors.text)}>
        {icon}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-semibold text-foreground truncate group-hover:text-primary">{skill.name}</h3>
          <Badge variant={statusConf.variant} size="sm" dot>{statusConf.label}</Badge>
          <Badge variant="outline" size="sm">{skill.category}</Badge>
        </div>
        <p className="text-xs text-muted truncate mt-0.5">{skill.description}</p>
      </div>
      <div className="hidden sm:flex items-center gap-4 shrink-0">
        <span className="flex items-center gap-1 text-xs text-muted">
          <Users className="w-3.5 h-3.5" />
          {skill.assignedUsers}
        </span>
        <span className="flex items-center gap-1 text-xs text-muted">
          <Zap className="w-3.5 h-3.5" />
          {skill.usageCount.toLocaleString()}
        </span>
        <span className="text-xs text-muted w-20 text-right">
          {new Date(skill.lastModified).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
        </span>
      </div>
      <div className="flex items-center gap-1 shrink-0" onClick={(e) => e.stopPropagation()}>
        <button onClick={onEdit} className="p-1.5 rounded-md text-muted hover:text-foreground hover:bg-surface transition-colors" aria-label="Edit skill">
          <Edit3 className="w-4 h-4" />
        </button>
        <button onClick={onCopyId} className="p-1.5 rounded-md text-muted hover:text-foreground hover:bg-surface transition-colors" aria-label="Copy skill ID">
          {copiedId === skill.id ? <Check className="w-4 h-4 text-success" /> : <Copy className="w-4 h-4" />}
        </button>
        <button onClick={onDelete} className="p-1.5 rounded-md text-muted hover:text-error hover:bg-error-light/50 transition-colors" aria-label="Delete skill">
          <Trash2 className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}

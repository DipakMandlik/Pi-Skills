import React, { useState, useEffect } from 'react';
import { motion } from 'motion/react';
import { AreaChart, Area, ResponsiveContainer, XAxis, YAxis, Tooltip, BarChart, Bar } from 'recharts';
import {
  Activity, Clock, Database, Users, Zap, AlertCircle, Search, Download, BarChart3
} from 'lucide-react';
import { useAuth } from '../../auth';
import { Card, MetricCard, DataTable, StatusBadge, EmptyState, Tabs } from '../common';
import type { Column } from '../common';
import { useToast } from '../common';
import { fetchMonitoring, type AuditLogEntry, type MonitoringData } from '../../services/backendApi';
import { getUserFacingError } from '../../services/errorUtils';

interface LogEntry {
  id: string;
  timestamp: string;
  user: string;
  action: string;
  target: string;
  status: 'success' | 'error' | 'warning';
  duration: string;
}

function mapLog(e: AuditLogEntry): LogEntry {
  return {
    id: e.id,
    timestamp: new Date(e.timestamp).toLocaleString(),
    user: e.user_id ? e.user_id.slice(0, 8) : 'system',
    action: e.action,
    target: [e.skill_id, e.model_id].filter(Boolean).join(' → ') || '—',
    status: e.outcome === 'SUCCESS' ? 'success' : e.outcome === 'ERROR' ? 'error' : 'warning',
    duration: e.latency_ms != null ? `${e.latency_ms}ms` : '—',
  };
}

const statusDotColors: Record<string, string> = {
  success: 'bg-emerald-400',
  error: 'bg-red-400',
  warning: 'bg-amber-400',
};

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-white border border-[var(--color-border)] rounded-lg shadow-lg px-3 py-2 text-xs">
      <p className="font-semibold text-[var(--color-text-main)] mb-1">{label}</p>
      {payload.map((entry: any, i: number) => (
        <div key={i} className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full" style={{ background: entry.color }} />
          <span className="text-[var(--color-text-muted)]">{entry.name}:</span>
          <span className="font-mono font-medium">{entry.value}</span>
        </div>
      ))}
    </div>
  );
};

export function MonitoringView() {
  const { permissions, user } = useAuth();
  const isAdmin = permissions.viewAllMonitoring;
  const { toast } = useToast();

  const [data, setData] = useState<MonitoringData | null>(null);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterAction, setFilterAction] = useState<string>('all');
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [timeRange, setTimeRange] = useState('24h');
  const [loadError, setLoadError] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const result = await fetchMonitoring({ page_size: 100 });
      setData(result);
    } catch (e) {
      const message = getUserFacingError(e, 'Failed to load monitoring data');
      setLoadError(message);
      toast('error', message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadData(); }, [timeRange]);

  const logs = data ? data.logs.map(mapLog) : [];

  const filteredLogs = logs.filter((log) => {
    const matchesSearch = log.action.toLowerCase().includes(searchQuery.toLowerCase()) ||
      log.target.toLowerCase().includes(searchQuery.toLowerCase()) ||
      log.user.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesAction = filterAction === 'all' || log.action === filterAction;
    const matchesStatus = filterStatus === 'all' || log.status === filterStatus;
    return matchesSearch && matchesAction && matchesStatus;
  });

  const uniqueActions = Array.from(new Set(logs.map((l) => l.action)));
  const totalExecutions = data?.summary.total_executions ?? 0;
  const errorCount = data?.summary.total_denials ?? 0;
  const totalTokens = data?.summary.total_tokens ?? 0;
  const avgDuration = data ? `${Math.round(data.summary.avg_latency_ms)}ms` : '—';

  const logColumns: Column<LogEntry>[] = [
    {
      key: 'timestamp',
      header: 'Time',
      sortable: true,
      render: (val) => <span className="text-xs font-mono text-[var(--color-text-muted)] tabular-nums">{val as string}</span>,
    },
    ...(isAdmin ? [{
      key: 'user',
      header: 'User',
      sortable: true,
      render: (val: unknown) => (
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-md bg-gradient-to-br from-[var(--color-accent)] to-[var(--color-accent-secondary)] flex items-center justify-center text-white text-[10px] font-bold">
            {(val as string).charAt(0).toUpperCase()}
          </div>
          <span className="text-sm font-medium text-[var(--color-text-main)]">{val as string}</span>
        </div>
      ),
    }] : []),
    {
      key: 'action',
      header: 'Action',
      sortable: true,
      render: (val) => (
        <span className="text-xs font-mono font-medium px-2 py-0.5 rounded-md bg-[var(--color-surface)] text-[var(--color-text-main)]">
          {val as string}
        </span>
      ),
    },
    {
      key: 'target',
      header: 'Target',
      render: (val) => (
        <span className="text-xs font-mono text-[var(--color-text-muted)] truncate max-w-[240px] block" title={val as string}>
          {val as string}
        </span>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      sortable: true,
      render: (val) => (
        <div className="flex items-center gap-1.5">
          <span className={`w-1.5 h-1.5 rounded-full ${statusDotColors[val as string]}`} />
          <StatusBadge status={val as 'success' | 'error' | 'warning'} />
        </div>
      ),
    },
    {
      key: 'duration',
      header: 'Duration',
      align: 'right',
      render: (val) => (
        <span className="text-xs font-mono tabular-nums text-[var(--color-text-muted)]">
          {val as string}
        </span>
      ),
    },
  ];

  if (loading) {
    return <div className="p-6 text-center text-[var(--color-text-muted)]">Loading monitoring data...</div>;
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="flex items-start justify-between">
        <div>
          <h2 className="text-xl font-bold text-[var(--color-text-main)]">
            {isAdmin ? 'System Monitoring' : 'My Activity'}
          </h2>
          <p className="text-sm text-[var(--color-text-muted)] mt-0.5">
            {isAdmin ? 'Usage metrics, audit logs, and execution tracking' : 'Your recent activity and query history'}
          </p>
        </div>
        <div className="flex items-center gap-1 bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl p-0.5">
          {(['1h', '24h', '7d', '30d'] as const).map((range) => (
            <button
              key={range}
              onClick={() => setTimeRange(range)}
              className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
                timeRange === range ? 'bg-white text-[var(--color-text-main)] shadow-sm' : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-main)]'
              }`}
            >
              {range}
            </button>
          ))}
        </div>
      </motion.div>

      {loadError && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex items-center gap-2 px-4 py-3 bg-red-50 border border-red-200 rounded-xl">
          <AlertCircle className="w-4 h-4 text-red-500 shrink-0" />
          <span className="text-sm text-red-700">{loadError}</span>
        </motion.div>
      )}

      {/* Metrics */}
      <div className={`grid grid-cols-1 sm:grid-cols-2 ${isAdmin ? 'lg:grid-cols-4' : 'lg:grid-cols-3'} gap-4`}>
        <MetricCard label="Total Executions" value={totalExecutions} subtitle="In selected period" icon={<Database className="w-4 h-4" />} color="blue" delay={0} />
        <MetricCard label="Total Denials" value={errorCount} subtitle="Blocked requests" icon={<AlertCircle className="w-4 h-4" />} color={errorCount > 0 ? 'rose' : 'emerald'} delay={1} />
        {isAdmin && <MetricCard label="Total Tokens" value={totalTokens} subtitle="Consumed" icon={<Users className="w-4 h-4" />} color="emerald" delay={2} />}
        <MetricCard label="Avg Latency" value={avgDuration} subtitle="Execution time" icon={<Clock className="w-4 h-4" />} color="purple" delay={isAdmin ? 3 : 2} />
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className="relative flex-1 min-w-[200px] max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--color-text-light)]" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search logs..."
            className="w-full pl-9 pr-3 py-2 bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl text-sm text-[var(--color-text-main)] placeholder:text-[var(--color-text-light)] focus:outline-none focus:border-[var(--color-accent)] focus:bg-white focus:ring-2 focus:ring-[var(--color-accent)]/10 transition-all"
          />
        </div>
        <select
          value={filterAction}
          onChange={(e) => setFilterAction(e.target.value)}
          className="px-3 py-2 bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl text-sm text-[var(--color-text-main)] focus:outline-none focus:border-[var(--color-accent)] transition-colors"
        >
          <option value="all">All Actions</option>
          {uniqueActions.map((action) => <option key={action} value={action}>{action}</option>)}
        </select>
        <select
          value={filterStatus}
          onChange={(e) => setFilterStatus(e.target.value)}
          className="px-3 py-2 bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl text-sm text-[var(--color-text-main)] focus:outline-none focus:border-[var(--color-accent)] transition-colors"
        >
          <option value="all">All Statuses</option>
          <option value="success">Success</option>
          <option value="error">Error</option>
          <option value="warning">Warning</option>
        </select>
      </div>

      {/* Logs Table */}
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.25 }}>
        <DataTable
          columns={logColumns}
          data={filteredLogs}
          emptyMessage="No logs match your filters"
          rowKey="id"
          compact
          paginated
          defaultPageSize={10}
          striped
        />
      </motion.div>
    </div>
  );
}

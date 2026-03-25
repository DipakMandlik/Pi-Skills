import React, { useState, useEffect } from 'react';
import { motion } from 'motion/react';
import { AreaChart, Area, ResponsiveContainer, XAxis, YAxis, Tooltip } from 'recharts';
import { Puzzle, Brain, Activity, Clock, Sparkles, Database, ArrowUpRight, CheckCircle2, Timer, Zap, RefreshCw, AlertCircle } from 'lucide-react';
import { MetricCard, Card, StatusBadge, Skeleton, EmptyState } from '../common';
import { useNavigate } from 'react-router-dom';
import { ROUTES } from '../../constants/routes';
import { fetchDashboardData, fetchQueryHistory, type DashboardData, type QueryHistoryEntry } from '../../api/snowflakeService';

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-white border border-[var(--color-border)] rounded-lg shadow-lg px-3 py-2 text-xs">
      <p className="font-semibold text-[var(--color-text-main)]">{label}</p>
      <p className="text-[var(--color-text-muted)]">{payload[0].value} rows</p>
    </div>
  );
};

export function UserDashboard() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null);
  const [queryHistory, setQueryHistory] = useState<QueryHistoryEntry[]>([]);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [data, history] = await Promise.allSettled([
        fetchDashboardData(),
        fetchQueryHistory(10),
      ]);
      if (data.status === 'fulfilled') setDashboardData(data.value);
      if (history.status === 'fulfilled') setQueryHistory(history.value);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load dashboard');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadData(); }, []);

  const chartData = queryHistory.length > 0
    ? queryHistory.slice(0, 7).reverse().map((q, i) => ({
        day: `Q${i + 1}`,
        queries: q.rows_produced || 1,
      }))
    : [
        { day: 'Mon', queries: 0 }, { day: 'Tue', queries: 0 }, { day: 'Wed', queries: 0 },
        { day: 'Thu', queries: 0 }, { day: 'Fri', queries: 0 }, { day: 'Sat', queries: 0 }, { day: 'Sun', queries: 0 },
      ];

  const sparkline = queryHistory.slice(0, 7).map((q) => q.rows_produced || 0);

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}
        className="flex items-start justify-between">
        <div>
          <h2 className="text-xl font-bold text-[var(--color-text-main)]">My Dashboard</h2>
          <p className="text-sm text-[var(--color-text-muted)] mt-0.5">Your databases, tables, and recent activity from Snowflake</p>
        </div>
        <button onClick={loadData} disabled={loading}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-[var(--color-text-muted)] hover:text-[var(--color-text-main)] bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl transition-colors disabled:opacity-50">
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} /> Refresh
        </button>
      </motion.div>

      {/* Error */}
      {error && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}
          className="flex items-center gap-2 px-4 py-3 bg-red-50 border border-red-200 rounded-xl">
          <AlertCircle className="w-4 h-4 text-red-500 shrink-0" />
          <span className="text-sm text-red-700">{error}</span>
          <button onClick={loadData} className="ml-auto text-xs font-medium text-red-600 underline">Retry</button>
        </motion.div>
      )}

      {/* Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {loading ? (
          <>
            <Card padding="md"><Skeleton variant="text" width={80} height={12} /><Skeleton variant="text" width={60} height={28} className="mt-2" /></Card>
            <Card padding="md"><Skeleton variant="text" width={80} height={12} /><Skeleton variant="text" width={60} height={28} className="mt-2" /></Card>
            <Card padding="md"><Skeleton variant="text" width={80} height={12} /><Skeleton variant="text" width={60} height={28} className="mt-2" /></Card>
          </>
        ) : (
          <>
            <MetricCard label="Databases" value={dashboardData?.totalDatabases || 0}
              subtitle="Snowflake databases" icon={<Database className="w-4 h-4" />} color="blue" delay={0} />
            <MetricCard label="Tables" value={dashboardData?.totalTables || 0}
              subtitle="Across all schemas" icon={<Puzzle className="w-4 h-4" />} color="purple" delay={1} />
            <MetricCard label="Queries" value={queryHistory.length}
              subtitle="Recent history" icon={<Activity className="w-4 h-4" />} color="emerald"
              trend={queryHistory.length > 0 ? 'up' : undefined} trendValue={queryHistory.length > 0 ? 'Active' : undefined}
              sparkline={sparkline.length > 2 ? sparkline : undefined} delay={2} />
          </>
        )}
      </div>

      {/* Content */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Databases */}
        <Card padding="none">
          <div className="px-5 py-4 border-b border-[var(--color-border)] flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Database className="w-4 h-4 text-blue-500" />
              <h3 className="text-sm font-semibold text-[var(--color-text-main)]">Databases</h3>
            </div>
            {!loading && dashboardData && (
              <span className="text-[10px] font-mono text-[var(--color-text-muted)] bg-[var(--color-surface)] px-1.5 py-0.5 rounded">
                {dashboardData.totalDatabases} found
              </span>
            )}
          </div>
          <div className="divide-y divide-[var(--color-border)] max-h-[300px] overflow-y-auto">
            {loading ? (
              [1, 2, 3].map((i) => (
                <div key={i} className="px-5 py-3"><Skeleton variant="text" width="60%" height={14} /></div>
              ))
            ) : dashboardData && dashboardData.databases.length > 0 ? (
              dashboardData.databases.slice(0, 10).map((db, i) => (
                <motion.div key={db} initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.04 }}
                  className="flex items-center gap-3 px-5 py-3 hover:bg-[var(--color-surface)]/50 transition-colors cursor-pointer"
                  onClick={() => navigate(ROUTES.WORKSPACE)}>
                  <div className="w-8 h-8 rounded-lg bg-blue-50 flex items-center justify-center">
                    <Database className="w-4 h-4 text-blue-500" />
                  </div>
                  <span className="text-sm font-medium text-[var(--color-text-main)] font-mono">{db}</span>
                </motion.div>
              ))
            ) : (
              <EmptyState icon={<Database className="w-6 h-6" />} title="No databases found"
                message="Connect to Snowflake to see your databases." />
            )}
          </div>
        </Card>

        {/* Warehouses */}
        <Card padding="none">
          <div className="px-5 py-4 border-b border-[var(--color-border)]">
            <div className="flex items-center gap-2">
              <Zap className="w-4 h-4 text-amber-500" />
              <h3 className="text-sm font-semibold text-[var(--color-text-main)]">Warehouses</h3>
            </div>
          </div>
          <div className="divide-y divide-[var(--color-border)]">
            {loading ? (
              [1, 2].map((i) => (
                <div key={i} className="px-5 py-4">
                  <Skeleton variant="text" width="40%" height={14} />
                  <Skeleton variant="text" width="60%" height={12} className="mt-1" />
                </div>
              ))
            ) : dashboardData && dashboardData.warehouses.length > 0 ? (
              dashboardData.warehouses.map((wh, i) => (
                <motion.div key={wh.name} initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.06 }}
                  className="flex items-center justify-between px-5 py-4 hover:bg-[var(--color-surface)]/50 transition-colors">
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-xl bg-amber-50 flex items-center justify-center">
                      <Zap className="w-4 h-4 text-amber-500" />
                    </div>
                    <div>
                      <span className="text-sm font-semibold text-[var(--color-text-main)]">{wh.name}</span>
                      <p className="text-[11px] text-[var(--color-text-muted)]">{wh.size || '—'} · {wh.running} active</p>
                    </div>
                  </div>
                  <StatusBadge status={wh.state === 'RUNNING' ? 'active' : wh.state === 'SUSPENDED' ? 'expired' : 'pending'} label={wh.state} />
                </motion.div>
              ))
            ) : (
              <EmptyState icon={<Zap className="w-6 h-6" />} title="No warehouses" message="Warehouse data will appear after connection." />
            )}
          </div>
        </Card>
      </div>

      {/* Recent Queries */}
      <Card padding="none">
        <div className="px-5 py-4 border-b border-[var(--color-border)] flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4 text-[var(--color-accent)]" />
            <h3 className="text-sm font-semibold text-[var(--color-text-main)]">Recent Queries</h3>
          </div>
          <button onClick={() => navigate(ROUTES.WORKSPACE)}
            className="text-xs text-[var(--color-accent)] hover:text-[var(--color-accent-hover)] font-medium flex items-center gap-1 transition-colors">
            Open workspace <ArrowUpRight className="w-3 h-3" />
          </button>
        </div>
        <div className="divide-y divide-[var(--color-border)]">
          {loading ? (
            [1, 2, 3].map((i) => (
              <div key={i} className="px-5 py-3">
                <div className="flex items-center gap-3">
                  <Skeleton variant="rectangular" width={32} height={32} className="rounded-lg" />
                  <div className="flex-1"><Skeleton variant="text" width="70%" height={12} /></div>
                  <Skeleton variant="text" width={60} height={12} />
                </div>
              </div>
            ))
          ) : queryHistory.length > 0 ? (
            queryHistory.slice(0, 6).map((q, i) => (
              <motion.div key={q.id} initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                transition={{ delay: i * 0.04 }}
                onClick={() => navigate(ROUTES.WORKSPACE)}
                className="flex items-center gap-3 px-5 py-3 hover:bg-[var(--color-surface)]/50 transition-colors cursor-pointer group/row">
                <div className="w-8 h-8 rounded-lg bg-[var(--color-surface)] flex items-center justify-center shrink-0">
                  <Database className="w-3.5 h-3.5 text-[var(--color-text-muted)]" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-mono text-[var(--color-text-main)] truncate">{q.query_text}</p>
                </div>
                <div className="flex items-center gap-3 shrink-0 text-[11px] text-[var(--color-text-muted)]">
                  <StatusBadge status={q.status === 'ERROR' ? 'error' : 'success'} />
                  <span className="tabular-nums">{q.rows_produced} rows</span>
                  <span className="font-mono tabular-nums text-[var(--color-text-light)]">{q.total_elapsed_time}ms</span>
                </div>
              </motion.div>
            ))
          ) : (
            <div className="px-5 py-12 text-center text-sm text-[var(--color-text-muted)]">
              No recent queries. Run a query in the workspace to see activity here.
            </div>
          )}
        </div>
      </Card>

      {/* CTA */}
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.5 }}>
        <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-blue-600 to-cyan-600 p-6 text-white">
          <div className="absolute inset-0 opacity-10" style={{
            backgroundImage: 'radial-gradient(circle at 20% 50%, rgba(255,255,255,0.3) 0%, transparent 50%), radial-gradient(circle at 80% 50%, rgba(255,255,255,0.2) 0%, transparent 50%)',
          }} />
          <div className="relative z-10 flex items-center justify-between">
            <div>
              <h3 className="text-lg font-bold mb-1">Ready to query?</h3>
              <p className="text-sm text-blue-100 max-w-md">
                Open the workspace to chat with your AI skills and run SQL queries against your Snowflake data.
              </p>
            </div>
            <button onClick={() => navigate(ROUTES.WORKSPACE)}
              className="flex items-center gap-2 px-5 py-2.5 bg-white text-blue-600 text-sm font-semibold rounded-xl hover:bg-blue-50 transition-colors shadow-lg shadow-black/10 shrink-0">
              Open Workspace <ArrowUpRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </motion.div>
    </div>
  );
}

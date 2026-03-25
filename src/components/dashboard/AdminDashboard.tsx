import { useState, useEffect } from 'react';
import { motion } from 'motion/react';
import { AreaChart, Area, ResponsiveContainer, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts';
import {
  Users, Puzzle, Brain, Activity, TrendingUp, Clock, Database, Zap,
  ArrowUpRight, BarChart3, Layers, AlertCircle, RefreshCw, Plus, UserPlus, Settings, Shield
} from 'lucide-react';
import { MetricCard, Card, StatusBadge, Tabs, Skeleton, MetricCardSkeleton } from '../common';
import { useNavigate } from 'react-router-dom';
import { ROUTES } from '../../constants/routes';
import { fetchDashboardData, fetchQueryHistory, type DashboardData, type QueryHistoryEntry } from '../../api/snowflakeService';
import { mcpClient } from '../../api/mcpClient';
import { cn } from '../../lib/cn';

const CustomTooltip = ({ active, payload, label }: { active?: boolean; payload?: Array<{ color: string; name: string; value: number }>; label?: string }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-surface-elevated border border-border rounded-lg shadow-lg px-3 py-2 text-xs">
      <p className="font-semibold text-foreground mb-1">{label}</p>
      {payload.map((entry, i) => (
        <div key={i} className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full" style={{ background: entry.color }} />
          <span className="text-muted">{entry.name}:</span>
          <span className="font-mono font-medium text-foreground">{entry.value}</span>
        </div>
      ))}
    </div>
  );
};

export function AdminDashboard() {
  const navigate = useNavigate();
  const [chartTab, setChartTab] = useState('queries');
  const [loading, setLoading] = useState(true);
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null);
  const [queryHistory, setQueryHistory] = useState<QueryHistoryEntry[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [backendStatus, setBackendStatus] = useState<'ok' | 'degraded' | 'error'>('degraded');

  const loadData = async () => {
    setLoading(true);
    setError(null);

    try {
      try {
        const health = await mcpClient.getHealth({ timeoutMs: 3000 });
        setBackendStatus((health as any).snowflake_connector_ready ? 'ok' : 'degraded');
      } catch {
        setBackendStatus('error');
      }

      const [data, history] = await Promise.allSettled([
        fetchDashboardData(),
        fetchQueryHistory(10),
      ]);

      if (data.status === 'fulfilled') setDashboardData(data.value);
      if (history.status === 'fulfilled') setQueryHistory(history.value);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const queryTrend = queryHistory.length > 0
    ? queryHistory.slice(0, 7).reverse().map((q, i) => ({
        day: `Q${i + 1}`,
        queries: q.rows_produced || 1,
        errors: q.status === 'ERROR' ? 1 : 0,
        elapsed: q.total_elapsed_time,
      }))
    : [
        { day: 'Mon', queries: 0, errors: 0, elapsed: 0 },
        { day: 'Tue', queries: 0, errors: 0, elapsed: 0 },
        { day: 'Wed', queries: 0, errors: 0, elapsed: 0 },
        { day: 'Thu', queries: 0, errors: 0, elapsed: 0 },
        { day: 'Fri', queries: 0, errors: 0, elapsed: 0 },
        { day: 'Sat', queries: 0, errors: 0, elapsed: 0 },
        { day: 'Sun', queries: 0, errors: 0, elapsed: 0 },
      ];

  const recentActivity = queryHistory.slice(0, 6).map((q) => ({
    id: q.id,
    user: q.user_name || 'System',
    action: 'Executed query',
    target: q.query_text.length > 60 ? q.query_text.substring(0, 60) + '...' : q.query_text,
    time: q.start_time ? new Date(q.start_time).toLocaleTimeString() : '—',
    type: q.status === 'ERROR' ? 'error' : 'query',
    status: q.status === 'ERROR' ? 'error' : q.status === 'RUNNING' ? 'warning' : 'success',
  }));

  const actionColors: Record<string, string> = {
    query: 'bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-300',
    error: 'bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-300',
    create: 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-300',
  };

  return (
    <div className="space-y-6 animate-fade-in-up">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="flex flex-col sm:flex-row sm:items-center justify-between gap-4"
      >
        <div>
          <h1 className="text-2xl font-bold text-foreground">System Overview</h1>
          <p className="text-sm text-muted mt-1">
            Live data from your Snowflake environment
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={loadData}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-muted hover:text-foreground bg-surface border border-border rounded-lg hover:border-border-hover transition-colors disabled:opacity-50"
          >
            <RefreshCw className={cn('w-3.5 h-3.5', loading && 'animate-spin')} />
            Refresh
          </button>
          <div className={cn(
            'flex items-center gap-1.5 text-[11px] font-medium px-3 py-1.5 rounded-full',
            backendStatus === 'ok' ? 'text-success bg-success-light' :
            backendStatus === 'degraded' ? 'text-warning bg-warning-light' :
            'text-error bg-error-light',
          )}>
            <span className="relative flex h-2 w-2">
              {backendStatus === 'ok' && <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-success opacity-40" />}
              <span className={cn(
                'relative inline-flex rounded-full h-2 w-2',
                backendStatus === 'ok' ? 'bg-success' : backendStatus === 'degraded' ? 'bg-warning' : 'bg-error',
              )} />
            </span>
            {backendStatus === 'ok' ? 'Snowflake Connected' : backendStatus === 'degraded' ? 'Degraded' : 'Disconnected'}
          </div>
        </div>
      </motion.div>

      {/* Error banner */}
      {error && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex items-center gap-2 px-4 py-3 bg-error-light border border-error/20 rounded-xl">
          <AlertCircle className="w-4 h-4 text-error shrink-0" />
          <span className="text-sm text-error">{error}</span>
        </motion.div>
      )}

      {/* Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {loading ? (
          <>
            <MetricCardSkeleton />
            <MetricCardSkeleton />
            <MetricCardSkeleton />
            <MetricCardSkeleton />
          </>
        ) : (
          <>
            <MetricCard
              label="Databases"
              value={dashboardData?.totalDatabases || 0}
              subtitle="Snowflake databases"
              icon={<Database className="w-4 h-4" />}
              color="blue"
              delay={0}
            />
            <MetricCard
              label="Tables"
              value={dashboardData?.totalTables || 0}
              subtitle="Across all schemas"
              icon={<Layers className="w-4 h-4" />}
              color="emerald"
              delay={1}
            />
            <MetricCard
              label="Warehouses"
              value={dashboardData?.totalWarehouses || 0}
              subtitle={`${dashboardData?.runningWarehouses || 0} running`}
              icon={<Zap className="w-4 h-4" />}
              color="purple"
              delay={2}
            />
            <MetricCard
              label="Queries"
              value={queryHistory.length}
              subtitle="Recent query history"
              icon={<Activity className="w-4 h-4" />}
              color="amber"
              live={backendStatus === 'ok'}
              delay={3}
            />
          </>
        )}
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card className="lg:col-span-2" padding="none">
          <div className="px-5 py-4 border-b border-border flex items-center justify-between">
            <div className="flex items-center gap-2">
              <BarChart3 className="w-4 h-4 text-primary" />
              <h3 className="text-sm font-semibold text-foreground">Query Trends</h3>
              <span className="text-[10px] text-muted bg-surface px-1.5 py-0.5 rounded font-mono">Live</span>
            </div>
          </div>
          <div className="p-5">
            {loading ? (
              <div className="h-[200px] bg-surface rounded-xl animate-pulse" />
            ) : (
              <ResponsiveContainer width="100%" height={200}>
                <AreaChart data={queryTrend} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
                  <defs>
                    <linearGradient id="queryGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#2563eb" stopOpacity={0.15} />
                      <stop offset="100%" stopColor="#2563eb" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" vertical={false} />
                  <XAxis dataKey="day" tick={{ fontSize: 11, fill: 'var(--color-muted)' }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fontSize: 11, fill: 'var(--color-muted)' }} axisLine={false} tickLine={false} />
                  <Tooltip content={<CustomTooltip />} />
                  <Area
                    type="monotone"
                    dataKey="queries"
                    name="Rows"
                    stroke="#2563eb"
                    strokeWidth={2}
                    fill="url(#queryGrad)"
                    dot={{ r: 3, fill: '#2563eb', strokeWidth: 2, stroke: '#fff' }}
                    activeDot={{ r: 5, fill: '#2563eb', strokeWidth: 2, stroke: '#fff' }}
                  />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </div>
        </Card>

        <Card padding="none">
          <div className="px-5 py-4 border-b border-border">
            <div className="flex items-center gap-2">
              <Zap className="w-4 h-4 text-warning" />
              <h3 className="text-sm font-semibold text-foreground">Warehouses</h3>
            </div>
          </div>
          <div className="p-5">
            {loading ? (
              <div className="space-y-3">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="h-10 bg-surface rounded-lg animate-pulse" />
                ))}
              </div>
            ) : dashboardData && dashboardData.warehouses.length > 0 ? (
              <div className="space-y-3">
                {dashboardData.warehouses.map((wh) => (
                  <div key={wh.name} className="flex items-center justify-between p-3 bg-surface rounded-xl">
                    <div className="flex items-center gap-3">
                      <Zap className="w-4 h-4 text-warning" />
                      <div>
                        <span className="text-sm font-semibold text-foreground">{wh.name}</span>
                        <div className="flex items-center gap-1.5 mt-0.5">
                          <span className="text-[11px] text-muted">{wh.size || '—'}</span>
                          <span className="text-[11px] text-muted-foreground">·</span>
                          <span className="text-[11px] text-muted">{wh.running} active</span>
                        </div>
                      </div>
                    </div>
                    <StatusBadge
                      status={wh.state === 'RUNNING' ? 'active' : wh.state === 'SUSPENDED' ? 'expired' : 'pending'}
                      label={wh.state}
                    />
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-sm text-muted">
                No warehouse data available
              </div>
            )}
          </div>
        </Card>
      </div>

      {/* Activity + DB Overview */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card className="lg:col-span-2" padding="none">
          <div className="px-5 py-4 border-b border-border flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4 text-primary" />
              <h3 className="text-sm font-semibold text-foreground">Recent Queries</h3>
            </div>
            <button
              onClick={() => navigate(ROUTES.MONITORING)}
              className="text-xs text-primary hover:text-primary-hover font-medium flex items-center gap-1 transition-colors"
            >
              View all
              <ArrowUpRight className="w-3 h-3" />
            </button>
          </div>
          <div className="divide-y divide-border">
            {loading ? (
              Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="px-5 py-3">
                  <div className="flex items-center gap-3">
                    <Skeleton variant="rectangular" width={32} height={32} className="rounded-lg" />
                    <div className="flex-1 space-y-1.5">
                      <Skeleton variant="text" width="60%" height={14} />
                      <Skeleton variant="text" width="40%" height={12} />
                    </div>
                  </div>
                </div>
              ))
            ) : recentActivity.length > 0 ? (
              recentActivity.map((item, i) => (
                <motion.div
                  key={item.id}
                  initial={{ opacity: 0, x: -12 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.04, duration: 0.3 }}
                  className="flex items-center gap-3 px-5 py-3 hover:bg-surface/50 transition-colors"
                >
                  <div className={cn('w-8 h-8 rounded-lg flex items-center justify-center shrink-0', actionColors[item.type] || actionColors.query)}>
                    <Activity className="w-3.5 h-3.5" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-foreground">
                      <span className="font-semibold">{item.user}</span>{' '}
                      <span className="text-muted">{item.action}</span>
                    </p>
                    <p className="text-[11px] text-muted-foreground font-mono truncate max-w-xs">{item.target}</p>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <StatusBadge status={item.status as any} />
                    <span className="text-[11px] text-muted-foreground tabular-nums">{item.time}</span>
                  </div>
                </motion.div>
              ))
            ) : (
              <div className="px-5 py-12 text-center text-sm text-muted">
                No recent queries. Run a query in the workspace to see activity here.
              </div>
            )}
          </div>
        </Card>

        <Card padding="none">
          <div className="px-5 py-4 border-b border-border">
            <div className="flex items-center gap-2">
              <Database className="w-4 h-4 text-primary" />
              <h3 className="text-sm font-semibold text-foreground">Databases</h3>
            </div>
          </div>
          <div className="divide-y divide-border max-h-[300px] overflow-y-auto">
            {loading ? (
              Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="px-5 py-3">
                  <Skeleton variant="text" width="70%" height={14} />
                </div>
              ))
            ) : dashboardData && dashboardData.databases.length > 0 ? (
              dashboardData.databases.slice(0, 10).map((db, i) => (
                <motion.div
                  key={db}
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.04 }}
                  className="flex items-center gap-3 px-5 py-3 hover:bg-surface/50 transition-colors"
                >
                  <div className="w-8 h-8 rounded-lg bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center">
                    <Database className="w-3.5 h-3.5 text-blue-500" />
                  </div>
                  <span className="text-sm font-medium text-foreground font-mono">{db}</span>
                </motion.div>
              ))
            ) : (
              <div className="px-5 py-12 text-center text-sm text-muted">
                No databases found
              </div>
            )}
          </div>
        </Card>
      </div>

      {/* Quick Actions */}
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }}>
        <Card>
          <h3 className="text-sm font-semibold text-foreground mb-4">Quick Actions</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {[
              { label: 'Create Skill', desc: 'Add a new AI skill', icon: Puzzle, color: 'blue', route: ROUTES.SKILLS },
              { label: 'Manage Models', desc: 'Configure AI access', icon: Brain, color: 'purple', route: ROUTES.MODELS },
              { label: 'View Monitoring', desc: 'Audit logs & metrics', icon: Activity, color: 'amber', route: ROUTES.MONITORING },
              { label: 'Open Workspace', desc: 'SQL chat & explorer', icon: Database, color: 'emerald', route: ROUTES.WORKSPACE },
            ].map((action, i) => {
              const Icon = action.icon;
              const colorClasses: Record<string, { bg: string; hover: string; icon: string }> = {
                blue: { bg: 'bg-blue-100 dark:bg-blue-900/30', hover: 'hover:bg-blue-200 dark:hover:bg-blue-800/30', icon: 'text-blue-500' },
                purple: { bg: 'bg-purple-100 dark:bg-purple-900/30', hover: 'hover:bg-purple-200 dark:hover:bg-purple-800/30', icon: 'text-purple-500' },
                amber: { bg: 'bg-amber-100 dark:bg-amber-900/30', hover: 'hover:bg-amber-200 dark:hover:bg-amber-800/30', icon: 'text-amber-500' },
                emerald: { bg: 'bg-emerald-100 dark:bg-emerald-900/30', hover: 'hover:bg-emerald-200 dark:hover:bg-emerald-800/30', icon: 'text-emerald-500' },
              };
              const c = colorClasses[action.color];
              return (
                <motion.button
                  key={action.label}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.4 + i * 0.05 }}
                  onClick={() => navigate(action.route)}
                  className={cn(
                    'flex items-center gap-3 p-4 rounded-xl border border-transparent transition-all duration-200 group/action',
                    c.bg, c.hover,
                  )}
                >
                  <div className={cn('w-10 h-10 rounded-xl flex items-center justify-center shrink-0 transition-transform group-hover/action:scale-110', c.bg)}>
                    <Icon className={cn('w-5 h-5', c.icon)} />
                  </div>
                  <div className="text-left flex-1">
                    <div className="text-sm font-semibold text-foreground">{action.label}</div>
                    <div className="text-[11px] text-muted">{action.desc}</div>
                  </div>
                  <ArrowUpRight className="w-4 h-4 text-muted opacity-0 group-hover/action:opacity-100 transition-opacity" />
                </motion.button>
              );
            })}
          </div>
        </Card>
      </motion.div>
    </div>
  );
}

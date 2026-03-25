import { useState, useEffect } from 'react';
import { motion } from 'motion/react';
import { BarChart3, TrendingUp, Users, Zap, Brain, ArrowUpRight, ArrowDownRight, AlertTriangle } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line, PieChart, Pie, Cell } from 'recharts';
import { Card, CardHeader, Badge, Skeleton, EmptyState } from '../components/ui';
import { cn } from '../lib/cn';

const USAGE_DATA = [
  { name: 'Mon', uses: 45, errors: 2 },
  { name: 'Tue', uses: 62, errors: 1 },
  { name: 'Wed', uses: 78, errors: 3 },
  { name: 'Thu', uses: 55, errors: 0 },
  { name: 'Fri', uses: 91, errors: 1 },
  { name: 'Sat', uses: 34, errors: 0 },
  { name: 'Sun', uses: 28, errors: 1 },
];

const SKILL_RANKING = [
  { name: 'Data Explorer', uses: 2103, trend: '+18%', color: '#2563eb' },
  { name: 'SQL Optimizer', uses: 1247, trend: '+12%', color: '#10b981' },
  { name: 'Analytics Engineer', uses: 923, trend: '+5%', color: '#f59e0b' },
  { name: 'Data Architect', uses: 892, trend: '+3%', color: '#8b5cf6' },
  { name: 'ETL Pipeline', uses: 567, trend: '-2%', color: '#0ea5e9' },
  { name: 'ML Engineer', uses: 634, trend: '+8%', color: '#f97316' },
];

const USER_ACTIVITY = [
  { name: 'Sarah Chen', queries: 234, skills: 12, trend: '+15%' },
  { name: 'Mike Johnson', queries: 189, skills: 8, trend: '+8%' },
  { name: 'Emily Davis', queries: 156, skills: 5, trend: '+3%' },
  { name: 'Alex Rivera', queries: 98, skills: 2, trend: '-1%' },
  { name: 'Jordan Lee', queries: 87, skills: 7, trend: '+12%' },
];

const CATEGORY_DATA = [
  { name: 'SQL', value: 35, color: '#2563eb' },
  { name: 'Analytics', value: 25, color: '#10b981' },
  { name: 'ML', value: 15, color: '#8b5cf6' },
  { name: 'Discovery', value: 15, color: '#0ea5e9' },
  { name: 'Security', value: 10, color: '#f59e0b' },
];

const ERROR_RATE_DATA = [
  { name: 'SQL Optimizer', rate: 0.5, color: '#10b981' },
  { name: 'Data Explorer', rate: 1.2, color: '#10b981' },
  { name: 'Analytics Engineer', rate: 2.8, color: '#f59e0b' },
  { name: 'ML Engineer', rate: 4.1, color: '#f97316' },
  { name: 'Data Quality', rate: 8.3, color: '#ef4444' },
];

export function AnalyticsPage() {
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => setLoading(false), 500);
    return () => clearTimeout(timer);
  }, []);

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton variant="text" width={180} height={28} />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} variant="rectangular" height={100} className="rounded-xl" />)}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Skeleton variant="rectangular" height={300} className="rounded-xl" />
          <Skeleton variant="rectangular" height={300} className="rounded-xl" />
        </div>
      </div>
    );
  }

  const totalUses = USAGE_DATA.reduce((a, d) => a + d.uses, 0);
  const totalErrors = USAGE_DATA.reduce((a, d) => a + d.errors, 0);
  const avgDaily = Math.round(totalUses / 7);
  const errorRate = ((totalErrors / totalUses) * 100).toFixed(1);

  return (
    <div className="space-y-6 animate-fade-in-up">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Analytics</h1>
        <p className="text-sm text-muted mt-1">Insights into skill usage and performance</p>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {[
          { label: 'Total Uses (Week)', value: totalUses.toLocaleString(), change: '+12% vs last week', trend: 'up' as const, icon: <Zap className="w-5 h-5" />, color: 'text-primary' },
          { label: 'Avg Daily Uses', value: avgDaily, change: 'Steady', trend: 'up' as const, icon: <TrendingUp className="w-5 h-5" />, color: 'text-success' },
          { label: 'Error Rate', value: `${errorRate}%`, change: '-0.3% improvement', trend: 'up' as const, icon: <AlertTriangle className="w-5 h-5" />, color: 'text-warning' },
          { label: 'Active Skills', value: '10/12', change: '83% utilization', trend: 'up' as const, icon: <Brain className="w-5 h-5" />, color: 'text-accent' },
        ].map((stat) => (
          <Card key={stat.label} padding="sm" hover>
            <div className="flex items-start justify-between">
              <div>
                <p className="text-xs text-muted font-medium">{stat.label}</p>
                <p className="text-2xl font-bold text-foreground mt-1">{stat.value}</p>
                <div className="flex items-center gap-1 mt-1">
                  {stat.trend === 'up' ? <ArrowUpRight className="w-3 h-3 text-success" /> : <ArrowDownRight className="w-3 h-3 text-error" />}
                  <span className="text-xs text-muted">{stat.change}</span>
                </div>
              </div>
              <div className={cn('p-2 rounded-lg bg-surface', stat.color)}>{stat.icon}</div>
            </div>
          </Card>
        ))}
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Usage Trend */}
        <Card>
          <CardHeader title="Usage Trend" subtitle="Daily skill usage over the past week" />
          <div className="h-[250px] mt-2">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={USAGE_DATA}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" vertical={false} />
                <XAxis dataKey="name" tick={{ fontSize: 11, fill: 'var(--color-muted)' }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 11, fill: 'var(--color-muted)' }} axisLine={false} tickLine={false} />
                <Tooltip
                  content={({ active, payload }) => {
                    if (!active || !payload?.length) return null;
                    return (
                      <div className="bg-surface-elevated border border-border rounded-lg shadow-lg px-3 py-2 text-xs">
                        <p className="font-semibold text-foreground">{payload[0].payload.name}</p>
                        <p className="text-muted">{payload[0].name}: <span className="font-mono text-foreground">{payload[0].value}</span></p>
                      </div>
                    );
                  }}
                />
                <Bar dataKey="uses" fill="var(--color-primary)" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>

        {/* Category Distribution */}
        <Card>
          <CardHeader title="Category Distribution" subtitle="Skills by category" />
          <div className="h-[250px] mt-2 flex items-center justify-center">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={CATEGORY_DATA}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={90}
                  paddingAngle={4}
                  dataKey="value"
                >
                  {CATEGORY_DATA.map((entry, i) => (
                    <Cell key={i} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip
                  content={({ active, payload }) => {
                    if (!active || !payload?.length) return null;
                    return (
                      <div className="bg-surface-elevated border border-border rounded-lg shadow-lg px-3 py-2 text-xs">
                        <p className="font-semibold text-foreground">{payload[0].name}</p>
                        <p className="text-muted">{payload[0].value}% of skills</p>
                      </div>
                    );
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="flex flex-wrap justify-center gap-3 mt-2">
            {CATEGORY_DATA.map((cat) => (
              <div key={cat.name} className="flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full" style={{ background: cat.color }} />
                <span className="text-xs text-muted">{cat.name} ({cat.value}%)</span>
              </div>
            ))}
          </div>
        </Card>

        {/* Skill Ranking */}
        <Card>
          <CardHeader title="Skill Ranking" subtitle="Most used skills this month" />
          <div className="space-y-3 mt-2">
            {SKILL_RANKING.map((skill, i) => (
              <div key={skill.name} className="flex items-center gap-3">
                <span className="text-xs font-mono text-muted w-5">{i + 1}</span>
                <div className="flex-1">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium text-foreground">{skill.name}</span>
                    <Badge variant={skill.trend.startsWith('+') ? 'success' : 'error'} size="sm">{skill.trend}</Badge>
                  </div>
                  <div className="h-2 bg-surface rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all duration-500"
                      style={{ width: `${(skill.uses / SKILL_RANKING[0].uses) * 100}%`, background: skill.color }}
                    />
                  </div>
                </div>
                <span className="text-xs text-muted w-16 text-right">{skill.uses.toLocaleString()}</span>
              </div>
            ))}
          </div>
        </Card>

        {/* Error Rate */}
        <Card>
          <CardHeader title="Error Rate by Skill" subtitle="Percentage of failed executions" />
          <div className="space-y-3 mt-2">
            {ERROR_RATE_DATA.map((skill) => (
              <div key={skill.name} className="flex items-center gap-3">
                <div className="flex-1">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium text-foreground">{skill.name}</span>
                    <span className="text-xs font-mono" style={{ color: skill.color }}>{skill.rate}%</span>
                  </div>
                  <div className="h-2 bg-surface rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all duration-500"
                      style={{ width: `${Math.min(skill.rate * 10, 100)}%`, background: skill.color }}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* Most Active Users */}
      <Card>
        <CardHeader title="Most Active Users" subtitle="Top users by query volume" />
        <div className="divide-y divide-border mt-2">
          {USER_ACTIVITY.map((user, i) => (
            <motion.div
              key={user.name}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.05 }}
              className="flex items-center justify-between py-3"
            >
              <div className="flex items-center gap-3">
                <span className="text-xs font-mono text-muted w-5">{i + 1}</span>
                <div>
                  <p className="text-sm font-medium text-foreground">{user.name}</p>
                  <p className="text-xs text-muted">{user.queries} queries · {user.skills} skills</p>
                </div>
              </div>
              <Badge variant={user.trend.startsWith('+') ? 'success' : 'error'} size="sm">{user.trend}</Badge>
            </motion.div>
          ))}
        </div>
      </Card>
    </div>
  );
}


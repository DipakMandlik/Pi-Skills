import React from 'react';
import { useStore } from '../store';
import { motion, AnimatePresence } from 'motion/react';
import { X, Activity, Cpu, Database, Bot, Clock } from 'lucide-react';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';

const mockLoadData = [
  { time: '00:00', load: 45 },
  { time: '04:00', load: 30 },
  { time: '08:00', load: 65 },
  { time: '12:00', load: 85 },
  { time: '16:00', load: 70 },
  { time: '20:00', load: 55 },
  { time: '24:00', load: 50 },
];

function StatCard({ title, value, trend, icon: Icon, trendUp }: any) {
  return (
    <div className="bg-panel border border-border rounded-xl p-4 shadow-sm">
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm font-medium text-text-muted">{title}</span>
        <Icon className="w-5 h-5 text-accent/70" />
      </div>
      <div className="flex items-end justify-between">
        <span className="text-2xl font-semibold text-text-main">{value}</span>
        <span className={`text-xs font-medium px-2 py-1 rounded ${trendUp ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'}`}>
          {trend}
        </span>
      </div>
    </div>
  );
}

export function SystemMonitorModal() {
  const { isMonitorOpen, setIsMonitorOpen } = useStore();

  if (!isMonitorOpen) return null;

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6">
        <motion.div 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={() => setIsMonitorOpen(false)}
          className="absolute inset-0 bg-black/40 backdrop-blur-sm"
        />
        
        <motion.div 
          initial={{ opacity: 0, scale: 0.95, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 20 }}
          className="relative w-full max-w-4xl max-h-[90vh] bg-bg-base rounded-2xl shadow-2xl border border-border flex flex-col overflow-hidden"
        >
          <div className="flex items-center justify-between p-5 border-b border-border bg-panel shrink-0">
            <div>
              <h2 className="text-xl font-display font-semibold text-text-main flex items-center gap-2">
                <Activity className="w-6 h-6 text-accent" />
                System Monitoring
              </h2>
              <p className="text-sm text-text-muted mt-1">Real-time warehouse performance and agent activity</p>
            </div>
            <button 
              onClick={() => setIsMonitorOpen(false)}
              className="p-2 text-text-muted hover:text-text-main hover:bg-slate-100 rounded-lg transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
          
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <StatCard title="Compute Load" value="78%" trend="+5%" icon={Cpu} trendUp={true} />
              <StatCard title="Active Queries" value="12" trend="-2" icon={Database} trendUp={false} />
              <StatCard title="Agent Tasks" value="45" trend="+12" icon={Bot} trendUp={true} />
              <StatCard title="Avg Latency" value="1.2s" trend="-0.1s" icon={Clock} trendUp={false} />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2 bg-panel border border-border rounded-xl p-5 shadow-sm">
                <div className="flex items-center justify-between mb-6">
                  <h3 className="text-base font-medium text-text-main">Compute Load (24h)</h3>
                  <span className="text-xs font-medium bg-accent/10 text-accent px-2.5 py-1 rounded-full flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse" />
                    Live
                  </span>
                </div>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={mockLoadData} margin={{ top: 5, right: 0, left: -20, bottom: 0 }}>
                      <defs>
                        <linearGradient id="colorLoad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#2563eb" stopOpacity={0.3}/>
                          <stop offset="95%" stopColor="#2563eb" stopOpacity={0}/>
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                      <XAxis dataKey="time" fontSize={12} stroke="#64748b" tickMargin={10} />
                      <YAxis fontSize={12} stroke="#64748b" tickFormatter={(val) => `${val}%`} />
                      <Tooltip 
                        contentStyle={{ backgroundColor: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '8px', fontSize: '13px' }}
                      />
                      <Area type="monotone" dataKey="load" stroke="#2563eb" strokeWidth={2} fillOpacity={1} fill="url(#colorLoad)" />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div className="bg-panel border border-border rounded-xl p-5 shadow-sm flex flex-col">
                <h3 className="text-base font-medium text-text-main mb-4">Recent Agent Activity</h3>
                <div className="space-y-4 flex-1 overflow-y-auto pr-2">
                  {[
                    { agent: 'Query Optimizer', action: 'Rewrote complex join', time: '2m ago', status: 'success' },
                    { agent: 'Data Explorer', action: 'Scanned new schema', time: '15m ago', status: 'success' },
                    { agent: 'Warehouse Monitor', action: 'Scaled up COMPUTE_WH', time: '1h ago', status: 'warning' },
                    { agent: 'SQL Writer', action: 'Generated revenue report', time: '2h ago', status: 'success' },
                    { agent: 'Metadata Inspector', action: 'Updated column stats', time: '3h ago', status: 'success' },
                    { agent: 'Query Optimizer', action: 'Failed to optimize query', time: '4h ago', status: 'error' },
                  ].map((log, i) => (
                    <div key={i} className="flex items-start gap-3 text-sm">
                      <div className={`w-2 h-2 rounded-full mt-1.5 shrink-0 ${
                        log.status === 'success' ? 'bg-green-500' : 
                        log.status === 'warning' ? 'bg-amber-500' : 'bg-red-500'
                      }`} />
                      <div>
                        <p className="text-text-main font-medium text-sm">{log.agent}</p>
                        <p className="text-text-muted text-xs mt-0.5">{log.action}</p>
                      </div>
                      <span className="ml-auto text-xs text-text-muted whitespace-nowrap">{log.time}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}

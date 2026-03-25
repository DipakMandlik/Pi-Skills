import React, { useState } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { motion } from 'motion/react';
import { User, Lock, Eye, EyeOff, ArrowRight, AlertCircle, Database, Shield, Building2, ChevronDown } from 'lucide-react';
import { useAuth } from '../auth';
import { ROUTES } from '../constants/routes';
import { Button } from '../components/common';

function FloatingDot({ delay, x, y, size, color }: { delay: number; x: number; y: number; size: number; color: string }) {
  return (
    <motion.div
      className="absolute rounded-full"
      style={{ width: size, height: size, background: color, left: `${x}%`, top: `${y}%`, filter: `blur(${size > 3 ? 1 : 0}px)` }}
      initial={{ opacity: 0, scale: 0 }}
      animate={{ opacity: [0, 0.6, 0.3, 0.6, 0], scale: [0.5, 1, 0.8, 1.2, 0.5], y: [0, -30, -10, -40, 0] }}
      transition={{ duration: 6 + Math.random() * 4, delay, repeat: Infinity, ease: 'easeInOut' }}
    />
  );
}

function BrandPanel() {
  const dots = Array.from({ length: 20 }, (_, i) => ({
    id: i, delay: Math.random() * 3, x: Math.random() * 100, y: Math.random() * 100,
    size: 2 + Math.random() * 4,
    color: ['#60a5fa', '#38bdf8', '#818cf8', '#a78bfa', '#06b6d4'][Math.floor(Math.random() * 5)],
  }));

  return (
    <div className="hidden lg:flex lg:w-[500px] xl:w-[560px] flex-col justify-between p-10 relative overflow-hidden"
      style={{ background: 'linear-gradient(145deg, #0f172a 0%, #1e293b 50%, #0f172a 100%)' }}>
      <div className="absolute inset-0 opacity-[0.03]" style={{
        backgroundImage: 'linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)',
        backgroundSize: '24px 24px',
      }} />
      <div className="absolute top-0 left-0 w-[500px] h-[500px] rounded-full opacity-15 blur-3xl" style={{ background: 'radial-gradient(circle, #2563eb 0%, transparent 70%)' }} />
      <div className="absolute bottom-0 right-0 w-[400px] h-[400px] rounded-full opacity-10 blur-3xl" style={{ background: 'radial-gradient(circle, #06b6d4 0%, transparent 70%)' }} />
      {dots.map(({ id, ...dot }) => <FloatingDot key={id} {...dot} />)}

      <div className="relative z-10">
        <div className="flex items-center gap-2.5">
          <motion.span initial={{ opacity: 0, scale: 0.8 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.6 }}
            className="text-5xl font-bold italic leading-none"
            style={{ background: 'linear-gradient(135deg, #60a5fa 0%, #38bdf8 50%, #818cf8 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
            π
          </motion.span>
          <motion.div initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.2 }} className="ml-1">
            <div className="text-xl font-semibold text-white leading-none">π-Optimized</div>
            <div className="text-[11px] text-slate-400 mt-1">Data Engineering Platform</div>
          </motion.div>
        </div>
      </div>

      <motion.div initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3, duration: 0.6 }}
        className="relative z-10 max-w-sm">
        <h1 className="text-[32px] font-extrabold text-white leading-tight mb-5">
          Intelligent data workflows,{' '}
          <span style={{ background: 'linear-gradient(135deg, #60a5fa, #a78bfa)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>optimized</span>{' '}
          for your team.
        </h1>
        <p className="text-sm text-slate-400 leading-relaxed">
          Role-aware skills management, model governance, and real-time monitoring — all unified in one platform built for data teams.
        </p>
      </motion.div>

      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.5 }}
        className="relative z-10 flex flex-wrap gap-2">
        {['AI Skills', 'Model Governance', 'RBAC', 'Real-time Monitoring'].map((pill, i) => (
          <motion.span key={pill} initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.6 + i * 0.08 }}
            className="text-[11px] font-medium text-slate-300 bg-white/5 border border-white/10 px-3 py-1.5 rounded-full backdrop-blur-sm">
            {pill}
          </motion.span>
        ))}
      </motion.div>

      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.7 }} className="relative z-10">
        <div className="bg-white/5 backdrop-blur-sm border border-white/10 rounded-xl p-4">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-blue-500/20 flex items-center justify-center">
              <Database className="w-4 h-4 text-blue-400" />
            </div>
            <div className="flex-1">
              <p className="text-xs font-semibold text-slate-200">Snowflake Native Auth</p>
              <p className="text-[11px] text-slate-400 mt-0.5">Your credentials authenticate directly against Snowflake</p>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-40" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-400" />
              </span>
              <span className="text-[11px] text-emerald-400 font-medium">Secure</span>
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  );
}

function InputField({
  label, icon: Icon, value, onChange, onFocus, onBlur, focused, placeholder, type = 'text', showToggle, onToggle,
}: {
  label: string; icon: React.ElementType; value: string; onChange: (v: string) => void;
  onFocus: () => void; onBlur: () => void; focused: boolean; placeholder: string;
  type?: string; showToggle?: boolean; onToggle?: () => void;
}) {
  return (
    <div>
      <label className="block text-xs font-semibold text-[var(--color-text-muted)] uppercase tracking-wider mb-1.5">{label}</label>
      <div className={`relative rounded-xl border transition-all ${focused ? 'border-[var(--color-accent)] ring-2 ring-[var(--color-accent)]/10 bg-white' : 'border-[var(--color-border)] bg-[var(--color-surface)]'}`}>
        <Icon className={`absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 transition-colors ${focused ? 'text-[var(--color-accent)]' : 'text-[var(--color-text-light)]'}`} />
        <input
          type={type}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onFocus={onFocus}
          onBlur={onBlur}
          placeholder={placeholder}
          className="w-full pl-9 pr-3 py-2.5 bg-transparent rounded-xl text-sm text-[var(--color-text-main)] placeholder:text-[var(--color-text-light)] focus:outline-none"
        />
        {showToggle && onToggle && (
          <button type="button" onClick={onToggle} className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--color-text-light)] hover:text-[var(--color-text-muted)] transition-colors">
            {type === 'password' ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
          </button>
        )}
      </div>
    </div>
  );
}

const SNOWFLAKE_ROLES = ['ACCOUNTADMIN', 'SYSADMIN', 'SECURITYADMIN', 'PUBLIC', 'CUSTOM'];
const DEFAULT_SNOWFLAKE_ROLE = SNOWFLAKE_ROLES[0];

export function LoginPage() {
  const { isAuthenticated, isLoading, error, login, loginDemo, clearError } = useAuth();
  const location = useLocation();
  const from = (location.state as { from?: { pathname: string } })?.from?.pathname || ROUTES.DASHBOARD;

  const [account, setAccount] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState(DEFAULT_SNOWFLAKE_ROLE);
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);
  const [focused, setFocused] = useState<Record<string, boolean>>({});
  const [showRoleDropdown, setShowRoleDropdown] = useState(false);

  if (isAuthenticated) return <Navigate to={from} replace />;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLocalError(null);
    clearError();
    if (!account.trim()) { setLocalError('Account identifier is required'); return; }
    if (!username.trim()) { setLocalError('Username is required'); return; }
    if (!password) { setLocalError('Password is required'); return; }
    const effectiveRole = role.trim().toUpperCase() || DEFAULT_SNOWFLAKE_ROLE;
    if (!role.trim()) {
      // Ensure the UI reflects the role sent to backend even when field was left empty.
      setRole(DEFAULT_SNOWFLAKE_ROLE);
    }
    setSubmitting(true);
    try {
      await login({
        account: account.trim(),
        username: username.trim(),
        password,
        role: effectiveRole,
      });
    }
    catch { /* error set in auth context */ }
    finally { setSubmitting(false); }
  };

  const displayError = localError || error;

  return (
    <div className="h-screen w-screen flex bg-[var(--color-bg-base)]">
      <BrandPanel />

      <div className="flex-1 flex items-center justify-center p-6">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }} className="w-full max-w-[420px]">

          <div className="lg:hidden flex items-center gap-2.5 mb-10">
            <span className="text-4xl font-bold italic leading-none"
              style={{ background: 'linear-gradient(135deg, #2563eb, #06b6d4)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>π</span>
            <div>
              <div className="text-lg font-semibold text-[var(--color-text-main)]">π-Optimized</div>
              <div className="text-[10px] text-[var(--color-text-muted)]">Data Engineering Platform</div>
            </div>
          </div>

          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.2 }}>
            <h2 className="text-2xl font-extrabold text-[var(--color-text-main)] mb-1">Connect to Snowflake</h2>
            <p className="text-sm text-[var(--color-text-muted)]">Enter your Snowflake credentials to access your data</p>
          </motion.div>

          {displayError && (
            <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }}
              className="flex items-center gap-2 px-3 py-2.5 bg-red-50 border border-red-200 rounded-xl mt-5">
              <AlertCircle className="w-4 h-4 text-red-500 shrink-0" />
              <span className="text-sm text-red-700">{displayError}</span>
            </motion.div>
          )}

          <form onSubmit={handleSubmit} className="space-y-3.5 mt-6">
            {/* Account Identifier */}
            <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
              <InputField
                label="Account Identifier"
                icon={Building2}
                value={account}
                onChange={(v) => { setAccount(v); setLocalError(null); clearError(); }}
                onFocus={() => setFocused({ ...focused, account: true })}
                onBlur={() => setFocused({ ...focused, account: false })}
                focused={!!focused.account}
                placeholder="xy12345.us-east-1"
              />
            </motion.div>

            {/* Username */}
            <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.25 }}>
              <InputField
                label="Username"
                icon={User}
                value={username}
                onChange={(v) => { setUsername(v); setLocalError(null); clearError(); }}
                onFocus={() => setFocused({ ...focused, username: true })}
                onBlur={() => setFocused({ ...focused, username: false })}
                focused={!!focused.username}
                placeholder="PIQLENS"
              />
            </motion.div>

            {/* Password */}
            <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
              <InputField
                label="Password"
                icon={Lock}
                value={password}
                onChange={(v) => { setPassword(v); setLocalError(null); clearError(); }}
                onFocus={() => setFocused({ ...focused, password: true })}
                onBlur={() => setFocused({ ...focused, password: false })}
                focused={!!focused.password}
                placeholder="Enter your password"
                type={showPassword ? 'text' : 'password'}
                showToggle
                onToggle={() => setShowPassword(!showPassword)}
              />
            </motion.div>

            {/* Role */}
            <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.35 }}>
              <label className="block text-xs font-semibold text-[var(--color-text-muted)] uppercase tracking-wider mb-1.5">Role</label>
              <div className="relative">
                <div className={`relative rounded-xl border transition-all ${focused.role ? 'border-[var(--color-accent)] ring-2 ring-[var(--color-accent)]/10 bg-white' : 'border-[var(--color-border)] bg-[var(--color-surface)]'}`}>
                  <Shield className={`absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 transition-colors ${focused.role ? 'text-[var(--color-accent)]' : 'text-[var(--color-text-light)]'}`} />
                  <input
                    type="text"
                    value={role}
                    onChange={(e) => { setRole(e.target.value.toUpperCase()); setLocalError(null); clearError(); }}
                    onFocus={() => setFocused({ ...focused, role: true })}
                    onBlur={() => { setFocused({ ...focused, role: false }); setTimeout(() => setShowRoleDropdown(false), 150); }}
                    placeholder="Select role"
                    className="w-full pl-9 pr-10 py-2.5 bg-transparent rounded-xl text-sm text-[var(--color-text-main)] placeholder:text-[var(--color-text-light)] focus:outline-none uppercase font-mono"
                  />
                  <button type="button" onClick={() => setShowRoleDropdown(!showRoleDropdown)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--color-text-light)] hover:text-[var(--color-text-muted)] transition-colors">
                    <ChevronDown className="w-4 h-4" />
                  </button>
                </div>
                {showRoleDropdown && (
                  <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-[var(--color-border)] rounded-xl shadow-lg z-10 overflow-hidden">
                    {SNOWFLAKE_ROLES.map((r) => (
                      <button key={r} type="button"
                        onMouseDown={(e) => { e.preventDefault(); setRole(r); setShowRoleDropdown(false); }}
                        className="w-full px-3 py-2 text-left text-sm font-mono hover:bg-[var(--color-surface)] transition-colors text-[var(--color-text-main)]">
                        {r}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </motion.div>

            {/* Submit */}
            <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }} className="pt-2">
              <Button type="submit" loading={submitting || isLoading} className="w-full" size="lg"
                iconRight={<ArrowRight className="w-4 h-4" />}>
                Connect to Snowflake
              </Button>
            </motion.div>

            <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.45 }} className="pt-1">
              <div className="relative">
                <div className="absolute inset-0 flex items-center"><div className="w-full border-t border-[var(--color-border)]" /></div>
                <div className="relative flex justify-center text-xs"><span className="px-2 bg-[var(--color-bg-base)] text-[var(--color-text-muted)]">or</span></div>
              </div>
              <Button variant="secondary" className="w-full mt-3" size="lg"
                onClick={loginDemo}>
                Try Demo Mode
              </Button>
            </motion.div>
          </form>

          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.5 }}
            className="mt-6 flex items-center justify-center gap-4 text-[11px] text-[var(--color-text-light)]">
            <div className="flex items-center gap-1.5">
              <Shield className="w-3 h-3" />
              <span>Role-based access</span>
            </div>
            <span>·</span>
            <div className="flex items-center gap-1.5">
              <Lock className="w-3 h-3" />
              <span>Credentials never stored</span>
            </div>
          </motion.div>
        </motion.div>
      </div>
    </div>
  );
}

import { useState, useEffect } from 'react';
import { motion } from 'motion/react';
import { Building2, Key, Bell, Palette, Sun, Moon, Monitor, Globe, Save, Shield, Database, Webhook } from 'lucide-react';
import { Button, Card, CardHeader, Tabs, Input, Select, Skeleton, useToast, Badge } from '../components/ui';
import { cn } from '../lib/cn';

type ThemeMode = 'light' | 'dark' | 'system';

export function SettingsPage() {
  const { toast } = useToast();
  const [activeTab, setActiveTab] = useState('general');
  const [loading, setLoading] = useState(true);
  const [orgName, setOrgName] = useState('π-Optimized');
  const [orgDomain, setOrgDomain] = useState('pi-optimized.com');
  const [notifications, setNotifications] = useState({
    email: true,
    skillCreated: true,
    skillAssigned: true,
    skillEdited: false,
    userJoined: true,
    errors: true,
  });
  const [theme, setTheme] = useState<ThemeMode>(() => {
    return (localStorage.getItem('theme') as ThemeMode) || 'system';
  });

  useEffect(() => {
    const timer = setTimeout(() => setLoading(false), 300);
    return () => clearTimeout(timer);
  }, []);

  const handleSave = () => {
    toast('success', 'Settings saved successfully');
  };

  const handleThemeChange = (newTheme: ThemeMode) => {
    setTheme(newTheme);
    localStorage.setItem('theme', newTheme);
    const root = document.documentElement;
    if (newTheme === 'dark') root.classList.add('dark');
    else if (newTheme === 'light') root.classList.remove('dark');
    else {
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      root.classList.toggle('dark', prefersDark);
    }
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton variant="text" width={120} height={28} />
        <Skeleton variant="rectangular" height={200} className="rounded-xl" />
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in-up max-w-3xl">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Settings</h1>
        <p className="text-sm text-muted mt-1">Manage your organization preferences</p>
      </div>

      <Tabs
        tabs={[
          { key: 'general', label: 'General', icon: <Building2 className="w-4 h-4" /> },
          { key: 'notifications', label: 'Notifications', icon: <Bell className="w-4 h-4" /> },
          { key: 'appearance', label: 'Appearance', icon: <Palette className="w-4 h-4" /> },
          { key: 'integrations', label: 'Integrations', icon: <Webhook className="w-4 h-4" /> },
        ]}
        activeKey={activeTab}
        onChange={setActiveTab}
      />

      {activeTab === 'general' && (
        <Card>
          <CardHeader title="Organization Profile" subtitle="Basic information about your organization" />
          <div className="space-y-4 mt-4">
            <Input
              label="Organization Name"
              value={orgName}
              onChange={(e) => setOrgName(e.target.value)}
            />
            <Input
              label="Domain"
              value={orgDomain}
              onChange={(e) => setOrgDomain(e.target.value)}
              hint="Your organization's primary domain"
            />
            <Select
              label="Default Region"
              options={[
                { value: 'us-east-1', label: 'US East (N. Virginia)' },
                { value: 'us-west-2', label: 'US West (Oregon)' },
                { value: 'eu-west-1', label: 'EU (Ireland)' },
                { value: 'ap-southeast-1', label: 'Asia Pacific (Singapore)' },
              ]}
              placeholder="Select region"
              defaultValue="us-east-1"
            />
            <div className="flex justify-end pt-2">
              <Button icon={<Save className="w-4 h-4" />} onClick={handleSave}>Save Changes</Button>
            </div>
          </div>
        </Card>
      )}

      {activeTab === 'notifications' && (
        <Card>
          <CardHeader title="Notification Preferences" subtitle="Choose what notifications you receive" />
          <div className="space-y-4 mt-4">
            {Object.entries({
              email: 'Email Notifications',
              skillCreated: 'Skill Created',
              skillAssigned: 'Skill Assigned to Me',
              skillEdited: 'Skill Modified',
              userJoined: 'New User Joined',
              errors: 'Error Alerts',
            }).map(([key, label]) => (
              <div key={key} className="flex items-center justify-between py-2">
                <div>
                  <p className="text-sm font-medium text-foreground">{label}</p>
                </div>
                <button
                  onClick={() => setNotifications((prev) => ({ ...prev, [key]: !prev[key as keyof typeof prev] }))}
                  className={cn(
                    'relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200',
                    notifications[key as keyof typeof notifications] ? 'bg-primary' : 'bg-surface',
                  )}
                  role="switch"
                  aria-checked={notifications[key as keyof typeof notifications]}
                  aria-label={label}
                >
                  <span
                    className={cn(
                      'pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200',
                      notifications[key as keyof typeof notifications] ? 'translate-x-5' : 'translate-x-0',
                    )}
                  />
                </button>
              </div>
            ))}
            <div className="flex justify-end pt-2">
              <Button icon={<Save className="w-4 h-4" />} onClick={handleSave}>Save Preferences</Button>
            </div>
          </div>
        </Card>
      )}

      {activeTab === 'appearance' && (
        <Card>
          <CardHeader title="Appearance" subtitle="Customize the look and feel" />
          <div className="space-y-6 mt-4">
            <div>
              <label className="text-sm font-medium text-foreground mb-3 block">Theme</label>
              <div className="grid grid-cols-3 gap-3">
                {([
                  { value: 'light' as const, label: 'Light', icon: <Sun className="w-5 h-5" /> },
                  { value: 'dark' as const, label: 'Dark', icon: <Moon className="w-5 h-5" /> },
                  { value: 'system' as const, label: 'System', icon: <Monitor className="w-5 h-5" /> },
                ]).map((t) => (
                  <button
                    key={t.value}
                    onClick={() => handleThemeChange(t.value)}
                    className={cn(
                      'flex flex-col items-center gap-2 p-4 rounded-xl border transition-colors',
                      theme === t.value
                        ? 'border-primary bg-primary-lighter text-primary'
                        : 'border-border bg-surface text-muted hover:border-border-hover',
                    )}
                  >
                    {t.icon}
                    <span className="text-sm font-medium">{t.label}</span>
                  </button>
                ))}
              </div>
            </div>
            <div>
              <label className="text-sm font-medium text-foreground mb-3 block">Language</label>
              <Select
                options={[
                  { value: 'en', label: 'English' },
                  { value: 'es', label: 'Spanish' },
                  { value: 'fr', label: 'French' },
                  { value: 'de', label: 'German' },
                ]}
                defaultValue="en"
              />
            </div>
          </div>
        </Card>
      )}

      {activeTab === 'integrations' && (
        <div className="space-y-4">
          <Card>
            <CardHeader title="API Keys" subtitle="Manage your API keys for external integrations" />
            <div className="mt-4 space-y-3">
              <div className="flex items-center justify-between p-3 rounded-lg border border-border bg-surface">
                <div className="flex items-center gap-3">
                  <Key className="w-4 h-4 text-muted" />
                  <div>
                    <p className="text-sm font-medium text-foreground">Production Key</p>
                    <p className="text-xs text-muted font-mono">sk-••••••••••••••••••••</p>
                  </div>
                </div>
                <Badge variant="success" size="sm">Active</Badge>
              </div>
              <div className="flex items-center justify-between p-3 rounded-lg border border-border bg-surface">
                <div className="flex items-center gap-3">
                  <Key className="w-4 h-4 text-muted" />
                  <div>
                    <p className="text-sm font-medium text-foreground">Development Key</p>
                    <p className="text-xs text-muted font-mono">sk-••••••••••••••••••••</p>
                  </div>
                </div>
                <Badge variant="secondary" size="sm">Revoked</Badge>
              </div>
              <Button variant="secondary" size="sm" icon={<Key className="w-4 h-4" />}>Generate New Key</Button>
            </div>
          </Card>

          <Card>
            <CardHeader title="Connected Services" subtitle="External services and databases" />
            <div className="mt-4 space-y-3">
              {[
                { name: 'Snowflake', icon: <Database className="w-4 h-4" />, status: 'Connected', color: 'text-success' },
                { name: 'Google AI', icon: <Globe className="w-4 h-4" />, status: 'Connected', color: 'text-success' },
                { name: 'Slack', icon: <Bell className="w-4 h-4" />, status: 'Not Connected', color: 'text-muted' },
              ].map((service) => (
                <div key={service.name} className="flex items-center justify-between p-3 rounded-lg border border-border bg-surface">
                  <div className="flex items-center gap-3">
                    <div className={cn('p-2 rounded-lg bg-surface-elevated', service.color)}>{service.icon}</div>
                    <div>
                      <p className="text-sm font-medium text-foreground">{service.name}</p>
                      <p className={cn('text-xs', service.color)}>{service.status}</p>
                    </div>
                  </div>
                  <Button size="sm" variant={service.status === 'Connected' ? 'secondary' : 'primary'}>
                    {service.status === 'Connected' ? 'Configure' : 'Connect'}
                  </Button>
                </div>
              ))}
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}


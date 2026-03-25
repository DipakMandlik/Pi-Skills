import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Bell,
  Search,
  Sun,
  Moon,
  Monitor as MonitorIcon,
  LogOut,
  User,
  Settings,
  ChevronDown,
  Command,
} from 'lucide-react';
import { cn } from '../../lib/cn';
import { Avatar, Dropdown, DropdownItem, DropdownSeparator, DropdownLabel } from '../ui';
import { useAuth } from '../../auth';

interface TopbarProps {
  onCommandOpen: () => void;
  sidebarCollapsed: boolean;
}

type ThemeMode = 'light' | 'dark' | 'system';

export function Topbar({ onCommandOpen, sidebarCollapsed }: TopbarProps) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const [notifOpen, setNotifOpen] = useState(false);
  const [theme, setTheme] = useState<ThemeMode>(() => {
    const stored = localStorage.getItem('theme') as ThemeMode | null;
    return stored || 'system';
  });

  useEffect(() => {
    localStorage.setItem('theme', theme);
    const root = document.documentElement;
    if (theme === 'dark') {
      root.classList.add('dark');
    } else if (theme === 'light') {
      root.classList.remove('dark');
    } else {
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      root.classList.toggle('dark', prefersDark);
    }
  }, [theme]);

  const cycleTheme = () => {
    setTheme((prev) => (prev === 'light' ? 'dark' : prev === 'dark' ? 'system' : 'light'));
  };

  const themeIcon = theme === 'light' ? <Sun className="w-4 h-4" /> : theme === 'dark' ? <Moon className="w-4 h-4" /> : <MonitorIcon className="w-4 h-4" />;

  const notifications = [
    { id: '1', title: 'Skill published', body: 'SQL Optimizer v2.1 is now live', time: '2m ago', unread: true },
    { id: '2', title: 'New team member', body: 'Sarah joined the Data team', time: '1h ago', unread: true },
    { id: '3', title: 'Deployment complete', body: 'Production deploy succeeded', time: '3h ago', unread: false },
  ];

  const unreadCount = notifications.filter((n) => n.unread).length;

  return (
    <header
      className={cn(
        'sticky top-0 z-sticky flex h-14 items-center justify-between border-b border-border bg-surface-elevated/80 px-4 backdrop-blur-xl',
        sidebarCollapsed ? 'ml-[60px]' : 'ml-[240px]',
        'transition-all duration-300',
      )}
      role="banner"
    >
      {/* Left: Search trigger */}
      <div className="flex items-center gap-3">
        <button
          onClick={onCommandOpen}
          className="flex items-center gap-2 rounded-lg border border-border bg-surface px-3 py-1.5 text-sm text-muted hover:text-foreground hover:border-border-hover transition-colors"
          aria-label="Open command palette"
        >
          <Search className="w-4 h-4" />
          <span className="hidden sm:inline">Search...</span>
          <kbd className="hidden sm:inline-flex items-center gap-0.5 text-[10px] font-mono text-muted">
            <Command className="w-3 h-3" />K
          </kbd>
        </button>
      </div>

      {/* Right: Actions */}
      <div className="flex items-center gap-1">
        {/* Theme toggle */}
        <button
          onClick={cycleTheme}
          className="p-2 rounded-lg text-muted hover:text-foreground hover:bg-surface transition-colors"
          aria-label={`Current theme: ${theme}. Click to change.`}
          title={`Theme: ${theme}`}
        >
          {themeIcon}
        </button>

        {/* Notifications */}
        <Dropdown
          trigger={
            <button
              className="relative p-2 rounded-lg text-muted hover:text-foreground hover:bg-surface transition-colors"
              aria-label={`Notifications${unreadCount > 0 ? `, ${unreadCount} unread` : ''}`}
            >
              <Bell className="w-5 h-5" />
              {unreadCount > 0 && (
                <span className="absolute top-1 right-1 h-2 w-2 rounded-full bg-error" />
              )}
            </button>
          }
          open={notifOpen}
          onOpenChange={setNotifOpen}
          align="end"
        >
          <DropdownLabel>Notifications</DropdownLabel>
          {notifications.map((n) => (
            <div key={n.id} className="px-3 py-2.5 hover:bg-surface rounded-md cursor-pointer">
              <div className="flex items-center gap-2">
                {n.unread && <span className="h-1.5 w-1.5 rounded-full bg-primary shrink-0" />}
                <div className="min-w-0">
                  <p className="text-sm font-medium text-foreground truncate">{n.title}</p>
                  <p className="text-xs text-muted truncate">{n.body}</p>
                  <p className="text-[10px] text-muted mt-0.5">{n.time}</p>
                </div>
              </div>
            </div>
          ))}
          <DropdownSeparator />
          <DropdownItem onClick={() => { setNotifOpen(false); }}>View all notifications</DropdownItem>
        </Dropdown>

        {/* User menu */}
        <Dropdown
          trigger={
            <button className="flex items-center gap-2 rounded-lg p-1.5 hover:bg-surface transition-colors">
              <Avatar
                initials={user?.name?.split(' ').map(n => n[0]).join('') || 'U'}
                alt={user?.name || 'User'}
                size="sm"
              />
              <ChevronDown className="w-3.5 h-3.5 text-muted hidden sm:block" />
            </button>
          }
          open={userMenuOpen}
          onOpenChange={setUserMenuOpen}
          align="end"
        >
          <div className="px-3 py-2.5">
            <p className="text-sm font-medium text-foreground">{user?.name || 'User'}</p>
            <p className="text-xs text-muted">{user?.email || 'user@example.com'}</p>
          </div>
          <DropdownSeparator />
          <DropdownItem icon={<User className="w-4 h-4" />} onClick={() => navigate('/settings')}>
            Profile
          </DropdownItem>
          <DropdownItem icon={<Settings className="w-4 h-4" />} onClick={() => navigate('/settings')}>
            Settings
          </DropdownItem>
          <DropdownSeparator />
          <DropdownItem icon={<LogOut className="w-4 h-4" />} destructive onClick={() => { logout(); navigate('/login'); }}>
            Sign out
          </DropdownItem>
        </Dropdown>
      </div>
    </header>
  );
}

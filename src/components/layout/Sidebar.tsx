import { useState, useCallback, type ReactNode } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'motion/react';
import {
  LayoutDashboard,
  Brain,
  Users,
  UserCog,
  BarChart3,
  Settings,
  Shield,
  Layers,
  ChevronLeft,
  ChevronRight,
  PanelLeftClose,
  PanelLeft,
  Monitor,
} from 'lucide-react';
import { cn } from '../../lib/cn';
import { ROUTES, type RoutePath } from '../../constants/routes';

interface NavItem {
  path: RoutePath;
  label: string;
  icon: ReactNode;
  permission?: string;
  section?: string;
}

const NAV_ITEMS: NavItem[] = [
  { path: ROUTES.DASHBOARD, label: 'Dashboard', icon: <LayoutDashboard className="w-5 h-5" />, section: 'Overview' },
  { path: ROUTES.SKILLS, label: 'Skill Library', icon: <Brain className="w-5 h-5" />, section: 'Platform' },
  { path: ROUTES.WORKSPACE, label: 'Workspace', icon: <Layers className="w-5 h-5" />, section: 'Platform' },
  { path: ROUTES.MODELS, label: 'Models', icon: <Monitor className="w-5 h-5" />, section: 'Platform' },
  { path: ROUTES.USERS, label: 'Users', icon: <Users className="w-5 h-5" />, section: 'Organization' },
  { path: ROUTES.TEAMS, label: 'Teams', icon: <UserCog className="w-5 h-5" />, section: 'Organization' },
  { path: ROUTES.ANALYTICS, label: 'Analytics', icon: <BarChart3 className="w-5 h-5" />, section: 'Insights' },
  { path: ROUTES.MONITORING, label: 'Monitoring', icon: <Shield className="w-5 h-5" />, section: 'Insights' },
  { path: ROUTES.GOVERNANCE, label: 'Governance', icon: <Shield className="w-5 h-5" />, section: 'Admin' },
  { path: ROUTES.SETTINGS, label: 'Settings', icon: <Settings className="w-5 h-5" />, section: 'Admin' },
];

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
}

export function Sidebar({ collapsed, onToggle }: SidebarProps) {
  const location = useLocation();
  const navigate = useNavigate();
  const [tooltip, setTooltip] = useState<string | null>(null);

  const handleNavigate = useCallback((path: RoutePath) => {
    navigate(path);
  }, [navigate]);

  const groupedItems = NAV_ITEMS.reduce<Record<string, NavItem[]>>((acc, item) => {
    const section = item.section || 'General';
    if (!acc[section]) acc[section] = [];
    acc[section].push(item);
    return acc;
  }, {});

  return (
    <aside
      className={cn(
        'flex flex-col border-r border-border bg-surface-elevated transition-all duration-300 ease-in-out',
        collapsed ? 'w-[60px]' : 'w-[240px]',
        'h-full',
      )}
      role="navigation"
      aria-label="Main navigation"
    >
      {/* Logo */}
      <div className={cn(
        'flex items-center h-14 px-4 border-b border-border',
        collapsed ? 'justify-center' : 'justify-between',
      )}>
        {!collapsed && (
          <div className="flex items-center gap-2">
            <div className="h-7 w-7 rounded-lg bg-primary flex items-center justify-center">
              <span className="text-primary-foreground font-bold text-sm">π</span>
            </div>
            <span className="font-semibold text-foreground text-sm">π-Optimized</span>
          </div>
        )}
        {collapsed && (
          <div className="h-7 w-7 rounded-lg bg-primary flex items-center justify-center">
            <span className="text-primary-foreground font-bold text-sm">π</span>
          </div>
        )}
        <button
          onClick={onToggle}
          className="p-1.5 rounded-md text-muted hover:text-foreground hover:bg-surface transition-colors"
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {collapsed ? <PanelLeft className="w-4 h-4" /> : <PanelLeftClose className="w-4 h-4" />}
        </button>
      </div>

      {/* Nav Items */}
      <nav className="flex-1 overflow-y-auto py-3 px-2">
        {Object.entries(groupedItems).map(([section, items]) => (
          <div key={section} className="mb-4 last:mb-0">
            {!collapsed && (
              <div className="px-2 mb-1.5 text-[10px] font-semibold text-muted uppercase tracking-wider">
                {section}
              </div>
            )}
            {items.map((item) => {
              const isActive = location.pathname === item.path ||
                (item.path !== ROUTES.DASHBOARD && location.pathname.startsWith(item.path));
              return (
                <div
                  key={item.path}
                  className="relative"
                  onMouseEnter={() => collapsed && setTooltip(item.label)}
                  onMouseLeave={() => setTooltip(null)}
                >
                  <button
                    onClick={() => handleNavigate(item.path)}
                    className={cn(
                      'flex w-full items-center gap-3 rounded-lg text-sm font-medium transition-colors',
                      collapsed ? 'justify-center py-2.5 px-2' : 'py-2 px-3',
                      isActive
                        ? 'bg-primary-lighter text-primary'
                        : 'text-muted hover:text-foreground hover:bg-surface',
                    )}
                    aria-current={isActive ? 'page' : undefined}
                  >
                    <span className="shrink-0">{item.icon}</span>
                    {!collapsed && <span className="truncate">{item.label}</span>}
                  </button>
                  {collapsed && tooltip === item.label && (
                    <div className="absolute left-full ml-2 top-1/2 -translate-y-1/2 z-tooltip">
                      <div className="bg-foreground text-background text-xs font-medium px-2.5 py-1.5 rounded-md whitespace-nowrap shadow-lg">
                        {item.label}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        ))}
      </nav>

      {/* Collapse indicator */}
      {collapsed && (
        <div className="px-2 pb-3">
          <button
            onClick={onToggle}
            className="flex w-full items-center justify-center py-2 rounded-lg text-muted hover:text-foreground hover:bg-surface transition-colors"
            aria-label="Expand sidebar"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      )}
    </aside>
  );
}

import { useState, useEffect, useCallback } from 'react';
import { Outlet, useNavigate } from 'react-router-dom';
import { Sidebar } from '../components/layout/Sidebar';
import { Topbar } from '../components/layout/Topbar';
import { Breadcrumbs } from '../components/layout/Breadcrumbs';
import { CommandPalette } from '../components/ui/CommandPalette';
import { Brain, Users, BarChart3, Settings, Shield, Layers, Monitor, LayoutDashboard, Plus, UserCog } from 'lucide-react';
import { ROUTES } from '../constants/routes';

function useSidebarState() {
  const [collapsed, setCollapsed] = useState(() => {
    const stored = localStorage.getItem('sidebar-collapsed');
    return stored === 'true';
  });

  const toggle = useCallback(() => {
    setCollapsed((prev) => {
      const next = !prev;
      localStorage.setItem('sidebar-collapsed', String(next));
      return next;
    });
  }, []);

  return { collapsed, toggle };
}

export function AppLayout() {
  const { collapsed, toggle } = useSidebarState();
  const [commandOpen, setCommandOpen] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'k' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setCommandOpen((prev) => !prev);
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, []);

  const commandItems = [
    { id: 'dashboard', label: 'Go to Dashboard', icon: <LayoutDashboard className="w-4 h-4" />, section: 'Navigation', action: () => navigate(ROUTES.DASHBOARD) },
    { id: 'skills', label: 'Skill Library', icon: <Brain className="w-4 h-4" />, section: 'Navigation', action: () => navigate(ROUTES.SKILLS) },
    { id: 'workspace', label: 'Workspace', icon: <Layers className="w-4 h-4" />, section: 'Navigation', action: () => navigate(ROUTES.WORKSPACE) },
    { id: 'models', label: 'Models', icon: <Monitor className="w-4 h-4" />, section: 'Navigation', action: () => navigate(ROUTES.MODELS) },
    { id: 'users', label: 'User Management', icon: <Users className="w-4 h-4" />, section: 'Organization', action: () => navigate(ROUTES.USERS) },
    { id: 'teams', label: 'Team Management', icon: <UserCog className="w-4 h-4" />, section: 'Organization', action: () => navigate(ROUTES.TEAMS) },
    { id: 'analytics', label: 'Analytics', icon: <BarChart3 className="w-4 h-4" />, section: 'Insights', action: () => navigate(ROUTES.ANALYTICS) },
    { id: 'monitoring', label: 'Monitoring', icon: <Shield className="w-4 h-4" />, section: 'Insights', action: () => navigate(ROUTES.MONITORING) },
    { id: 'governance', label: 'Governance', icon: <Shield className="w-4 h-4" />, section: 'Admin', action: () => navigate(ROUTES.GOVERNANCE) },
    { id: 'settings', label: 'Settings', icon: <Settings className="w-4 h-4" />, section: 'Admin', action: () => navigate(ROUTES.SETTINGS) },
    { id: 'create-skill', label: 'Create New Skill', icon: <Plus className="w-4 h-4" />, shortcut: 'N', section: 'Actions', action: () => navigate(ROUTES.SKILL_STUDIO_NEW) },
  ];

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <Sidebar collapsed={collapsed} onToggle={toggle} />
      <div className="flex flex-col flex-1 min-w-0">
        <Topbar onCommandOpen={() => setCommandOpen(true)} sidebarCollapsed={collapsed} />
        <div className="flex-1 overflow-y-auto">
          <div className="px-6 py-4">
            <Breadcrumbs />
          </div>
          <main className="px-6 pb-6">
            <Outlet />
          </main>
        </div>
      </div>
      <CommandPalette isOpen={commandOpen} onClose={() => setCommandOpen(false)} items={commandItems} />
    </div>
  );
}

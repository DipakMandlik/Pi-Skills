import { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { AnimatePresence, motion } from 'motion/react';
import { AuthProvider } from './auth';
import { ProtectedRoute } from './auth';
import { ToastProvider } from './components/ui/Toast';
import { AppLayout } from './layouts/AppLayout';
import { GuestLayout } from './layouts/GuestLayout';
import { LoginPage } from './pages/LoginPage';
import { UnauthorizedPage } from './pages/UnauthorizedPage';
import { ROUTES } from './constants/routes';
import { PageSkeleton } from './components/ui/Skeleton';
import { ErrorBoundary } from './components/common/ErrorBoundary';

const LazyPage = ({ importFn }: { importFn: () => Promise<{ default?: React.ComponentType<unknown>; [key: string]: unknown }> }) => {
  const Component = lazy(() => importFn().then((mod) => ({ default: (mod.default || mod[Object.keys(mod)[0]]) as React.ComponentType<unknown> })));
  return <Component />;
};

function SuspenseWrapper({ children }: { children: React.ReactNode }) {
  return (
    <Suspense fallback={<PageSkeleton />}>
      {children}
    </Suspense>
  );
}

function AnimatedRoutes() {
  const location = useLocation();

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={location.pathname}
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -4 }}
        transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
        className="h-full"
      >
        <Routes location={location}>
          <Route element={<GuestLayout />}>
            <Route path={ROUTES.LOGIN} element={<LoginPage />} />
          </Route>

          <Route
            element={
              <ProtectedRoute>
                <AppLayout />
              </ProtectedRoute>
            }
          >
            <Route index element={<Navigate to={ROUTES.DASHBOARD} replace />} />
            <Route path={ROUTES.DASHBOARD} element={<SuspenseWrapper><LazyPage importFn={() => import('./pages/DashboardPage')} /></SuspenseWrapper>} />
            <Route path={ROUTES.WORKSPACE} element={<SuspenseWrapper><LazyPage importFn={() => import('./pages/WorkspacePage')} /></SuspenseWrapper>} />
            <Route
              path={ROUTES.SKILLS}
              element={
                <SuspenseWrapper>
                  <ProtectedRoute requiredPermission="viewAllSkills">
                    <LazyPage importFn={() => import('./pages/SkillsPage')} />
                  </ProtectedRoute>
                </SuspenseWrapper>
              }
            />
            <Route path={ROUTES.SKILL_DETAIL} element={<SuspenseWrapper><LazyPage importFn={() => import('./pages/SkillDetailPage')} /></SuspenseWrapper>} />
            <Route path={ROUTES.SKILL_STUDIO} element={<SuspenseWrapper><LazyPage importFn={() => import('./pages/SkillStudioPage')} /></SuspenseWrapper>} />
            <Route path={ROUTES.SKILL_STUDIO_NEW} element={<SuspenseWrapper><LazyPage importFn={() => import('./pages/SkillStudioPage')} /></SuspenseWrapper>} />
            <Route
              path={ROUTES.MODELS}
              element={
                <SuspenseWrapper>
                  <ProtectedRoute requiredPermission="viewAllModels">
                    <LazyPage importFn={() => import('./pages/ModelsPage')} />
                  </ProtectedRoute>
                </SuspenseWrapper>
              }
            />
            <Route path={ROUTES.MONITORING} element={<SuspenseWrapper><LazyPage importFn={() => import('./pages/MonitoringPage')} /></SuspenseWrapper>} />
            <Route
              path={ROUTES.GOVERNANCE}
              element={
                <SuspenseWrapper>
                  <ProtectedRoute requiredPermission="manageModels">
                    <LazyPage importFn={() => import('./pages/GovernanceAdminPage')} />
                  </ProtectedRoute>
                </SuspenseWrapper>
              }
            />
            <Route path={ROUTES.USERS} element={<SuspenseWrapper><LazyPage importFn={() => import('./pages/UsersPage')} /></SuspenseWrapper>} />
            <Route path={ROUTES.TEAMS} element={<SuspenseWrapper><LazyPage importFn={() => import('./pages/TeamsPage')} /></SuspenseWrapper>} />
            <Route path={ROUTES.ANALYTICS} element={<SuspenseWrapper><LazyPage importFn={() => import('./pages/AnalyticsPage')} /></SuspenseWrapper>} />
            <Route path={ROUTES.SETTINGS} element={<SuspenseWrapper><LazyPage importFn={() => import('./pages/SettingsPage')} /></SuspenseWrapper>} />
          </Route>

          <Route path={ROUTES.UNAUTHORIZED} element={<UnauthorizedPage />} />
          <Route path="*" element={<Navigate to={ROUTES.DASHBOARD} replace />} />
        </Routes>
      </motion.div>
    </AnimatePresence>
  );
}

export default function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <ToastProvider>
          <AuthProvider>
            <AnimatedRoutes />
          </AuthProvider>
        </ToastProvider>
      </BrowserRouter>
    </ErrorBoundary>
  );
}

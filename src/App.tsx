import { LeftPanel } from './components/LeftPanel';
import { CenterPanel } from './components/CenterPanel';
import { RightPanel } from './components/RightPanel';
import { SystemMonitorModal } from './components/SystemMonitorModal';

export default function App() {
  return (
    <div className="flex h-screen w-screen overflow-hidden bg-bg-base text-text-main font-sans selection:bg-accent/20 selection:text-accent">
      <LeftPanel />
      <CenterPanel />
      <RightPanel />
      <SystemMonitorModal />
    </div>
  );
}

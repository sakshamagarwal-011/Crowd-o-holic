import { useSimulation } from '@/state/SimulationContext';
import { AlertTriangle, X, ArrowRight, RefreshCw } from 'lucide-react';

export function EmergencyBanner() {
  const { snapshot, clearEm } = useSimulation();
  const em = snapshot?.emergency;
  if (!em?.active) return null;

  return (
    <div className="cmd-pulse-red flex items-center gap-3 px-4 h-10 flex-shrink-0 overflow-hidden"
      style={{ background: 'rgba(255,23,68,0.12)', borderBottom: '1px solid rgba(224,77,69,0.4)' }}>
      <AlertTriangle size={18} color="#e04d45" className="cmd-pulse flex-shrink-0" />
      <div className="flex items-center gap-2 text-[12px]">
        <span className="font-bold" style={{ color: '#e04d45' }}>EMERGENCY ACTIVE</span>
        <span style={{ color: 'var(--cmd-text-dim)' }}>·</span>
        <span className="font-semibold text-white">{em.type.toUpperCase()} at {em.location}</span>
      </div>
      <div className="flex items-center gap-2 ml-3 text-[10px]" style={{ color: 'var(--cmd-text-dim)' }}>
        <Step label="Event" done />
        <ArrowRight size={10} />
        <Step label="Routes Disabled" done />
        <ArrowRight size={10} />
        <Step label="Recalculating" done />
        <ArrowRight size={10} />
        <Step label="Redistribution" active />
      </div>
      <button onClick={clearEm}
        className="ml-auto flex items-center gap-1.5 px-2.5 py-1 rounded text-[10px] font-semibold hover:opacity-90"
        style={{ background: 'rgba(34,197,94,0.15)', border: '1px solid rgba(143,166,111,0.30)', color: '#8fa66f' }}>
        <X size={11} />
        <span>CLEAR</span>
      </button>
    </div>
  );
}

function Step({ label, done, active }: { label: string; done?: boolean; active?: boolean }) {
  return (
    <span className="flex items-center gap-1">
      {done && <RefreshCw size={9} color="#8fa66f" />}
      <span style={{ color: done ? '#8fa66f' : active ? '#e04d45' : 'var(--cmd-text-faint)' }}
        className={active ? 'cmd-pulse' : ''}>
        {label}
      </span>
    </span>
  );
}

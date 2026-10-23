import { useSimulation } from '@/state/SimulationContext';
import { riskColor } from '@/utils/display';
import { AlertTriangle, X } from 'lucide-react';

export function AlertPanel() {
  const { snapshot, ackAlert } = useSimulation();
  const alerts = snapshot?.safety.alerts ?? [];

  if (alerts.length === 0) return null;

  return (
    <div className="cmd-panel rounded overflow-hidden"
      style={{ borderColor: alerts[0]?.severity === 'emergency' ? 'rgba(224,77,69,0.4)' : 'var(--cmd-border)' }}>
      <div className="flex items-center gap-2 px-3 py-1.5 border-b border-[var(--cmd-border)]">
        <AlertTriangle size={13} color="#d7a24a" className="cmd-pulse" />
        <span className="cmd-label">Active Alerts</span>
        <span className="ml-auto text-[10px] font-bold" style={{ color: '#d7a24a' }}>{alerts.length}</span>
      </div>
      <div className="max-h-[160px] overflow-y-auto">
        {alerts.map((a) => {
          const color = riskColor(a.severity);
          return (
            <div key={a.id} className="px-3 py-2 border-b border-[var(--cmd-border)] flex items-start gap-2"
              style={{ background: a.severity === 'emergency' ? 'rgba(224,77,69,0.05)' : 'transparent' }}>
              <AlertTriangle size={12} style={{ color }} className="mt-0.5 flex-shrink-0" />
              <div className="flex-1 min-w-0">
                <div className="text-[11px] font-semibold text-white">{a.title}</div>
                <div className="text-[10px] leading-snug" style={{ color: 'var(--cmd-text-dim)' }}>{a.message}</div>
              </div>
              <button onClick={() => ackAlert(a.id)}
                className="flex-shrink-0 hover:text-white transition-colors" style={{ color: 'var(--cmd-text-faint)' }}>
                <X size={12} />
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}

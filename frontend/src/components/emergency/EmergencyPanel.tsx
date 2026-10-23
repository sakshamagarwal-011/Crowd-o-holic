import { useSimulation } from '@/state/SimulationContext';
import { NODE_MAP } from '@/data/venue';
import { AlertTriangle, X, Zap } from 'lucide-react';
import type { EmergencyEvent } from '@/types';

const EMERGENCY_TYPES: { type: EmergencyEvent['type']; label: string }[] = [
  { type: 'fire', label: 'Fire' },
  { type: 'medical', label: 'Medical' },
  { type: 'structural', label: 'Structural' },
  { type: 'security', label: 'Security' },
  { type: 'crowd-crush', label: 'Crowd crush' },
  { type: 'gate-failure', label: 'Gate failure' },
];

const EMERGENCY_NODES = ['j-n', 'j-e', 'j-w', 'j-s', 'food-n', 'gate-e', 'stage'];

export function EmergencyPanel() {
  const { snapshot, triggerEm, clearEm } = useSimulation();
  const em = snapshot?.emergency;
  const isEm = em?.active === true;

  return (
    <div className="cmd-panel rounded-lg overflow-hidden"
      style={{ borderColor: isEm ? 'rgba(224,77,69,0.45)' : 'var(--cmd-border)' }}>
      <div className="panel-header">
        <div className="flex items-center gap-2">
          <Zap size={14} color={isEm ? '#e04d45' : '#d7a24a'} />
          <span className="cmd-label">Emergency controls</span>
        </div>
        <span className={`status-badge ${isEm ? 'status-badge--critical' : 'status-badge--neutral'}`}>
          {isEm ? 'ACTIVE' : 'SIMULATION'}
        </span>
      </div>

      {isEm ? (
        <div className="p-3 space-y-2">
          <div className="critical-card cmd-pulse-red">
            <div className="flex items-center gap-1.5 mb-1">
              <AlertTriangle size={13} color="#e04d45" />
              <span className="text-[12px] font-bold text-white">{em!.type.toUpperCase()} · {em!.location}</span>
            </div>
            <div className="text-[10px]" style={{ color: 'var(--cmd-text-dim)' }}>{em!.summary}</div>
            <div className="text-[10px] mt-1.5" style={{ color: 'var(--cmd-text-faint)' }}>
              {em!.closedEdgeIds.length} route segment(s) disabled · rerouting active
            </div>
          </div>
          <button onClick={clearEm}
            className="w-full flex items-center justify-center gap-1.5 px-3 py-1.5 rounded text-[11px] font-semibold transition-all hover:opacity-90"
            style={{ background: 'rgba(143,166,111,0.12)', border: '1px solid rgba(143,166,111,0.30)', color: '#8fa66f' }}>
            <X size={12} /> CLEAR EMERGENCY
          </button>
        </div>
      ) : (
        <div className="p-3 space-y-2">
          <div className="text-[10px]" style={{ color: 'var(--cmd-text-dim)' }}>
            Simulation-only triggers. Select an incident to arm it at a venue node.
          </div>
          <div className="grid grid-cols-3 gap-1.5">
            {EMERGENCY_TYPES.map((t) => (
              <button key={t.type}
                onClick={() => triggerEm(t.type, EMERGENCY_NODES[Math.floor(Math.random() * EMERGENCY_NODES.length)])}
                className="emergency-chip"
                aria-label={`Simulate ${t.label} emergency`}>
                <span>{t.label}</span>
              </button>
            ))}
          </div>
          <div className="text-[9px] pt-1" style={{ color: 'var(--cmd-text-faint)' }}>
            Target pool: {EMERGENCY_NODES.map((id) => NODE_MAP[id]?.label).slice(0, 3).join(', ')}…
          </div>
        </div>
      )}
    </div>
  );
}

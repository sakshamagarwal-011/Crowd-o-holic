import { useSimulation } from '@/state/SimulationContext';
import { STADIUM_A } from '@/data/venue';
import { riskColor, riskLabel, connectionColor, connectionLabel, formatSimClock } from '@/utils/display';
import { ShieldAlert, Radio, Activity, Clock, AlertTriangle, Wifi } from 'lucide-react';

export function Header() {
  const { snapshot, connection, scenario } = useSimulation();
  const sim = snapshot?.simulation;
  const safety = snapshot?.safety;
  const emergency = snapshot?.emergency;

  const status = sim?.status ?? 'idle';
  const simClock = sim
    ? formatSimClock(scenario.timing.startMinutesOfDay + sim.simTimeMin)
    : '--:--';
  const riskLevel = safety?.riskLevel ?? 'low';
  const riskScore = safety?.riskScore ?? 0;
  const isEm = emergency?.active === true;

  const statusLabel = status === 'running' ? 'RUNNING'
    : status === 'paused' ? 'PAUSED'
    : status === 'completed' ? 'COMPLETED'
    : status === 'error' ? 'ERROR'
    : 'STANDBY';

  const statusColor = status === 'running' ? '#8fa66f'
    : status === 'paused' ? '#d7a24a'
    : status === 'completed' ? '#d39a5a'
    : status === 'error' ? '#d85b52'
    : '#89867d';

  return (
    <header className={`cmd-surface border-b flex items-center px-4 h-[60px] gap-5 flex-shrink-0 ${isEm ? 'cmd-pulse-red' : ''}`}
      style={{ borderColor: isEm ? 'rgba(224,77,69,0.5)' : 'var(--cmd-border)' }}>
      {/* brand */}
      <div className="flex items-center gap-2.5">
        <ShieldAlert size={22} style={{ color: isEm ? '#e04d45' : '#d39a5a' }} />
        <div className="leading-tight">
          <div className="text-[13px] font-bold tracking-tight text-white">
            Crowd Flow Optimiser
          </div>
          <div className="text-[9px] tracking-[0.06em]" style={{ color: 'var(--cmd-text-faint)' }}>
            Venue operations dashboard
          </div>
        </div>
      </div>

      <div className="h-8 w-px" style={{ background: 'var(--cmd-border)' }} />

      {/* venue / event */}
      <div className="flex items-center gap-5">
        <HeaderField label="Venue" value={STADIUM_A.name} />
        <HeaderField label="Event" value={scenario.name} />
      </div>

      <div className="h-8 w-px" style={{ background: 'var(--cmd-border)' }} />

      {/* sim status */}
      <div className="flex items-center gap-5">
        <div className="flex items-center gap-2">
          <Activity size={14} style={{ color: statusColor }} className={status === 'running' ? 'cmd-pulse' : ''} />
          <div className="leading-tight">
            <div className="cmd-label">Simulation</div>
            <div className="text-[12px] font-semibold" style={{ color: statusColor }}>{statusLabel}</div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Clock size={14} style={{ color: 'var(--cmd-text-dim)' }} />
          <div className="leading-tight">
            <div className="cmd-label">Sim Time</div>
            <div className="text-[12px] font-semibold cmd-mono-value">{simClock}</div>
          </div>
        </div>
      </div>

      {/* connection */}
      <div className="ml-auto flex items-center gap-5">
        <div className="flex items-center gap-2">
          {connection === 'live'
            ? <Wifi size={14} style={{ color: connectionColor(connection) }} />
            : <Radio size={14} style={{ color: connectionColor(connection) }} className="cmd-pulse" />}
          <div className="leading-tight">
            <div className="cmd-label">Connection</div>
            <div className="text-[12px] font-semibold" style={{ color: connectionColor(connection) }}>
              {connectionLabel(connection)}
            </div>
          </div>
        </div>

        <div className="h-8 w-px" style={{ background: 'var(--cmd-border)' }} />

        {/* risk */}
        <div className="flex items-center gap-2.5 px-3 py-1 rounded"
          style={{ background: riskColor(riskLevel) + '18', border: `1px solid ${riskColor(riskLevel)}40` }}>
          {isEm || riskLevel === 'critical' || riskLevel === 'high'
            ? <AlertTriangle size={16} style={{ color: riskColor(riskLevel) }} className={isEm ? 'cmd-pulse' : ''} />
            : <ShieldAlert size={16} style={{ color: riskColor(riskLevel) }} />}
          <div className="leading-tight">
            <div className="cmd-label">Risk {status === 'idle' ? '(Standby)' : ''}</div>
            <div className="text-[12px] font-bold" style={{ color: riskColor(riskLevel) }}>
              {riskLabel(riskLevel)} · {riskScore}
            </div>
          </div>
        </div>

        {/* emergency indicator */}
        {isEm && (
          <div className="flex items-center gap-2 px-3 py-1.5 rounded cmd-pulse-red"
            style={{ background: 'rgba(224,77,69,0.12)', border: '1px solid #e04d45' }}>
            <AlertTriangle size={16} color="#e04d45" className="cmd-pulse" />
            <span className="text-[12px] font-bold" style={{ color: '#e04d45' }}>
              EMERGENCY
            </span>
          </div>
        )}
      </div>
    </header>
  );
}

function HeaderField({ label, value }: { label: string; value: string }) {
  return (
    <div className="leading-tight">
      <div className="cmd-label">{label}</div>
      <div className="text-[12px] font-semibold text-white">{value}</div>
    </div>
  );
}

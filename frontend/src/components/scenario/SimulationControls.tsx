import { useSimulation } from '@/state/SimulationContext';
import { Play, Pause, RotateCcw, Gauge } from 'lucide-react';
import type { SimulationStatus } from '@/types';

const SPEEDS = [0.5, 1, 2, 5, 10];

export function SimulationControls() {
  const { snapshot, start, pause, resume, reset, setSpeedMult } = useSimulation();
  const status: SimulationStatus = snapshot?.simulation.status ?? 'idle';
  const speed = snapshot?.simulation.speedMultiplier ?? 1;

  const isRunning = status === 'running';
  const isPaused = status === 'paused';
  const isIdle = status === 'idle' || status === 'completed';

  return (
    <div className="flex items-center gap-2">
      {/* start / pause / resume */}
      {isRunning ? (
        <CtrlButton onClick={pause} icon={<Pause size={14} />} label="Pause" color="#d7a24a" />
      ) : isIdle ? (
        <CtrlButton onClick={start} icon={<Play size={14} />} label="Start" color="#8fa66f" primary />
      ) : isPaused ? (
        <CtrlButton onClick={resume} icon={<Play size={14} />} label="Resume" color="#8fa66f" primary />
      ) : (
        <CtrlButton onClick={start} icon={<Play size={14} />} label="Start" color="#8fa66f" primary />
      )}

      <CtrlButton onClick={reset} icon={<RotateCcw size={13} />} label="Reset" color="#89867d" />

      {/* speed selector */}
      <div className="flex items-center gap-1.5 ml-2">
        <Gauge size={13} style={{ color: 'var(--cmd-text-dim)' }} />
        <div className="flex gap-0.5">
          {SPEEDS.map((s) => (
            <button key={s} onClick={() => setSpeedMult(s)}
              className={`px-1.5 py-1 text-[10px] font-semibold rounded transition-colors ${
                speed === s
                  ? 'bg-[var(--cmd-border-bright)] text-white'
                  : 'text-[var(--cmd-text-dim)] hover:text-[var(--cmd-text)] hover:bg-[var(--cmd-surface-2)]'
              }`}>
              {s}×
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

function CtrlButton({ onClick, icon, label, color, primary }: {
  onClick: () => void; icon: React.ReactNode; label: string;
  color: string; primary?: boolean;
}) {
  return (
    <button onClick={onClick}
      className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded text-[11px] font-semibold transition-all ${
        primary ? 'hover:opacity-90' : 'hover:bg-[var(--cmd-surface-2)]'
      }`}
      style={primary
        ? { background: primary ? 'rgba(211,154,90,.10)' : 'transparent', border: `1px solid ${primary ? 'rgba(211,154,90,.55)' : 'var(--cmd-border)'}`, color: primary ? 'var(--live)' : color }
        : { border: '1px solid var(--cmd-border)', color }}>
      {icon}
      <span>{label}</span>
    </button>
  );
}

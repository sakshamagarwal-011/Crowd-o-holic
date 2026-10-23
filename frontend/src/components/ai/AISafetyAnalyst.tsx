import { useState } from 'react';
import { useSimulation } from '@/state/SimulationContext';
import { riskColor, riskLabel } from '@/utils/display';
import {
  Brain,
  Loader2,
  Lightbulb,
  AlertTriangle,
  ShieldCheck,
  ChevronRight,
  Zap,
  DoorOpen,
  RotateCcw,
} from 'lucide-react';

export function AISafetyAnalyst() {
  const { snapshot, intervene, activeRestrictions } = useSimulation();
  const [acting, setActing] = useState(false);
  const ai = snapshot?.ai;
  const current = ai?.analyst.current;

  if (!ai || (!current && ai.analyst.stage !== 'analyzing')) {
    return (
      <div className="cmd-panel rounded p-3 h-full flex flex-col">
        <div className="flex items-center gap-2 mb-2">
          <Brain size={14} color="#d39a5a" />
          <span className="cmd-label">AI Safety Analyst</span>
        </div>
        <div className="flex-1 flex items-center justify-center text-[11px] text-[var(--cmd-text-faint)]">
          Awaiting simulation data…
        </div>
      </div>
    );
  }

  if (ai.analyst.stage === 'analyzing' && !current) {
    return (
      <div className="cmd-panel rounded p-3 h-full flex flex-col">
        <div className="flex items-center gap-2 mb-2">
          <Brain size={14} color="#d39a5a" />
          <span className="cmd-label">AI Safety Analyst</span>
        </div>
        <div className="flex-1 flex flex-col items-center justify-center gap-2 text-[var(--live)]">
          <Loader2 size={20} className="animate-spin" />
          <span className="text-[11px]">Analyzing simulation state…</span>
        </div>
      </div>
    );
  }

  if (!current) return null;

  const color = riskColor(current.riskLevel);
  const isEm = current.riskLevel === 'emergency';
  const isWarning = current.riskLevel === 'high' || current.riskLevel === 'critical';

  const bottlenecks = snapshot?.safety.bottlenecks ?? [];
  const primaryEdge = bottlenecks[0]?.edgeId || 'e-gw-jw';

  async function handleApplyMitigation() {
    setActing(true);
    try {
      await intervene({
        action: 'divert',
        edgeId: primaryEdge,
        targetNodeId: 'exit-n',
        reason: current?.recommendedAction || 'AI Recommended Mitigation',
      });
    } finally {
      setActing(false);
    }
  }

  async function handleOpenBypass() {
    setActing(true);
    try {
      await intervene({
        action: 'open_bypass',
        targetNodeId: 'exit-n',
        reason: 'Open North Exit auxiliary bypass',
      });
    } finally {
      setActing(false);
    }
  }

  async function handleReopenAll() {
    setActing(true);
    try {
      await intervene({
        action: 'reopen',
        reason: 'Reopen all corridors',
      });
    } finally {
      setActing(false);
    }
  }

  return (
    <div className="cmd-panel rounded h-full flex flex-col overflow-hidden"
      style={{ borderColor: isEm ? 'rgba(255,23,68,0.3)' : 'var(--cmd-border)' }}>
      <div className="flex items-center gap-2 px-3 py-2 border-b border-[var(--cmd-border)]">
        <Brain size={14} color="#d39a5a" />
        <span className="cmd-label">AI Safety Analyst</span>
        <span className="ml-auto text-[9px] px-1.5 py-0.5 rounded font-bold"
          style={{ background: color + '22', color }}>
          {riskLabel(current.riskLevel).toUpperCase()}
        </span>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {/* headline */}
        <div className="flex items-start gap-2">
          {isEm || isWarning
            ? <AlertTriangle size={15} style={{ color }} className="mt-0.5 flex-shrink-0" />
            : <ShieldCheck size={15} style={{ color: '#8fa66f' }} className="mt-0.5 flex-shrink-0" />}
          <div className="text-[12px] font-semibold text-white leading-snug">
            {current.headline}
          </div>
        </div>

        {/* explanation */}
        <div className="text-[11px] leading-relaxed" style={{ color: 'var(--cmd-text-dim)' }}>
          {current.explanation}
        </div>

        {/* recommended action with direct interactive triggers */}
        <div className="rounded p-2.5" style={{ background: 'rgba(211,154,90,0.06)', border: '1px solid rgba(211,154,90,0.20)' }}>
          <div className="flex items-center gap-1.5 mb-1.5">
            <Lightbulb size={12} color="#d39a5a" />
            <span className="cmd-label text-[var(--live)]">Recommended Action</span>
          </div>
          <div className="text-[11px] leading-relaxed text-white mb-2">
            {current.recommendedAction}
          </div>

          {/* Action Trigger Buttons */}
          <div className="flex items-center gap-1.5 flex-wrap pt-1 border-t border-[rgba(211,154,90,0.15)]">
            <button
              type="button"
              disabled={acting}
              onClick={handleApplyMitigation}
              className="px-2 py-1 rounded text-[10px] font-bold bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border border-amber-500/40 flex items-center gap-1 cursor-pointer transition-colors"
            >
              <Zap size={10} />
              <span>Apply Mitigation</span>
            </button>
            <button
              type="button"
              disabled={acting}
              onClick={handleOpenBypass}
              className="px-2 py-1 rounded text-[10px] font-bold bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 border border-emerald-500/40 flex items-center gap-1 cursor-pointer transition-colors"
            >
              <DoorOpen size={10} />
              <span>Open Bypass</span>
            </button>
            {activeRestrictions.length > 0 && (
              <button
                type="button"
                disabled={acting}
                onClick={handleReopenAll}
                className="px-2 py-1 rounded text-[10px] font-semibold bg-slate-700 hover:bg-slate-600 text-slate-200 border border-slate-500 flex items-center gap-1 cursor-pointer transition-colors ml-auto"
              >
                <RotateCcw size={10} />
                <span>Reopen</span>
              </button>
            )}
          </div>
        </div>

        {/* confidence / basis */}
        <div className="flex items-center gap-2 text-[10px] pt-1" style={{ color: 'var(--cmd-text-faint)' }}>
          <span>Confidence: <span style={{ color: current.confidence === 'high' ? '#8fa66f' : current.confidence === 'medium' ? '#d7a24a' : '#89867d' }}>{current.confidence}</span></span>
          <span>·</span>
          <span className="truncate">{current.basis}</span>
        </div>
      </div>

      {/* history */}
      {ai.analyst.history.length > 1 && (
        <div className="border-t border-[var(--cmd-border)] max-h-[80px] overflow-y-auto">
          {ai.analyst.history.slice(1, 4).map((h) => (
            <div key={h.id} className="px-3 py-1.5 border-b border-[var(--cmd-border)] flex items-center gap-2">
              <ChevronRight size={11} style={{ color: riskColor(h.riskLevel) }} />
              <span className="text-[10px] truncate" style={{ color: 'var(--cmd-text-dim)' }}>{h.headline}</span>
              <span className="ml-auto text-[9px] flex-shrink-0" style={{ color: 'var(--cmd-text-faint)' }}>
                {String(Math.floor((h.atMinute + 60) / 60)).padStart(2, '0')}h
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

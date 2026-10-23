import { useState } from 'react';
import { useSimulation } from '@/state/SimulationContext';
import { riskColor, riskLabel, pct, formatCountdown } from '@/utils/display';
import { Flame, Crosshair, TrendingUp, CheckCircle2, Zap, Ban, RotateCcw } from 'lucide-react';

export function BottleneckPanel() {
  const { snapshot, selectEdge } = useSimulation();
  const bottlenecks = snapshot?.safety.bottlenecks ?? [];
  const predicted = snapshot?.safety.predictedBottlenecks ?? [];

  if (bottlenecks.length === 0 && predicted.length === 0) {
    return (
      <div className="cmd-panel rounded-lg p-3">
        <div className="flex items-center gap-2 mb-2">
          <CheckCircle2 size={14} color="#8fa66f" />
          <span className="cmd-label">Bottlenecks</span>
          <span className="status-badge status-badge--safe ml-auto">CLEAR</span>
        </div>
        <div className="empty-state empty-state--small">
          <div className="empty-state__icon"><Flame size={14} /></div>
          <div>
            <div className="empty-state__title">All corridors clear</div>
            <div className="empty-state__copy">No current or predicted capacity constraint.</div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="cmd-panel rounded-lg overflow-hidden">
      <div className="panel-header">
        <div className="flex items-center gap-2">
          <Flame size={14} color="#d7a24a" />
          <span className="cmd-label">Bottlenecks</span>
        </div>
        <span className="panel-count">{bottlenecks.length} active · {predicted.length} predicted</span>
      </div>
      <div className="max-h-[260px] overflow-y-auto">
        {bottlenecks.map((b) => (
          <BottleneckRow key={b.id} b={b} predicted={false} onClick={() => selectEdge(b.edgeId)} />
        ))}
        {predicted.map((b) => (
          <BottleneckRow key={b.id} b={b} predicted={true} onClick={() => selectEdge(b.edgeId)} />
        ))}
      </div>
    </div>
  );
}

function BottleneckRow({ b, predicted, onClick }: {
  b: import('@/types').Bottleneck; predicted: boolean; onClick: () => void;
}) {
  const { intervene, activeRestrictions } = useSimulation();
  const [loading, setLoading] = useState(false);
  const color = riskColor(b.risk);
  const isRestricted = activeRestrictions.includes(b.edgeId);

  async function handleDivert(e: React.MouseEvent) {
    e.stopPropagation();
    setLoading(true);
    try {
      await intervene({
        action: 'divert',
        edgeId: b.edgeId,
        targetNodeId: 'exit-n',
        reason: `Divert flow away from ${b.location}`,
      });
    } finally {
      setLoading(false);
    }
  }

  async function handleRestrict(e: React.MouseEvent) {
    e.stopPropagation();
    setLoading(true);
    try {
      await intervene({
        action: 'restrict',
        edgeId: b.edgeId,
        targetNodeId: 'exit-n',
        reason: `Restrict corridor ${b.edgeId}`,
      });
    } finally {
      setLoading(false);
    }
  }

  async function handleReopen(e: React.MouseEvent) {
    e.stopPropagation();
    setLoading(true);
    try {
      await intervene({
        action: 'reopen',
        reason: `Reopen ${b.location}`,
      });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div
      onClick={onClick}
      className="w-full text-left px-3 py-2.5 border-b border-[var(--cmd-border)] hover:bg-[var(--cmd-surface-2)] transition-colors flex items-start gap-2.5 cursor-pointer"
    >
      <div className="mt-0.5 flex-shrink-0">
        {predicted ? <TrendingUp size={14} color="#d7a24a" /> : <Flame size={14} style={{ color }} />}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-[12px] font-semibold text-white truncate">{b.location}</span>
          {predicted && <span className="status-badge status-badge--warning">PREDICTED</span>}
          {isRestricted && (
            <span className="text-[8px] font-bold px-1.5 py-0.5 rounded bg-rose-500/25 text-rose-300 border border-rose-500/30">
              RESTRICTED
            </span>
          )}
          <span className="ml-auto text-[8px] font-bold px-1.5 py-0.5 rounded"
            style={{ background: color + '22', color }}>
            {riskLabel(b.risk).toUpperCase()}
          </span>
        </div>
        <div className="flex items-center gap-3 text-[10px]" style={{ color: 'var(--cmd-text-dim)' }}>
          <span>Util <span className="cmd-mono-value" style={{ color }}>{pct(b.capacityUtilization)}</span></span>
          {b.timeToCriticalMin != null && (
            <span>TTC <span className="cmd-mono-value" style={{ color: b.timeToCriticalMin < 10 ? '#d85b52' : '#d7a24a' }}>{formatCountdown(b.timeToCriticalMin)}</span></span>
          )}
        </div>
        <div className="text-[10px] mt-1" style={{ color: 'var(--cmd-text-dim)' }}>{b.recommendedAction}</div>

        {/* Action Buttons to Resolve the Bottleneck Rush */}
        <div className="mt-2 flex items-center gap-1.5 flex-wrap">
          {isRestricted ? (
            <button
              type="button"
              disabled={loading}
              onClick={handleReopen}
              className="px-2 py-0.5 rounded text-[9px] font-semibold bg-slate-700 hover:bg-slate-600 text-slate-200 border border-slate-500 flex items-center gap-1 cursor-pointer transition-colors"
            >
              <RotateCcw size={9} /> Reopen Corridor
            </button>
          ) : (
            <>
              <button
                type="button"
                disabled={loading}
                onClick={handleDivert}
                className="px-2 py-0.5 rounded text-[9px] font-bold bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border border-amber-500/40 flex items-center gap-1 cursor-pointer transition-colors"
                title="Divert crowd away from this bottleneck to North Exit bypass"
              >
                <Zap size={9} /> ⚡ Divert to North Exit
              </button>
              <button
                type="button"
                disabled={loading}
                onClick={handleRestrict}
                className="px-2 py-0.5 rounded text-[9px] font-bold bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 border border-rose-500/40 flex items-center gap-1 cursor-pointer transition-colors"
                title="Close/restrict inflow on this corridor to stop pileup"
              >
                <Ban size={9} /> 🚫 Restrict Inflow
              </button>
            </>
          )}
        </div>
      </div>
      <Crosshair size={12} className="mt-1 flex-shrink-0" style={{ color: 'var(--cmd-text-faint)' }} />
    </div>
  );
}

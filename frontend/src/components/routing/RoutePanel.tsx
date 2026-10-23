import { useSimulation } from '@/state/SimulationContext';
import { NODE_MAP, EDGE_MAP } from '@/data/venue';
import { Route as RouteIcon, GitBranch, ArrowRight, Ban, RefreshCw } from 'lucide-react';
import type { Route, RouteChange } from '@/types';

export function RoutePanel() {
  const { snapshot, selectEdge } = useSimulation();
  const routing = snapshot?.routing;
  if (!routing) return null;

  const active = routing.activeRoutes;
  const alt = routing.alternativeRoutes;
  const disabled = routing.disabledEdges;
  const changes = routing.recentChanges;

  return (
    <div className="cmd-panel rounded h-full flex flex-col overflow-hidden">
      <div className="flex items-center gap-2 px-3 py-2 border-b border-[var(--cmd-border)]">
        <RouteIcon size={14} color="#817d74" />
        <span className="cmd-label">Dynamic Routing</span>
        <span className="ml-auto text-[10px] text-[var(--cmd-text-faint)]">
          {active.length} active · {alt.length} alt · {disabled.length} disabled
        </span>
      </div>

      <div className="flex-1 overflow-y-auto">
        {/* recent changes */}
        {changes.length > 0 && (
          <div className="border-b border-[var(--cmd-border)]">
            <div className="px-3 py-1.5 bg-[var(--cmd-surface-2)] flex items-center gap-1.5">
              <RefreshCw size={11} color="#817d74" />
              <span className="cmd-label text-[9px]">Recent Changes</span>
            </div>
            {changes.slice(0, 3).map((c) => <RouteChangeRow key={c.id} c={c} />)}
          </div>
        )}

        {/* alternative routes */}
        {alt.length > 0 && (
          <div className="border-b border-[var(--cmd-border)]">
            <div className="px-3 py-1.5 bg-[var(--cmd-surface-2)] flex items-center gap-1.5">
              <GitBranch size={11} color="#817d74" />
              <span className="cmd-label text-[9px]">Recommended Alternatives</span>
            </div>
            {alt.map((r) => <RouteRow key={r.id} r={r} onClick={() => {
              const seg = r.segments[0];
              if (seg) selectEdge(seg.edgeId);
            }} />)}
          </div>
        )}

        {/* active routes */}
        <div>
          <div className="px-3 py-1.5 bg-[var(--cmd-surface-2)] flex items-center gap-1.5">
            <RouteIcon size={11} color="#d39a5a" />
            <span className="cmd-label text-[9px]">Active Routes</span>
          </div>
          {active.length === 0 ? (
            <div className="px-3 py-2 text-[10px] text-[var(--cmd-text-faint)]">No active routes.</div>
          ) : (
            active.map((r) => <RouteRow key={r.id} r={r} onClick={() => {
              const seg = r.segments[0];
              if (seg) selectEdge(seg.edgeId);
            }} />)
          )}
        </div>

        {/* disabled */}
        {disabled.length > 0 && (
          <div className="border-t border-[var(--cmd-border)]">
            <div className="px-3 py-1.5 bg-[var(--cmd-surface-2)] flex items-center gap-1.5">
              <Ban size={11} color="#e04d45" />
              <span className="cmd-label text-[9px]">Disabled Segments</span>
            </div>
            {disabled.map((id) => {
              const e = EDGE_MAP[id];
              if (!e) return null;
              return (
                <div key={id} className="px-3 py-1.5 text-[10px] flex items-center gap-2"
                  style={{ color: 'var(--cmd-text-dim)' }}>
                  <Ban size={10} color="#e04d45" />
                  <span>{NODE_MAP[e.from]?.label} → {NODE_MAP[e.to]?.label}</span>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

function RouteRow({ r, onClick }: { r: Route; onClick: () => void }) {
  const isAlt = r.status === 'recommended';
  const color = isAlt ? '#817d74' : r.status === 'disabled' ? '#e04d45' : '#d39a5a';
  return (
    <button onClick={onClick}
      className="w-full text-left px-3 py-2 border-b border-[var(--cmd-border)] hover:bg-[var(--cmd-surface-2)] transition-colors">
      <div className="flex items-center gap-1.5 mb-1">
        <span className="w-2 h-2 rounded-full" style={{ background: color }} />
        <span className="text-[11px] font-medium text-white truncate">{r.label}</span>
        <span className="ml-auto text-[9px] cmd-mono-value" style={{ color: 'var(--cmd-text-faint)' }}>
          cost {r.cost.toFixed(1)}
        </span>
      </div>
      <div className="flex items-center gap-1 text-[9px] overflow-hidden" style={{ color: 'var(--cmd-text-faint)' }}>
        {r.segments.map((seg, i) => (
          <span key={i} className="flex items-center gap-0.5 flex-shrink-0">
            {NODE_MAP[seg.fromNodeId]?.label}
            <ArrowRight size={8} />
            {i === r.segments.length - 1 ? NODE_MAP[seg.toNodeId]?.label : ''}
            {i < r.segments.length - 1 && <ArrowRight size={8} />}
          </span>
        ))}
      </div>
      {r.flow > 0 && (
        <div className="text-[9px] mt-0.5" style={{ color: 'var(--cmd-text-faint)' }}>
          Flow: {r.flow} people/min
        </div>
      )}
    </button>
  );
}

function RouteChangeRow({ c }: { c: RouteChange }) {
  return (
    <div className="px-3 py-2 border-b border-[var(--cmd-border)]">
      <div className="text-[10px] text-white mb-0.5">{c.reason}</div>
      <div className="flex items-center gap-1.5 text-[9px]" style={{ color: 'var(--cmd-text-faint)' }}>
        <span style={{ color: '#d85b52' }}>old route</span>
        <ArrowRight size={8} />
        <span style={{ color: '#817d74' }}>new route</span>
        <span className="ml-auto">+{c.redistributedFlow} flow</span>
      </div>
    </div>
  );
}

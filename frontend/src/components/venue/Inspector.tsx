import { useState } from 'react';
import { useSimulation } from '@/state/SimulationContext';
import { NODE_MAP, EDGE_MAP } from '@/data/venue';
import { nodeKindColor } from '@/utils/venueColors';
import { pct, formatCountdown } from '@/utils/display';
import { X, MapPin, ArrowRight, Users, Gauge, AlertTriangle, Route, Crosshair, Ban, ShieldAlert, CheckCircle2, Loader2 } from 'lucide-react';

export function Inspector() {
  const { selectedNodeId, selectedEdgeId, selectNode, selectEdge, liveEdges } = useSimulation();
  if (!selectedNodeId && !selectedEdgeId) return null;

  const close = () => { selectNode(null); selectEdge(null); };

  return (
    <div className="inspector absolute top-3 right-3 w-[270px] cmd-surface rounded-lg shadow-2xl z-20 pointer-events-auto border border-[#2b3245]">
      <div className="inspector__header">
        <div className="flex items-center gap-2">
          <Crosshair size={12} color="#d39a5a" />
          <div>
            <div className="cmd-label">Selected on map</div>
            <div className="text-[10px]" style={{ color: 'var(--cmd-text-dim)' }}>Inspector & Controls</div>
          </div>
        </div>
        <button onClick={close} className="icon-button" aria-label="Close inspector"><X size={13} /></button>
      </div>
      {selectedNodeId && <NodeInspector nodeId={selectedNodeId} />}
      {selectedEdgeId && <EdgeInspector edgeId={selectedEdgeId} liveDensity={liveEdges[selectedEdgeId]?.density ?? 0} />}
    </div>
  );
}

function NodeInspector({ nodeId }: { nodeId: string }) {
  const { snapshot, liveAgents, scenario, intervene, activeRestrictions } = useSimulation();
  const [loading, setLoading] = useState(false);
  const node = NODE_MAP[nodeId];
  if (!node) return null;
  const color = nodeKindColor(node.kind);
  const agentsHere = liveAgents.filter((a) => a.fromNodeId === nodeId || a.toNodeId === nodeId).length;
  const bn = snapshot?.safety.bottlenecks.find((b) => b.edgeId && EDGE_MAP[b.edgeId]?.to === nodeId);
  const occupancy = node.capacity ? Math.min(1, agentsHere / node.capacity) : 0;

  // Check if connected edges are closed or restricted
  const connectedEdges = Object.values(EDGE_MAP).filter((e) => e.from === nodeId || e.to === nodeId);
  const isAnyDisabled = connectedEdges.some((e) => snapshot?.routing.disabledEdges.includes(e.id));
  const isAnyRestricted = connectedEdges.some((e) => activeRestrictions.includes(e.id));

  async function handleCloseDoor() {
    setLoading(true);
    try {
      await intervene({
        action: 'close',
        nodeId,
        reason: `Close Door / Gate at ${node?.label}`,
      });
    } finally {
      setLoading(false);
    }
  }

  async function handleReopenDoor() {
    setLoading(true);
    try {
      await intervene({
        action: 'reopen',
        nodeId,
        reason: `Reopen Door / Gate at ${node?.label}`,
      });
    } finally {
      setLoading(false);
    }
  }

  async function handleThrottleGate() {
    setLoading(true);
    try {
      await intervene({
        action: 'restrict',
        nodeId,
        reason: `Throttle / Meter Gate ${node?.label}`,
      });
    } finally {
      setLoading(false);
    }
  }

  async function handleDivertGate() {
    setLoading(true);
    try {
      await intervene({
        action: 'divert',
        nodeId,
        targetNodeId: nodeId.includes('e') ? 'exit-se' : 'exit-n',
        reason: `Divert crowd away from ${node?.label}`,
      });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="p-3 space-y-2.5">
      <div className="flex items-center gap-2">
        <MapPin size={15} style={{ color }} />
        <div>
          <div className="text-[13px] font-bold text-white">{node.label}</div>
          <div className="text-[10px] capitalize" style={{ color: 'var(--cmd-text-dim)' }}>{node.kind} · selected</div>
        </div>
      </div>
      {node.description && <div className="text-[10px] leading-relaxed" style={{ color: 'var(--cmd-text-dim)' }}>{node.description}</div>}
      <div className="occupancy-block">
        <div className="flex items-center justify-between text-[9px] mb-1">
          <span className="cmd-label text-[8px]">Zone Occupancy</span>
          <span className="cmd-mono-value text-white">{pct(occupancy)} of {node.capacity.toLocaleString()} max</span>
        </div>
        <div className="occupancy-bar"><span style={{ width: `${occupancy * 100}%`, background: occupancy > .8 ? '#d85b52' : '#d39a5a' }} /></div>
      </div>
      <div className="grid grid-cols-2 gap-1.5">
        <Info label="Zone Capacity" value={node.capacity.toLocaleString()} />
        <Info label="Agents in Zone" value={String(agentsHere)} icon={<Users size={10} />} />
      </div>
      <div className="pt-2 mt-1 border-t border-[var(--cmd-border)] flex items-center justify-between text-[10px]">
        <span className="text-[var(--cmd-text-faint)]">Event Total Crowd:</span>
        <span className="font-bold text-[#d39a5a]">{scenario.crowdSize.toLocaleString()} attendees</span>
      </div>
      {bn && (
        <div className="critical-card">
          <div className="flex items-center gap-1.5 mb-1"><AlertTriangle size={11} color="#d85b52" /><span className="text-[10px] font-bold text-[#d85b52]">BOTTLENECK</span></div>
          <Info label="Utilization" value={pct(bn.capacityUtilization)} />
          {bn.timeToCriticalMin != null && <Info label="Time to Critical" value={formatCountdown(bn.timeToCriticalMin)} />}
        </div>
      )}

      {/* Operator Door & Gate Controls */}
      <div className="pt-2 border-t border-[#2b3245] space-y-2">
        <div className="text-[10px] font-bold uppercase text-slate-300 flex items-center justify-between">
          <span>Door & Gate Controls</span>
          {isAnyDisabled ? (
            <span className="text-[9px] px-1.5 py-0.5 rounded bg-rose-500/20 text-rose-300 border border-rose-500/40 font-bold">
              DOOR CLOSED
            </span>
          ) : isAnyRestricted ? (
            <span className="text-[9px] px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/40 font-bold">
              THROTTLED
            </span>
          ) : (
            <span className="text-[9px] px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 font-bold">
              OPEN
            </span>
          )}
        </div>

        <div className="grid grid-cols-2 gap-1.5">
          {isAnyDisabled ? (
            <button
              type="button"
              disabled={loading}
              onClick={handleReopenDoor}
              className="col-span-2 px-2.5 py-1.5 rounded text-[11px] font-bold bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 border border-emerald-500/40 flex items-center justify-center gap-1.5 transition-colors cursor-pointer"
            >
              {loading ? <Loader2 size={12} className="animate-spin" /> : <CheckCircle2 size={12} />}
              <span>REOPEN DOOR / GATE</span>
            </button>
          ) : (
            <button
              type="button"
              disabled={loading}
              onClick={handleCloseDoor}
              className="px-2.5 py-1.5 rounded text-[10px] font-bold bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 border border-rose-500/40 flex items-center justify-center gap-1 transition-colors cursor-pointer"
            >
              {loading ? <Loader2 size={11} className="animate-spin" /> : <Ban size={11} />}
              <span>CLOSE DOOR</span>
            </button>
          )}

          {!isAnyDisabled && (
            <button
              type="button"
              disabled={loading}
              onClick={handleThrottleGate}
              className="px-2.5 py-1.5 rounded text-[10px] font-bold bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border border-amber-500/40 flex items-center justify-center gap-1 transition-colors cursor-pointer"
            >
              {loading ? <Loader2 size={11} className="animate-spin" /> : <ShieldAlert size={11} />}
              <span>THROTTLE 50%</span>
            </button>
          )}
        </div>

        <button
          type="button"
          disabled={loading}
          onClick={handleDivertGate}
          className="w-full px-2.5 py-1.5 rounded text-[10px] font-bold bg-blue-500/20 hover:bg-blue-500/30 text-blue-300 border border-blue-500/40 flex items-center justify-center gap-1.5 transition-colors cursor-pointer"
        >
          {loading ? <Loader2 size={11} className="animate-spin" /> : <Route size={11} />}
          <span>DIVERT CROWD TO RELIEF EXIT</span>
        </button>
      </div>
    </div>
  );
}

function EdgeInspector({ edgeId, liveDensity }: { edgeId: string; liveDensity: number }) {
  const { snapshot, intervene, activeRestrictions } = useSimulation();
  const [loading, setLoading] = useState(false);
  const edge = EDGE_MAP[edgeId];
  if (!edge) return null;
  const from = NODE_MAP[edge.from], to = NODE_MAP[edge.to];
  const isDisabled = snapshot?.routing.disabledEdges.includes(edgeId) ?? false;
  const isRestricted = activeRestrictions.includes(edgeId);
  const bn = snapshot?.safety.bottlenecks.find((b) => b.edgeId === edgeId);
  const color = isDisabled ? '#e04d45' : liveDensity > 0.7 ? '#d85b52' : liveDensity > 0.4 ? '#d7a24a' : '#b5a994';

  async function handleClose() {
    setLoading(true);
    try {
      await intervene({
        action: 'close',
        edgeId,
        reason: `Emergency closure of ${edgeId}`,
      });
    } finally {
      setLoading(false);
    }
  }

  async function handleRestrict() {
    setLoading(true);
    try {
      await intervene({
        action: 'restrict',
        edgeId,
        reason: `Restrict corridor ${edgeId}`,
      });
    } finally {
      setLoading(false);
    }
  }

  async function handleReopen() {
    setLoading(true);
    try {
      await intervene({
        action: 'reopen',
        edgeId,
        reason: `Reopen corridor ${edgeId}`,
      });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="p-3 space-y-2.5">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Route size={15} style={{ color }} />
          <div>
            <div className="text-[12px] font-semibold text-white flex items-center gap-1.5">{from?.label} <ArrowRight size={11} /> {to?.label}</div>
            <div className="text-[10px] font-mono text-slate-400">{edgeId}</div>
          </div>
        </div>
        {isDisabled ? (
          <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-rose-500/20 text-rose-300 border border-rose-500/40">
            CLOSED
          </span>
        ) : isRestricted ? (
          <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/40">
            RESTRICTED
          </span>
        ) : (
          <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
            OPEN
          </span>
        )}
      </div>

      <div className="occupancy-block">
        <div className="flex items-center justify-between text-[9px] mb-1">
          <span className="cmd-label text-[8px]">Live density</span>
          <span className="cmd-mono-value" style={{ color }}>{pct(liveDensity)}</span>
        </div>
        <div className="occupancy-bar"><span style={{ width: `${Math.min(1, liveDensity) * 100}%`, background: color }} /></div>
      </div>

      <div className="grid grid-cols-2 gap-1.5">
        <Info label="Width" value={`${edge.width}m`} />
        <Info label="Length" value={`${edge.length}m`} />
        <Info label="Capacity" value={`${edge.capacity}/min`} />
        <Info label="Cost" value={edge.cost.toFixed(1)} />
        <Info label="Flow" value={`${edge.flow}/min`} icon={<Gauge size={10} />} />
        <Info label="Density" value={pct(liveDensity)} color={color} />
      </div>

      {isDisabled && (
        <div className="critical-card flex items-center gap-1.5">
          <AlertTriangle size={11} color="#e04d45" />
          <span className="text-[10px] font-bold text-[#e04d45]">CORRIDOR CLOSED (ROUTES DIVERTED)</span>
        </div>
      )}

      {bn && <div className="text-[10px] leading-relaxed text-amber-300/80">{bn.recommendedAction}</div>}

      {/* Corridor Actions */}
      <div className="pt-2 border-t border-[#2b3245] space-y-1.5">
        <div className="text-[9px] font-bold uppercase text-slate-400 tracking-wider">Corridor Controls</div>
        <div className="grid grid-cols-2 gap-1.5">
          {isDisabled || isRestricted ? (
            <button
              type="button"
              disabled={loading}
              onClick={handleReopen}
              className="col-span-2 px-2 py-1.5 rounded text-[10px] font-bold flex items-center justify-center gap-1 bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 border border-emerald-500/40 cursor-pointer disabled:opacity-50"
            >
              {loading ? <Loader2 size={11} className="animate-spin" /> : <CheckCircle2 size={11} />}
              <span>Reopen Corridor</span>
            </button>
          ) : (
            <>
              <button
                type="button"
                disabled={loading}
                onClick={handleRestrict}
                className="px-2 py-1.5 rounded text-[10px] font-bold flex items-center justify-center gap-1 bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border border-amber-500/40 cursor-pointer disabled:opacity-50"
              >
                {loading ? <Loader2 size={11} className="animate-spin" /> : <ShieldAlert size={11} />}
                <span>Restrict Flow</span>
              </button>
              <button
                type="button"
                disabled={loading}
                onClick={handleClose}
                className="px-2 py-1.5 rounded text-[10px] font-bold flex items-center justify-center gap-1 bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 border border-rose-500/40 cursor-pointer disabled:opacity-50"
              >
                {loading ? <Loader2 size={11} className="animate-spin" /> : <Ban size={11} />}
                <span>Close Corridor</span>
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function Info({ label, value, color, icon }: { label: string; value: string; color?: string; icon?: React.ReactNode }) {
  return (
    <div className="cmd-surface-2 rounded px-2 py-1.5">
      <div className="cmd-label text-[8px] flex items-center gap-1">{icon}{label}</div>
      <div className="text-[12px] font-semibold cmd-mono-value" style={{ color: color ?? '#fff' }}>{value}</div>
    </div>
  );
}

import { useRef, useEffect, useCallback, useState } from 'react';
import { useSimulation } from '@/state/SimulationContext';
import { STADIUM_A, NODE_MAP, EDGE_MAP } from '@/data/venue';
import { nodeKindColor, nodeKindRadius } from '@/utils/venueColors';
import { riskColor } from '@/utils/display';
import type { VenueNode, VenueEdge, SimAgent } from '@/types';

// ===========================================================================
// VenueMap — the visual center of the dashboard
// Canvas layer: crowd particles (efficient for thousands of agents)
// SVG layer:   graph (nodes, edges, routes, bottlenecks, density heatmap)
// Pan & zoom via wheel + drag. Click node/edge to inspect.
// ===========================================================================

const LOGICAL_W = 1000;
const LOGICAL_H = 620;

interface ViewState {
  scale: number;
  offsetX: number;
  offsetY: number;
}

export function VenueMap() {
  const {
    snapshot, liveEdges, liveAgents, layers, activeRestrictions,
    selectedNodeId, selectedEdgeId, selectNode, selectEdge,
  } = useSimulation();

  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [view, setView] = useState<ViewState>({ scale: 1, offsetX: 0, offsetY: 0 });
  const [size, setSize] = useState({ w: 800, h: 600 });
  const dragRef = useRef<{ x: number; y: number; ox: number; oy: number; active: boolean }>({
    x: 0, y: 0, ox: 0, oy: 0, active: false,
  });

  // --- resize observer ---
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const ro = new ResizeObserver(() => {
      const r = el.getBoundingClientRect();
      setSize({ w: r.width, h: r.height });
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  // --- fit-to-view on mount ---
  useEffect(() => {
    if (size.w < 10) return;
    const sx = size.w / LOGICAL_W;
    const sy = size.h / LOGICAL_H;
    const s = Math.min(sx, sy) * 0.92;
    setView({
      scale: s,
      offsetX: (size.w - LOGICAL_W * s) / 2,
      offsetY: (size.h - LOGICAL_H * s) / 2,
    });
  }, [size.w, size.h]);

  // --- canvas crowd rendering ---
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    const dpr = window.devicePixelRatio || 1;
    canvas.width = size.w * dpr;
    canvas.height = size.h * dpr;
    canvas.style.width = `${size.w}px`;
    canvas.style.height = `${size.h}px`;
    ctx.scale(dpr, dpr);

    let raf = 0;
    const draw = () => {
      ctx.clearRect(0, 0, size.w, size.h);
      const { scale, offsetX, offsetY } = view;

      // agents
      if (layers.crowd) {
        const agents = liveAgents;
        const len = agents.length;
        for (let i = 0; i < len; i++) {
          const a = agents[i];
          const sx = a.x * scale + offsetX;
          const sy = a.y * scale + offsetY;
          if (sx < -10 || sx > size.w + 10 || sy < -10 || sy > size.h + 10) continue;
          const edge = liveEdges[a.edgeId];
          const d = edge?.density ?? 0;

          // Vivid high-contrast colors:
          // Critical (> 0.75): Glowing Crimson
          // Congested (> 0.45): High-visibility Gold / Amber
          // Normal: Electric Cyan Blue
          const isCritical = d > 0.75;
          const isHigh = d > 0.45;
          const mainColor = isCritical ? '#ef4444' : isHigh ? '#f59e0b' : '#38bdf8';
          const radius = isCritical ? 4.2 : isHigh ? 3.6 : 3.0;

          // Soft outer glow halo
          ctx.beginPath();
          ctx.fillStyle = mainColor;
          ctx.globalAlpha = 0.28;
          ctx.arc(sx, sy, radius + 2.5, 0, Math.PI * 2);
          ctx.fill();

          // Solid vibrant core
          ctx.beginPath();
          ctx.fillStyle = mainColor;
          ctx.globalAlpha = 0.95;
          ctx.arc(sx, sy, radius, 0, Math.PI * 2);
          ctx.fill();

          // Bright center pinpoint for crispness
          ctx.beginPath();
          ctx.fillStyle = '#ffffff';
          ctx.globalAlpha = 0.85;
          ctx.arc(sx, sy, radius * 0.4, 0, Math.PI * 2);
          ctx.fill();
        }
        ctx.globalAlpha = 1;
      }
      raf = requestAnimationFrame(draw);
    };
    raf = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(raf);

  }, [size, view, liveAgents, liveEdges, layers.crowd]);

  // --- interaction ---
  const onWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault();
    const el = containerRef.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    const mx = e.clientX - r.left;
    const my = e.clientY - r.top;
    setView((v) => {
      const delta = -e.deltaY * 0.0015;
      const newScale = Math.max(0.3, Math.min(4, v.scale * (1 + delta)));
      const ratio = newScale / v.scale;
      return {
        scale: newScale,
        offsetX: mx - (mx - v.offsetX) * ratio,
        offsetY: my - (my - v.offsetY) * ratio,
      };
    });
  }, []);

  const onPointerDown = useCallback((e: React.PointerEvent) => {
    dragRef.current = {
      x: e.clientX, y: e.clientY,
      ox: view.offsetX, oy: view.offsetY,
      active: true,
    };
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
  }, [view.offsetX, view.offsetY]);

  const onPointerMove = useCallback((e: React.PointerEvent) => {
    if (!dragRef.current.active) return;
    const dx = e.clientX - dragRef.current.x;
    const dy = e.clientY - dragRef.current.y;
    setView((v) => ({ ...v, offsetX: dragRef.current.ox + dx, offsetY: dragRef.current.oy + dy }));
  }, []);

  const onPointerUp = useCallback((e: React.PointerEvent) => {
    dragRef.current.active = false;
    (e.target as HTMLElement).releasePointerCapture?.(e.pointerId);
  }, []);

  // convert screen → logical coords
  const screenToLogical = useCallback((sx: number, sy: number) => {
    return {
      x: (sx - view.offsetX) / view.scale,
      y: (sy - view.offsetY) / view.scale,
    };
  }, [view]);

  const handleSvgClick = useCallback((e: React.MouseEvent) => {
    const el = containerRef.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    const { x, y } = screenToLogical(e.clientX - r.left, e.clientY - r.top);
    // find nearest node within 18px
    let nearest: VenueNode | null = null;
    let nearestDist = 18;
    for (const n of STADIUM_A.nodes) {
      const d = Math.hypot(n.x - x, n.y - y);
      if (d < nearestDist) { nearestDist = d; nearest = n; }
    }
    if (nearest) { selectNode(nearest.id); return; }
    // find nearest edge within 8px
    let nearestEdge: VenueEdge | null = null;
    let nearestEdgeDist = 8;
    for (const ed of STADIUM_A.edges) {
      const a = NODE_MAP[ed.from], b = NODE_MAP[ed.to];
      const d = pointToSegmentDist(x, y, a.x, a.y, b.x, b.y);
      if (d < nearestEdgeDist) { nearestEdgeDist = d; nearestEdge = ed; }
    }
    if (nearestEdge) { selectEdge(nearestEdge.id); return; }
    selectNode(null);
  }, [screenToLogical, selectNode, selectEdge]);

  const agents = liveAgents;
  const bottlenecks = snapshot?.safety.bottlenecks ?? [];
  const routes = snapshot?.routing.activeRoutes ?? [];
  const altRoutes = snapshot?.routing.alternativeRoutes ?? [];
  const disabledEdges = new Set(snapshot?.routing.disabledEdges ?? []);
  const isEm = snapshot?.emergency?.active === true;
  const densityCounts = agents.reduce((acc, agent) => {
    const d = liveEdges[agent.edgeId]?.density ?? 0;
    if (d > 0.8) acc.high += 1;
    else if (d > 0.6) acc.medium += 1;
    else acc.low += 1;
    return acc;
  }, { low: 0, medium: 0, high: 0 });

  const transform = `translate(${view.offsetX},${view.offsetY}) scale(${view.scale})`;

  return (
    <div ref={containerRef} className="relative w-full h-full overflow-hidden"
      style={{ background: '#070b10', cursor: dragRef.current.active ? 'grabbing' : 'grab' }}
      onWheel={onWheel}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onClick={handleSvgClick}>

      {/* grid background */}
      <GridBg w={size.w} h={size.h} />

      <canvas ref={canvasRef} className="absolute inset-0 pointer-events-none" />

      <svg width={size.w} height={size.h} className="absolute inset-0 pointer-events-none">
        <g transform={transform}>
          {/* density heatmap (under edges) */}
          {layers.heatmap && <HeatmapLayer edges={liveEdges} />}

          {/* edges */}
          {STADIUM_A.edges.map((e) => {
            const live = liveEdges[e.id];
            const density = live?.density ?? 0;
            const status = live?.status ?? 'open';
            const isDisabled = disabledEdges.has(e.id);
            const isRestricted = activeRestrictions.includes(e.id);
            const isSelected = selectedEdgeId === e.id;
            return (
              <EdgeLine key={e.id} edge={e} live={live} density={density}
                status={status} isDisabled={isDisabled} isRestricted={isRestricted} isSelected={isSelected}
                showFlow={layers.density} />
            );
          })}

          {/* routes */}
          {layers.routes && routes.map((r) => (
            <RouteLine key={r.id} route={r} alt={false} />
          ))}
          {layers.routes && altRoutes.map((r) => (
            <RouteLine key={r.id} route={r} alt={true} />
          ))}

          {/* bottleneck rings */}
          {layers.bottlenecks && bottlenecks.map((b) => {
            const e = EDGE_MAP[b.edgeId];
            if (!e) return null;
            const n = NODE_MAP[e.to];
            return (
              <g key={b.id}>
                <circle cx={n.x} cy={n.y} r={nodeKindRadius(n.kind) + 8}
                  fill="none" stroke={riskColor(b.risk)} strokeWidth="2"
                  opacity="0.7" className="cmd-pulse" />
                <circle cx={n.x} cy={n.y} r={nodeKindRadius(n.kind) + 14}
                  fill="none" stroke={riskColor(b.risk)} strokeWidth="1"
                  opacity="0.3" />
              </g>
            );
          })}

          {/* nodes */}
          {STADIUM_A.nodes.map((n) => (
            <NodeShape key={n.id} node={n}
              selected={selectedNodeId === n.id}
              isEmergency={isEm && snapshot?.emergency?.nodeId === n.id}
              agentCount={agents.filter((a: SimAgent) => a.fromNodeId === n.id).length} />
          ))}

          {/* emergency marker */}
          {isEm && snapshot?.emergency && (
            <EmergencyMarker nodeId={snapshot.emergency.nodeId} />
          )}
        </g>
      </svg>

      {/* zoom controls */}
      <ZoomControls view={view} setView={setView} />

      {/* legend */}
      <MapLegend agentCount={agents.length} densityCounts={densityCounts} showRoutes={layers.routes} />
    </div>
  );
}

// --- sub-components -------------------------------------------------------

function GridBg({ w, h }: { w: number; h: number }) {
  const grid = 40;
  const lines: string[] = [];
  for (let x = 0; x < w; x += grid) lines.push(`M${x} 0V${h}`);
  for (let y = 0; y < h; y += grid) lines.push(`M0 ${y}H${w}`);
  return (
    <svg width={w} height={h} className="absolute inset-0 pointer-events-none opacity-30">
      <path d={lines.join(' ')} stroke="#121511" strokeWidth="1" fill="none" />
    </svg>
  );
}

function EdgeLine({ edge, density, status, isDisabled, isRestricted, isSelected, showFlow }: {
  edge: VenueEdge; live?: VenueEdge; density: number;
  status: VenueEdge['status']; isDisabled: boolean; isRestricted?: boolean; isSelected: boolean;
  showFlow: boolean;
}) {
  const a = NODE_MAP[edge.from], b = NODE_MAP[edge.to];
  if (!a || !b) return null;

  let stroke = '#343b35';
  let width = 2;
  let dash: string | undefined;

  if (isRestricted) {
    stroke = '#f43f5e';
    width = 3.5;
    dash = '6 3';
  } else if (isDisabled || status === 'emergency-closed') {
    stroke = '#e04d45';
    width = 2;
    dash = '6 4';
  } else if (status === 'congested') {
    stroke = density > 0.9 ? '#c94b44' : density > 0.8 ? '#d85b52' : '#d7a24a';
    width = 3;
  } else if (density > 0.5) {
    stroke = '#d7a24a';
    width = 2.5;
  } else if (density > 0.2) {
    stroke = '#4a4033';
    width = 2.5;
  } else {
    stroke = '#343b35';
    width = 2;
  }

  if (isSelected) {
    stroke = '#d39a5a';
    width = 4;
  }

  // direction arrow
  const mx = (a.x + b.x) / 2;
  const my = (a.y + b.y) / 2;
  const angle = Math.atan2(b.y - a.y, b.x - a.x) * 180 / Math.PI;

  return (
    <g>
      <line x1={a.x} y1={a.y} x2={b.x} y2={b.y}
        stroke={stroke} strokeWidth={width} strokeLinecap="round"
        strokeDasharray={dash} opacity={isDisabled ? 0.6 : 0.95} />
      {showFlow && !isDisabled && density > 0.05 && (
        <line x1={a.x} y1={a.y} x2={b.x} y2={b.y}
          stroke={stroke} strokeWidth={width + 2} strokeLinecap="round"
          opacity={0.15} />
      )}
      {/* direction marker */}
      {!isDisabled && (
        <g transform={`translate(${mx},${my}) rotate(${angle})`}>
          <polygon points="-3,-3 4,0 -3,3" fill={stroke} opacity="0.8" />
        </g>
      )}
      {/* restricted tag */}
      {isRestricted && (
        <g transform={`translate(${mx},${my - 10})`}>
          <rect x="-38" y="-7" width="76" height="14" rx="3" fill="#f43f5e" opacity="0.9" />
          <text textAnchor="middle" y="3.5" fill="#ffffff" fontSize="7.5" fontWeight="bold">
            RESTRICTED
          </text>
        </g>
      )}
    </g>
  );
}

function RouteLine({ route, alt }: { route: import('@/types').Route; alt: boolean }) {
  const color = alt ? '#817d74' : '#d39a5a';
  const dash = alt ? '8 4' : undefined;
  return (
    <g>
      {route.segments.map((seg, i) => {
        const e = EDGE_MAP[seg.edgeId];
        if (!e) return null;
        const a = NODE_MAP[seg.fromNodeId], b = NODE_MAP[seg.toNodeId];
        if (!a || !b) return null;
        return (
          <line key={i} x1={a.x} y1={a.y} x2={b.x} y2={b.y}
            stroke={color} strokeWidth={alt ? 3 : 2} fill="none"
            strokeDasharray={dash} strokeLinecap="round"
            opacity="0.5"
            className={alt ? 'cmd-flow-dash-alt' : 'cmd-flow-dash'} />
        );
      })}
    </g>
  );
}

function NodeShape({ node, selected, isEmergency, agentCount }: {
  node: VenueNode; selected: boolean; isEmergency: boolean; agentCount: number;
}) {
  const r = nodeKindRadius(node.kind);
  const color = isEmergency ? '#e04d45' : nodeKindColor(node.kind);
  const size = Math.max(7, Math.round(r * 1.45));
  const isEndpoint = node.kind === 'entry' || node.kind === 'exit';
  return (
    <g>
      {isEndpoint && (
        <rect x={node.x - size / 2 - 4} y={node.y - size / 2 - 4} width={size + 8} height={size + 8}
          fill="none" stroke={color} strokeWidth="1" opacity="0.5" />
      )}
      {selected && (
        <rect x={node.x - size / 2 - 5} y={node.y - size / 2 - 5} width={size + 10} height={size + 10}
          fill="none" stroke="#d39a5a" strokeWidth="1.5" />
      )}
      {node.kind === 'junction' ? (
        <rect x={node.x - size / 2} y={node.y - size / 2} width={size} height={size}
          fill={color + '26'} stroke={color} strokeWidth="1.5" />
      ) : (
        <rect x={node.x - size / 2} y={node.y - size / 2} width={size} height={size}
          fill={color + '26'} stroke={color} strokeWidth="1.5" transform={`rotate(45 ${node.x} ${node.y})`} />
      )}
      <text x={node.x} y={node.y + 3.5} textAnchor="middle"
        fontSize={node.kind === 'stage' ? 9 : 7} fontWeight="700"
        fill={color} pointerEvents="none">
        {node.label.length > 10 ? node.label.slice(0, 9) + '…' : node.label}
      </text>
      {agentCount > 0 && (
        <text x={node.x} y={node.y - size / 2 - 5} textAnchor="middle"
          fontSize="8" fontWeight="700" fill="#e6e0d6" pointerEvents="none">
          {agentCount}
        </text>
      )}
    </g>
  );
}

function EmergencyMarker({ nodeId }: { nodeId: string }) {
  const n = NODE_MAP[nodeId];
  if (!n) return null;
  return (
    <g>
      <circle cx={n.x} cy={n.y} r="30" fill="none" stroke="#e04d45"
        strokeWidth="2" className="cmd-pulse" opacity="0.7" />
      <circle cx={n.x} cy={n.y} r="40" fill="none" stroke="#e04d45"
        strokeWidth="1" opacity="0.3" />
    </g>
  );
}

function HeatmapLayer({ edges }: { edges: Record<string, VenueEdge> }) {
  return (
    <g opacity="0.35">
      {STADIUM_A.edges.map((e) => {
        const live = edges[e.id];
        const d = live?.density ?? 0;
        if (d < 0.1) return null;
        const a = NODE_MAP[e.from], b = NODE_MAP[e.to];
        const color = d > 0.8 ? '#c94b44' : d > 0.6 ? '#d85b52' : d > 0.4 ? '#d7a24a' : '#b5a994';
        return (
          <line key={e.id} x1={a.x} y1={a.y} x2={b.x} y2={b.y}
            stroke={color} strokeWidth={Math.max(4, d * 24)} strokeLinecap="round"
            opacity={0.2 + d * 0.4} />
        );
      })}
    </g>
  );
}

function ZoomControls({ view, setView }: {
  view: ViewState; setView: (v: ViewState) => void;
}) {
  return (
    <div className="zoom-controls absolute bottom-3 right-3">
      <button aria-label="Zoom in" onClick={() => setView({ ...view, scale: Math.min(4, view.scale * 1.2) })}
        className="cmd-surface w-7 h-7 text-sm hover:bg-[var(--cmd-surface-2)] text-[var(--cmd-text)]">+</button>
      <button aria-label="Zoom out" onClick={() => setView({ ...view, scale: Math.max(0.3, view.scale / 1.2) })}
        className="cmd-surface w-7 h-7 text-sm hover:bg-[var(--cmd-surface-2)] text-[var(--cmd-text)]">−</button>
      <button aria-label="Fit map" onClick={() => setView({ scale: 1, offsetX: 0, offsetY: 0 })}
        className="cmd-surface w-7 h-7 text-[8px] hover:bg-[var(--cmd-surface-2)] text-[var(--cmd-text)]">{Math.round(view.scale * 100)}%</button>
    </div>
  );
}

function MapLegend({ agentCount, densityCounts, showRoutes }: {
  agentCount: number; densityCounts: { low: number; medium: number; high: number }; showRoutes?: boolean;
}) {
  return (
    <div className="map-legend absolute top-3 left-3 px-3 py-2 rounded text-[10px] space-y-1.5 pointer-events-none">
      <div className="flex items-baseline justify-between gap-5">
        <span className="metric-label">Agents</span>
        <strong className="text-[15px] font-semibold text-white cmd-mono-value">{agentCount.toLocaleString()}</strong>
      </div>
      <div className="grid grid-cols-3 gap-3 pt-1.5 border-t border-[var(--cmd-border)]">
        <LegendDot color="#b5a994" label={`Low ${densityCounts.low}`} />
        <LegendDot color="#d7a24a" label={`Med ${densityCounts.medium}`} />
        <LegendDot color="#d85b52" label={`High ${densityCounts.high}`} />
      </div>
      {showRoutes && (
        <div className="flex gap-3 pt-1">
          <LegendLine color="#d39a5a" label="Active" />
          <LegendLine color="#77736a" label="Alt" dashed />
        </div>
      )}
    </div>
  );
}

function LegendDot({ color, label }: { color: string; label: string }) {
  return (
    <div className="flex items-center gap-1">
      <div className="w-2 h-2 rounded-full" style={{ background: color }} />
      <span style={{ color: 'var(--cmd-text-dim)' }}>{label}</span>
    </div>
  );
}

function LegendLine({ color, label, dashed }: { color: string; label: string; dashed?: boolean }) {
  return (
    <div className="flex items-center gap-1">
      <svg width="14" height="4"><line x1="0" y1="2" x2="14" y2="2"
        stroke={color} strokeWidth="2" strokeDasharray={dashed ? '3 2' : undefined} /></svg>
      <span style={{ color: 'var(--cmd-text-dim)' }}>{label}</span>
    </div>
  );
}

function pointToSegmentDist(px: number, py: number, x1: number, y1: number, x2: number, y2: number): number {
  const dx = x2 - x1, dy = y2 - y1;
  const len2 = dx * dx + dy * dy;
  if (len2 === 0) return Math.hypot(px - x1, py - y1);
  let t = ((px - x1) * dx + (py - y1) * dy) / len2;
  t = Math.max(0, Math.min(1, t));
  return Math.hypot(px - (x1 + t * dx), py - (y1 + t * dy));
}

import React, { useState, useEffect, useMemo, useRef } from 'react';
import { useSimulation } from '@/state/SimulationContext';
import { STADIUM_A } from '@/data/venue';
import {
  Flame,
  TrendingUp,
  TrendingDown,
  Minus,
  Search,
  Filter,
  ArrowUpDown,
} from 'lucide-react';

// Friendly descriptive names for every corridor in Stadium A
const CORRIDOR_LABELS: Record<string, { name: string; category: string }> = {
  'e-ge-je': { name: 'Main East Entrance Corridor', category: 'Entrance' },
  'e-gw-jw': { name: 'West Gate Entrance Corridor', category: 'Entrance' },
  'e-gs-js': { name: 'South Gate Entrance Corridor', category: 'Entrance' },
  'e-je-stage': { name: 'East Plaza Stage Access', category: 'Central' },
  'e-jw-stage': { name: 'West Plaza Stage Access', category: 'Central' },
  'e-jn-stage': { name: 'North Central Stage Concourse', category: 'Central' },
  'e-js-stage': { name: 'South Central Stage Concourse', category: 'Central' },
  'e-stage-medical': { name: 'Medical Station Emergency Lane', category: 'Emergency' },
  'e-jw-jnw': { name: 'North-West Outer Ring Corridor', category: 'Ring' },
  'e-jw-jsw': { name: 'South-West Outer Ring Corridor', category: 'Ring' },
  'e-je-jne': { name: 'North-East Outer Ring Corridor', category: 'Ring' },
  'e-je-jse': { name: 'South-East Outer Ring Corridor', category: 'Ring' },
  'e-jnw-jn': { name: 'NW to North Junction Link', category: 'Connector' },
  'e-jne-jn': { name: 'NE to North Junction Link', category: 'Connector' },
  'e-jsw-js': { name: 'SW to South Junction Link', category: 'Connector' },
  'e-jse-js': { name: 'SE to South Junction Link', category: 'Connector' },
  'e-jn-foodn': { name: 'North Food Court Promenade', category: 'Facilities' },
  'e-foodn-exitn': { name: 'North Emergency Evacuation Route', category: 'Exit' },
  'e-js-foods': { name: 'South Food Court Plaza Link', category: 'Facilities' },
  'e-jsw-exitsw': { name: 'South-West Egress Corridor', category: 'Exit' },
  'e-jse-exitse': { name: 'South-East Egress Corridor', category: 'Exit' },
  'e-foods-exitsw': { name: 'South Food to SW Exit Link', category: 'Exit' },
  'e-foods-exitse': { name: 'South Food to SE Exit Link', category: 'Exit' },
};

function getDensityColor(density: number): { hex: string; tone: string; badge: string } {
  if (density >= 0.8) return { hex: '#ef4444', tone: 'critical', badge: 'Critical' };
  if (density >= 0.6) return { hex: '#f97316', tone: 'high', badge: 'Congested' };
  if (density >= 0.35) return { hex: '#f59e0b', tone: 'moderate', badge: 'Moderate' };
  return { hex: '#10b981', tone: 'safe', badge: 'Clear' };
}

interface CorridorHistory {
  samples: number[];
  prevDensity: number;
}

export function CorridorHeatmapPanel() {
  const { liveEdges, selectEdge, selectedEdgeId } = useSimulation();

  // History buffer for real-time fluctuations per corridor edge
  const historyRef = useRef<Record<string, CorridorHistory>>({});
  const [, setTick] = useState(0);

  const [searchTerm, setSearchTerm] = useState('');
  const [filterCategory, setFilterCategory] = useState<string>('all');
  const [sortBy, setSortBy] = useState<'density' | 'flow' | 'name'>('density');
  const [sortAsc, setSortAsc] = useState<boolean>(false);

  // Read current edge states
  const edges = useMemo(() => {
    return STADIUM_A.edges.map((baseEdge) => {
      const live = (liveEdges && liveEdges[baseEdge.id]) || null;
      const density = live ? live.density : baseEdge.density;
      const flow = live ? live.flow : baseEdge.flow;
      const status = live ? live.status : baseEdge.status;
      const meta = CORRIDOR_LABELS[baseEdge.id] || {
        name: `Corridor ${baseEdge.from} ↔ ${baseEdge.to}`,
        category: 'Corridor',
      };

      const fromNode = STADIUM_A.nodes.find((n) => n.id === baseEdge.from);
      const toNode = STADIUM_A.nodes.find((n) => n.id === baseEdge.to);

      return {
        ...baseEdge,
        density,
        flow,
        status,
        name: meta.name,
        category: meta.category,
        fromLabel: fromNode?.label || baseEdge.from,
        toLabel: toNode?.label || baseEdge.to,
      };
    });
  }, [liveEdges]);

  // Update rolling fluctuation history every second
  useEffect(() => {
    const interval = setInterval(() => {
      edges.forEach((e) => {
        if (!historyRef.current[e.id]) {
          historyRef.current[e.id] = { samples: [e.density], prevDensity: e.density };
        } else {
          const prev = historyRef.current[e.id].samples;
          historyRef.current[e.id].prevDensity = prev[prev.length - 1] ?? e.density;
          historyRef.current[e.id].samples = [...prev.slice(-24), e.density];
        }
      });
      setTick((t) => t + 1);
    }, 1000);

    return () => clearInterval(interval);
  }, [edges]);

  // Filter & Sort
  const filteredEdges = useMemo(() => {
    return edges
      .filter((e) => {
        if (filterCategory === 'congested') return e.density >= 0.35;
        if (filterCategory === 'emergency') return e.category === 'Emergency' || e.category === 'Exit';
        if (filterCategory !== 'all') return e.category.toLowerCase() === filterCategory.toLowerCase();
        return true;
      })
      .filter((e) => {
        if (!searchTerm) return true;
        const q = searchTerm.toLowerCase();
        return (
          e.name.toLowerCase().includes(q) ||
          e.fromLabel.toLowerCase().includes(q) ||
          e.toLabel.toLowerCase().includes(q) ||
          e.id.toLowerCase().includes(q)
        );
      })
      .sort((a, b) => {
        let diff = 0;
        if (sortBy === 'density') diff = a.density - b.density;
        else if (sortBy === 'flow') diff = a.flow - b.flow;
        else diff = a.name.localeCompare(b.name);
        return sortAsc ? diff : -diff;
      });
  }, [edges, filterCategory, searchTerm, sortBy, sortAsc]);

  // Stats summaries
  const totalCorridors = edges.length;
  const congestedCount = edges.filter((e) => e.density >= 0.35).length;
  const criticalCount = edges.filter((e) => e.density >= 0.8).length;
  const totalFlow = edges.reduce((acc, e) => acc + e.flow, 0);
  const peakEdge = useMemo(() => {
    return [...edges].sort((a, b) => b.density - a.density)[0];
  }, [edges]);

  return (
    <div className="corridor-heatmap-container flex flex-col h-full bg-[#111317] text-[#e2e8f0] rounded-lg overflow-hidden border border-[#272b36]">
      {/* ── Top Header KPI Strip ── */}
      <div className="p-3 bg-[#181b22] border-b border-[#272b36] flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <Flame size={18} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-semibold text-sm text-white tracking-wide">Corridor Density & Heatmap Matrix</span>
              <span className="flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                LIVE STREAM (2 Hz)
              </span>
            </div>
            <div className="text-[11px] text-[#94a3b8]">
              Continuous real-time pedestrian flow, density heat gradients, and corridor capacity telemetry
            </div>
          </div>
        </div>

        {/* Quick KPI stats */}
        <div className="flex items-center gap-3 text-[11px]">
          <div className="px-2.5 py-1 rounded bg-[#20242e] border border-[#2d3342]">
            <span className="text-[#94a3b8] mr-1">Corridors:</span>
            <strong className="text-white font-mono">{totalCorridors}</strong>
          </div>
          <div className="px-2.5 py-1 rounded bg-[#20242e] border border-[#2d3342]">
            <span className="text-[#94a3b8] mr-1">Congested:</span>
            <strong className={congestedCount > 0 ? 'text-amber-400 font-mono' : 'text-emerald-400 font-mono'}>
              {congestedCount}
            </strong>
          </div>
          {criticalCount > 0 && (
            <div className="px-2.5 py-1 rounded bg-rose-500/10 border border-rose-500/30 text-rose-400 font-mono">
              Critical: <strong>{criticalCount}</strong>
            </div>
          )}
          <div className="px-2.5 py-1 rounded bg-[#20242e] border border-[#2d3342]">
            <span className="text-[#94a3b8] mr-1">Aggregate Flow:</span>
            <strong className="text-white font-mono">{totalFlow.toFixed(0)}/min</strong>
          </div>
          {peakEdge && (
            <div className="px-2.5 py-1 rounded bg-[#20242e] border border-[#2d3342] hidden sm:block">
              <span className="text-[#94a3b8] mr-1">Peak:</span>
              <strong className="text-amber-300 font-mono">
                {peakEdge.fromLabel} ↔ {peakEdge.toLabel} ({Math.round(peakEdge.density * 100)}%)
              </strong>
            </div>
          )}
        </div>
      </div>

      {/* ── Toolbar: Filters, Search & Sorters ── */}
      <div className="p-2.5 bg-[#14171d] border-b border-[#272b36] flex flex-wrap items-center justify-between gap-2 text-xs">
        {/* Category Filters */}
        <div className="flex items-center gap-1">
          <Filter size={12} className="text-[#64748b] mr-1" />
          {[
            { id: 'all', label: `All (${totalCorridors})` },
            { id: 'congested', label: `Congested (${congestedCount})` },
            { id: 'Entrance', label: 'Entrances' },
            { id: 'Central', label: 'Central Plaza' },
            { id: 'emergency', label: 'Exits & Medical' },
          ].map((cat) => (
            <button
              key={cat.id}
              type="button"
              onClick={() => setFilterCategory(cat.id)}
              className={`px-2 py-1 rounded text-[11px] transition-colors ${
                filterCategory === cat.id
                  ? 'bg-amber-500/20 text-amber-300 font-medium border border-amber-500/40'
                  : 'bg-[#1e222b] text-[#94a3b8] hover:text-white hover:bg-[#282d39] border border-transparent'
              }`}
            >
              {cat.label}
            </button>
          ))}
        </div>

        {/* Search & Sort Controls */}
        <div className="flex items-center gap-2">
          <div className="relative">
            <Search size={12} className="absolute left-2.5 top-2 text-[#64748b]" />
            <input
              type="text"
              placeholder="Filter corridors or nodes…"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-7 pr-2.5 py-1 bg-[#1e222b] border border-[#2d3342] rounded text-[11px] text-white placeholder-[#64748b] focus:outline-none focus:border-amber-500/50 w-48"
            />
          </div>

          <div className="flex items-center gap-1 bg-[#1e222b] border border-[#2d3342] rounded px-1.5 py-0.5">
            <ArrowUpDown size={11} className="text-[#64748b]" />
            <span className="text-[10px] text-[#64748b]">Sort:</span>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as 'density' | 'flow' | 'name')}
              className="bg-transparent text-[11px] text-[#cbd5e1] focus:outline-none cursor-pointer"
            >
              <option value="density" className="bg-[#1e222b]">Density %</option>
              <option value="flow" className="bg-[#1e222b]">Flow Rate</option>
              <option value="name" className="bg-[#1e222b]">Corridor Name</option>
            </select>
            <button
              type="button"
              onClick={() => setSortAsc((v) => !v)}
              className="px-1 text-[10px] text-[#94a3b8] hover:text-white"
              title="Toggle sort direction"
            >
              {sortAsc ? '▲' : '▼'}
            </button>
          </div>
        </div>
      </div>

      {/* ── Real-Time Table & Heatmap Grid ── */}
      <div className="flex-1 overflow-auto">
        <table className="w-full text-left text-xs border-collapse">
          <thead>
            <tr className="bg-[#181b22] text-[#94a3b8] text-[10px] uppercase font-semibold border-b border-[#272b36] sticky top-0 z-10">
              <th className="py-2.5 px-3">Corridor Name & Category</th>
              <th className="py-2.5 px-3">Segment (From ↔ To)</th>
              <th className="py-2.5 px-3 min-w-[150px]">Live Density Heatmap</th>
              <th className="py-2.5 px-3 text-right">Flow Rate</th>
              <th className="py-2.5 px-3 text-center min-w-[90px]">Fluctuation Trend</th>
              <th className="py-2.5 px-3 text-right">Capacity</th>
              <th className="py-2.5 px-3 text-center">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#1e222b]">
            {filteredEdges.map((edge) => {
              const colorInfo = getDensityColor(edge.density);
              const history = historyRef.current[edge.id];
              const samples = history?.samples || [edge.density];
              const prev = history?.prevDensity ?? edge.density;
              const delta = edge.density - prev;
              const isSelected = selectedEdgeId === edge.id;

              // Sparkline path
              const sparkWidth = 70;
              const sparkHeight = 16;
              const sparkMin = 0;
              const sparkMax = Math.max(1.0, ...samples);
              const sparkPoints = samples
                .map((val, idx) => {
                  const x = (idx / Math.max(1, samples.length - 1)) * sparkWidth;
                  const y = sparkHeight - ((val - sparkMin) / Math.max(0.01, sparkMax - sparkMin)) * sparkHeight;
                  return `${x.toFixed(1)},${y.toFixed(1)}`;
                })
                .join(' ');

              return (
                <tr
                  key={edge.id}
                  onClick={() => selectEdge(isSelected ? null : edge.id)}
                  className={`transition-colors cursor-pointer ${
                    isSelected
                      ? 'bg-amber-500/15 border-l-2 border-amber-400'
                      : 'hover:bg-[#1c2029]'
                  }`}
                >
                  {/* Name & Category */}
                  <td className="py-2 px-3">
                    <div className="font-medium text-[#f1f5f9] flex items-center gap-1.5">
                      <span
                        className="w-2 h-2 rounded-full inline-block shrink-0"
                        style={{ backgroundColor: colorInfo.hex }}
                      />
                      <span>{edge.name}</span>
                    </div>
                    <div className="text-[10px] text-[#64748b] font-mono flex items-center gap-1 mt-0.5">
                      <span className="px-1.5 py-0.2 rounded bg-[#20242e] border border-[#2d3342]">
                        {edge.category}
                      </span>
                      <span>· id: {edge.id}</span>
                    </div>
                  </td>

                  {/* Nodes */}
                  <td className="py-2 px-3 font-mono text-[11px] text-[#cbd5e1]">
                    <div className="flex items-center gap-1">
                      <span className="text-[#38bdf8]">{edge.fromLabel}</span>
                      <span className="text-[#64748b]">↔</span>
                      <span className="text-[#38bdf8]">{edge.toLabel}</span>
                    </div>
                    <div className="text-[9px] text-[#64748b]">width {edge.width}m · {edge.length}m</div>
                  </td>

                  {/* Heatmap Bar */}
                  <td className="py-2 px-3">
                    <div className="flex items-center justify-between text-[11px] font-mono mb-1">
                      <span style={{ color: colorInfo.hex }} className="font-bold">
                        {(edge.density * 100).toFixed(1)}%
                      </span>
                      <span className="text-[10px] text-[#64748b]">
                        {Math.round(edge.density * edge.capacity)} / {edge.capacity}
                      </span>
                    </div>
                    {/* Animated Heatmap Progress Bar */}
                    <div className="w-full h-2 bg-[#20242e] rounded-full overflow-hidden border border-[#2d3342] relative">
                      <div
                        className="h-full rounded-full transition-all duration-500"
                        style={{
                          width: `${Math.min(100, Math.max(4, edge.density * 100))}%`,
                          backgroundColor: colorInfo.hex,
                          boxShadow: edge.density >= 0.6 ? `0 0 8px ${colorInfo.hex}` : 'none',
                        }}
                      />
                    </div>
                  </td>

                  {/* Flow Rate */}
                  <td className="py-2 px-3 text-right font-mono">
                    <span className="text-white font-semibold">{edge.flow.toFixed(0)}</span>
                    <span className="text-[10px] text-[#64748b] ml-1">p/min</span>
                  </td>

                  {/* Live Fluctuation Sparkline & Trend */}
                  <td className="py-2 px-3 text-center">
                    <div className="inline-flex flex-col items-center">
                      <svg width={sparkWidth} height={sparkHeight} className="overflow-visible">
                        <polyline
                          fill="none"
                          stroke={colorInfo.hex}
                          strokeWidth="1.5"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          points={sparkPoints}
                        />
                      </svg>
                      <div className="flex items-center gap-1 text-[9px] font-mono mt-0.5">
                        {delta > 0.005 ? (
                          <span className="text-rose-400 flex items-center">
                            <TrendingUp size={10} className="mr-0.5" /> +{(delta * 100).toFixed(1)}%
                          </span>
                        ) : delta < -0.005 ? (
                          <span className="text-emerald-400 flex items-center">
                            <TrendingDown size={10} className="mr-0.5" /> {(delta * 100).toFixed(1)}%
                          </span>
                        ) : (
                          <span className="text-[#64748b] flex items-center">
                            <Minus size={10} className="mr-0.5" /> 0.0%
                          </span>
                        )}
                      </div>
                    </div>
                  </td>

                  {/* Capacity */}
                  <td className="py-2 px-3 text-right font-mono text-[11px] text-[#94a3b8]">
                    <div>{edge.capacity} cap</div>
                    <div className="text-[9px] text-[#64748b]">{edge.width}m width</div>
                  </td>

                  {/* Status Badge */}
                  <td className="py-2 px-3 text-center">
                    <span
                      className="inline-block px-2 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wider font-mono"
                      style={{
                        backgroundColor: `${colorInfo.hex}22`,
                        color: colorInfo.hex,
                        border: `1px solid ${colorInfo.hex}44`,
                      }}
                    >
                      {colorInfo.badge}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>

        {filteredEdges.length === 0 && (
          <div className="p-8 text-center text-[#64748b] text-xs">
            No corridors match the search or filter criteria.
          </div>
        )}
      </div>

      {/* ── Heatmap Legend & Legend Footer ── */}
      <div className="p-2.5 bg-[#14171d] border-t border-[#272b36] flex flex-wrap items-center justify-between text-[11px] text-[#94a3b8]">
        <div className="flex items-center gap-3">
          <span className="text-[#64748b] text-[10px] uppercase font-semibold">Heat Legend:</span>
          <span className="flex items-center gap-1">
            <span className="w-2.5 h-2.5 rounded-sm bg-[#10b981]" /> Safe (&lt;35%)
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2.5 h-2.5 rounded-sm bg-[#f59e0b]" /> Moderate (35-60%)
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2.5 h-2.5 rounded-sm bg-[#f97316]" /> High (60-80%)
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2.5 h-2.5 rounded-sm bg-[#ef4444]" /> Critical (&gt;80%)
          </span>
        </div>
        <div className="text-[10px] text-[#64748b]">
          Click any corridor row to highlight & inspect on venue map
        </div>
      </div>
    </div>
  );
}

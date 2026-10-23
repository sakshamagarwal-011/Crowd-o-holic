import { useState } from 'react';
import { useSimulation } from '@/state/SimulationContext';
import {
  Zap,
  Sparkles,
  Loader2,
  CheckCircle2,
  RotateCcw,
  DoorOpen,
  Ban,
  ArrowUpRight,
  Info,
  Navigation,
  Compass,
} from 'lucide-react';
import type { MitigationPlanResponse } from '@/services/backendClient';

export function CrowdMitigationPanel() {
  const { snapshot, intervene, getMitigationPlan, activeRestrictions } = useSimulation();
  const [loadingAi, setLoadingAi] = useState(false);
  const [sectorFocus, setSectorFocus] = useState<'auto' | 'east' | 'west' | 'north'>('auto');
  const [plan, setPlan] = useState<MitigationPlanResponse | null>(null);
  const [executingId, setExecutingId] = useState<string | null>(null);
  const [lastActionMsg, setLastActionMsg] = useState<string | null>(null);

  const bottlenecks = snapshot?.safety.bottlenecks ?? [];
  const hasRush = bottlenecks.length > 0 || (snapshot?.safety.riskScore ?? 0) >= 40;

  // Determine active primary bottleneck based on selection or live telemetry
  let activeEdge = 'e-ge-je';
  let activeLocation = 'East Gate / Main Entrance (e-ge-je)';
  let targetExit = 'exit-se (South-East Exit, 900/hr)';
  let targetExitNode = 'exit-se';

  if (sectorFocus === 'east') {
    activeEdge = 'e-ge-je';
    activeLocation = 'East Gate Corridor (e-ge-je)';
    targetExit = 'exit-se (South-East Exit) & exit-n (North Exit)';
    targetExitNode = 'exit-se';
  } else if (sectorFocus === 'west') {
    activeEdge = 'e-gw-jw';
    activeLocation = 'West Corridor (e-gw-jw)';
    targetExit = 'exit-sw (South-West Exit) & exit-n (North Exit)';
    targetExitNode = 'exit-sw';
  } else if (sectorFocus === 'north') {
    activeEdge = 'e-jn-foodn';
    activeLocation = 'North Food Concourse (e-jn-foodn)';
    targetExit = 'exit-n (North Exit Evacuation Route)';
    targetExitNode = 'exit-n';
  } else if (bottlenecks.length > 0) {
    const first = bottlenecks[0];
    activeEdge = first.edgeId;
    activeLocation = `${first.location} (${first.edgeId})`;
    if (activeEdge.includes('ge') || activeEdge.includes('je')) {
      targetExit = 'exit-se (South-East Exit) & exit-n';
      targetExitNode = 'exit-se';
    } else if (activeEdge.includes('gw') || activeEdge.includes('jw')) {
      targetExit = 'exit-sw (South-West Exit) & exit-n';
      targetExitNode = 'exit-sw';
    } else {
      targetExit = 'exit-n (North Exit Relief Bypass)';
      targetExitNode = 'exit-n';
    }
  }

  async function handleConsultAi() {
    setLoadingAi(true);
    try {
      const result = await getMitigationPlan(sectorFocus === 'auto' ? undefined : sectorFocus);
      if (result) {
        setPlan(result);
        setLastActionMsg(`Generated tactical plan via ${result.model}`);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingAi(false);
    }
  }

  async function executeAction(
    actionType: 'restrict' | 'open_bypass' | 'divert' | 'reopen',
    edgeId?: string,
    targetNodeId?: string,
    label?: string,
  ) {
    setExecutingId(edgeId || actionType);
    try {
      await intervene({
        action: actionType,
        edgeId,
        targetNodeId: targetNodeId || targetExitNode,
        reason: label,
      });
      setLastActionMsg(`Executed: ${label || actionType}`);
      setTimeout(() => setLastActionMsg(null), 4000);
    } catch (err) {
      console.error(err);
    } finally {
      setExecutingId(null);
    }
  }

  const isEdgeRestricted = (eid: string) => activeRestrictions.includes(eid);

  return (
    <div className="cmd-panel rounded-lg overflow-hidden border border-[#2b3245] bg-[#12151d] text-slate-200">
      {/* Panel Header */}
      <div className="panel-header bg-[#181d28] px-3 py-2 border-b border-[#2b3245] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Zap size={14} className="text-amber-400" />
          <span className="text-xs font-bold uppercase tracking-wider text-white">
            Crowd Rush Solutions & Control
          </span>
        </div>
        <span
          className={`text-[9px] font-bold px-2 py-0.5 rounded ${
            hasRush
              ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
              : 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
          }`}
        >
          {hasRush ? 'RUSH ACTIVE' : 'FLOW BALANCED'}
        </span>
      </div>

      <div className="p-3 space-y-3">
        {/* Sector Focus Filter */}
        <div className="flex items-center gap-1.5 bg-[#171b24] p-1 rounded border border-[#272c3d]">
          <span className="text-[10px] text-slate-400 font-semibold px-1 flex items-center gap-1">
            <Compass size={11} className="text-cyan-400" /> Focus:
          </span>
          <button
            type="button"
            onClick={() => {
              setSectorFocus('auto');
              setPlan(null);
            }}
            className={`px-2 py-0.5 rounded text-[10px] font-medium transition-colors ${
              sectorFocus === 'auto'
                ? 'bg-cyan-500/20 text-cyan-300 font-bold border border-cyan-500/40'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Auto-Detect
          </button>
          <button
            type="button"
            onClick={() => {
              setSectorFocus('east');
              setPlan(null);
            }}
            className={`px-2 py-0.5 rounded text-[10px] font-medium transition-colors ${
              sectorFocus === 'east'
                ? 'bg-amber-500/20 text-amber-300 font-bold border border-amber-500/40'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            East Gate Rush
          </button>
          <button
            type="button"
            onClick={() => {
              setSectorFocus('west');
              setPlan(null);
            }}
            className={`px-2 py-0.5 rounded text-[10px] font-medium transition-colors ${
              sectorFocus === 'west'
                ? 'bg-indigo-500/20 text-indigo-300 font-bold border border-indigo-500/40'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            West Gate Rush
          </button>
          <button
            type="button"
            onClick={() => {
              setSectorFocus('north');
              setPlan(null);
            }}
            className={`px-2 py-0.5 rounded text-[10px] font-medium transition-colors ${
              sectorFocus === 'north'
                ? 'bg-emerald-500/20 text-emerald-300 font-bold border border-emerald-500/40'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            North Concourse
          </button>
        </div>

        {/* Diagnostic Routing Box: Where blocked & where to evacuate */}
        <div className="rounded p-2.5 bg-[#161c28] border border-[#2c364e] space-y-1.5">
          <div className="flex items-center justify-between text-[11px]">
            <div className="flex items-center gap-1.5 text-rose-300 font-medium truncate">
              <Ban size={12} className="text-rose-400 flex-shrink-0" />
              <span>Blocked Corridor:</span>
              <span className="font-mono text-white bg-rose-950/60 px-1.5 py-0.2 rounded border border-rose-800/40">
                {activeLocation}
              </span>
            </div>
          </div>
          <div className="flex items-center justify-between text-[11px]">
            <div className="flex items-center gap-1.5 text-emerald-300 font-medium truncate">
              <Navigation size={12} className="text-emerald-400 flex-shrink-0" />
              <span>Evacuation Relief Exit:</span>
              <span className="font-mono text-white bg-emerald-950/60 px-1.5 py-0.2 rounded border border-emerald-800/40">
                {targetExit}
              </span>
            </div>
          </div>
        </div>

        {/* Active Strategy / Explanation Banner */}
        <div className="rounded p-2.5 bg-[#181f2f] border border-blue-500/20 text-xs">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[10px] font-bold uppercase text-blue-400 flex items-center gap-1">
              <Info size={12} /> Tactical Solution Strategy
            </span>
            <button
              type="button"
              onClick={handleConsultAi}
              disabled={loadingAi}
              className="flex items-center gap-1 px-2.5 py-1 rounded text-[10px] font-semibold bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border border-amber-500/40 transition-colors disabled:opacity-50 cursor-pointer shadow"
            >
              {loadingAi ? <Loader2 size={11} className="animate-spin" /> : <Sparkles size={11} />}
              <span>{loadingAi ? 'Analyzing Ollama…' : 'Consult Ollama GPU'}</span>
            </button>
          </div>
          <p className="text-slate-300 leading-relaxed text-[11px]">
            {plan?.tactical_strategy ||
              (sectorFocus === 'east' || activeEdge.includes('ge')
                ? 'East Gate se heavy arrival surge hai. East Corridor (e-ge-je) inflow throttle karein aur crowd ko South-East Exit (exit-se) bypass tatha North Exit (exit-n) ki taraf nikalein.'
                : hasRush
                  ? `Congestion detected at ${activeLocation}. Restrict inflow corridor (${activeEdge}) aur crowd ko bypass route (${targetExit}) ki taraf divert karein.`
                  : 'Corridors operating within safe limits. Preemptive bypass routes ready to absorb East or West surges.')}
          </p>
        </div>

        {/* Action Status Feedback Toast */}
        {lastActionMsg && (
          <div className="rounded px-2.5 py-1.5 text-[11px] bg-emerald-500/15 border border-emerald-500/40 text-emerald-300 flex items-center gap-1.5 animate-fadeIn">
            <CheckCircle2 size={13} className="text-emerald-400 flex-shrink-0" />
            <span>{lastActionMsg}</span>
          </div>
        )}

        {/* Tactical Solutions Checklist (Dynamic or Context-Aware) */}
        {plan && plan.actions.length > 0 ? (
          <div className="space-y-2">
            <div className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1">
              <Sparkles size={11} className="text-amber-400" />
              Tactical Recommended Actions ({plan.actions.length})
            </div>
            {plan.actions.map((act) => {
              const restricted = act.edge_id ? isEdgeRestricted(act.edge_id) : false;
              const isExecuting = executingId === (act.edge_id || act.id);

              return (
                <div
                  key={act.id}
                  className="rounded p-2 bg-[#171b24] border border-[#2b3245] hover:border-slate-600 transition-colors"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-semibold text-white text-[11px] truncate flex items-center gap-1.5">
                      {act.action_type === 'restrict' ? (
                        <Ban size={12} className="text-rose-400" />
                      ) : act.action_type === 'open_bypass' ? (
                        <DoorOpen size={12} className="text-emerald-400" />
                      ) : (
                        <ArrowUpRight size={12} className="text-blue-400" />
                      )}
                      {act.title}
                    </span>
                    {restricted && (
                      <span className="text-[8px] font-bold px-1.5 py-0.5 rounded bg-rose-500/20 text-rose-300 border border-rose-500/30">
                        RESTRICTED
                      </span>
                    )}
                  </div>
                  <p className="text-[10px] text-slate-400 leading-snug mb-2">{act.instruction}</p>
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-[9px] text-slate-500 italic truncate">{act.expected_outcome}</span>
                    <button
                      type="button"
                      disabled={isExecuting}
                      onClick={() =>
                        executeAction(
                          act.action_type === 'meter' ? 'divert' : act.action_type,
                          act.edge_id,
                          act.target_node_id,
                          act.title,
                        )
                      }
                      className="px-2.5 py-1 rounded text-[10px] font-bold uppercase transition-all flex items-center gap-1 bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border border-amber-500/40 disabled:opacity-50 flex-shrink-0 cursor-pointer"
                    >
                      {isExecuting ? <Loader2 size={10} className="animate-spin" /> : <Zap size={10} />}
                      <span>Execute</span>
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          /* Context-Aware Solutions for East / West / General */
          <div className="space-y-2">
            <div className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider flex items-center justify-between">
              <span>Tactical Solutions Checklist</span>
              <span className="text-amber-400 font-mono text-[9px]">
                {sectorFocus === 'east' || activeEdge.includes('ge') ? 'EAST SECTOR PROTOCOL' : 'STANDARD PROTOCOL'}
              </span>
            </div>

            {/* Solution 1: Restrict / Meter Inflow */}
            <div className="rounded p-2 bg-[#171b24] border border-[#2b3245] flex items-center justify-between gap-2">
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-1.5 text-[11px] font-semibold text-white">
                  <Ban size={12} className="text-rose-400 flex-shrink-0" />
                  <span className="truncate">
                    1. {sectorFocus === 'east' || activeEdge.includes('ge') ? 'Meter East Gate Inflow' : `Restrict Inflow on ${activeLocation}`}
                  </span>
                </div>
                <div className="text-[10px] text-slate-400 mt-0.5">
                  {sectorFocus === 'east' || activeEdge.includes('ge')
                    ? 'Corridor e-ge-je turnstiles throttle karke concourse queue build-up roko'
                    : `Corridor ${activeEdge} close karke queue compression roko`}
                </div>
              </div>
              <button
                type="button"
                disabled={executingId === activeEdge}
                onClick={() => executeAction('restrict', activeEdge, targetExitNode, `Throttle ${activeLocation}`)}
                className={`px-2.5 py-1 rounded text-[10px] font-bold uppercase transition-all flex items-center gap-1 flex-shrink-0 cursor-pointer ${
                  isEdgeRestricted(activeEdge)
                    ? 'bg-rose-500/30 text-rose-200 border border-rose-500/50'
                    : 'bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 border border-rose-500/40'
                }`}
              >
                {executingId === activeEdge ? <Loader2 size={10} className="animate-spin" /> : <Ban size={10} />}
                <span>{isEdgeRestricted(activeEdge) ? 'Restricted' : 'Throttle Inflow'}</span>
              </button>
            </div>

            {/* Solution 2: Open Dedicated Exit Bypass */}
            <div className="rounded p-2 bg-[#171b24] border border-[#2b3245] flex items-center justify-between gap-2">
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-1.5 text-[11px] font-semibold text-white">
                  <DoorOpen size={12} className="text-emerald-400 flex-shrink-0" />
                  <span className="truncate">
                    2. {sectorFocus === 'east' || activeEdge.includes('ge') ? 'Open South-East Exit Bypass (exit-se)' : 'Open North Exit Bypass (exit-n)'}
                  </span>
                </div>
                <div className="text-[10px] text-slate-400 mt-0.5">
                  {sectorFocus === 'east' || activeEdge.includes('ge')
                    ? 'SE Exit khol kar 900 people/hr ko direct perimeter par nikalo'
                    : 'North Exit turnstiles khol kar 2,000 people/hr evacuate karo'}
                </div>
              </div>
              <button
                type="button"
                disabled={executingId === 'open_bypass'}
                onClick={() =>
                  executeAction(
                    'open_bypass',
                    undefined,
                    sectorFocus === 'east' || activeEdge.includes('ge') ? 'exit-se' : 'exit-n',
                    sectorFocus === 'east' || activeEdge.includes('ge') ? 'Open South-East Exit' : 'Open North Exit Bypass',
                  )
                }
                className="px-2.5 py-1 rounded text-[10px] font-bold uppercase transition-all flex items-center gap-1 flex-shrink-0 bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 border border-emerald-500/40 cursor-pointer"
              >
                {executingId === 'open_bypass' ? (
                  <Loader2 size={10} className="animate-spin" />
                ) : (
                  <DoorOpen size={10} />
                )}
                <span>Open Bypass</span>
              </button>
            </div>

            {/* Solution 3: Divert Flow to Secondary Relief Corridor */}
            <div className="rounded p-2 bg-[#171b24] border border-[#2b3245] flex items-center justify-between gap-2">
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-1.5 text-[11px] font-semibold text-white">
                  <ArrowUpRight size={12} className="text-blue-400 flex-shrink-0" />
                  <span className="truncate">
                    3. {sectorFocus === 'east' || activeEdge.includes('ge') ? 'Divert to North Concourse (exit-n)' : 'Divert to South Gate (gate-s)'}
                  </span>
                </div>
                <div className="text-[10px] text-slate-400 mt-0.5">
                  {sectorFocus === 'east' || activeEdge.includes('ge')
                    ? 'NE Corridor (j-ne) ke through crowd ko North Exit par reroute karo'
                    : 'Concourse crowd ko gate-s / plaza ki taraf divert karo'}
                </div>
              </div>
              <button
                type="button"
                disabled={executingId === 'divert-relief'}
                onClick={() =>
                  executeAction(
                    'divert',
                    activeEdge,
                    sectorFocus === 'east' || activeEdge.includes('ge') ? 'exit-n' : 'gate-s',
                    sectorFocus === 'east' || activeEdge.includes('ge') ? 'Divert to North Exit' : 'Divert to South Gate',
                  )
                }
                className="px-2.5 py-1 rounded text-[10px] font-bold uppercase transition-all flex items-center gap-1 flex-shrink-0 bg-blue-500/20 hover:bg-blue-500/30 text-blue-300 border border-blue-500/40 cursor-pointer"
              >
                {executingId === 'divert-relief' ? (
                  <Loader2 size={10} className="animate-spin" />
                ) : (
                  <ArrowUpRight size={10} />
                )}
                <span>Divert Flow</span>
              </button>
            </div>
          </div>
        )}

        {/* Reopen All Corridors / Reset Action */}
        <div className="pt-1 flex items-center justify-between border-t border-[#2b3245]">
          <div className="text-[10px] text-slate-400">
            Active restrictions:{' '}
            <span className="font-mono text-amber-300">
              {activeRestrictions.length > 0 ? activeRestrictions.join(', ') : 'None'}
            </span>
          </div>
          <button
            type="button"
            disabled={activeRestrictions.length === 0 && executingId === 'reopen'}
            onClick={() => executeAction('reopen', undefined, undefined, 'Reopen All Corridors')}
            className="flex items-center gap-1 px-2.5 py-1 rounded text-[10px] font-semibold bg-slate-700/50 hover:bg-slate-700 text-slate-300 border border-slate-600 transition-colors disabled:opacity-40 cursor-pointer"
          >
            <RotateCcw size={10} />
            <span>Reopen All Corridors</span>
          </button>
        </div>
      </div>
    </div>
  );
}

import type {
  Scenario, SimAgent, SimulationState, CrowdMetrics, SafetyState,
  RoutingState, AIState, EmergencyEvent, TimelineEntry, SimSnapshot,
  Bottleneck, RiskLevel, Route, RouteChange, AIRecommendation,
  SafetyAlert, VenueEdge,
} from '@/types';
import {
  STADIUM_A, NODE_MAP, shortestPath, edgeBetween, EDGE_MAP,
} from '@/data/venue';

// ===========================================================================
// Mock simulation engine
// Produces a SimSnapshot each tick. This stands in for the real backend's
// crowd sim, metrics, risk, routing, and AI layers. The component layer
// only ever consumes SimSnapshot — so replacing this with a WebSocket feed
// that emits the same shape requires no UI changes.
// ===========================================================================

const MAX_AGENTS_RENDERED = 1400; // visual cap; crowd represented as particles

interface EngineState {
  status: SimulationState['status'];
  simTimeMin: number;
  speed: number;
  agents: SimAgent[];
  totalEntered: number;
  totalExited: number;
  nextAgentId: number;
  edges: Record<string, VenueEdge>; // mutable copies with live flow/density
  disabledEdges: Set<string>;
  emergency: EmergencyEvent | null;
  timeline: TimelineEntry[];
  routes: Route[];
  routeChanges: RouteChange[];
  aiHistory: AIRecommendation[];
  lastAiMinute: number;
  acknowledgedAlerts: Set<string>;
}

function cloneEdges(): Record<string, VenueEdge> {
  const out: Record<string, VenueEdge> = {};
  for (const e of STADIUM_A.edges) {
    out[e.id] = { ...e, status: 'open', flow: 0, density: 0 };
  }
  return out;
}

function emptyState(): EngineState {
  return {
    status: 'idle',
    simTimeMin: -60, // start 60 min before event start (arrival phase)
    speed: 1,
    agents: [],
    totalEntered: 0,
    totalExited: 0,
    nextAgentId: 0,
    edges: cloneEdges(),
    disabledEdges: new Set(),
    emergency: null,
    timeline: [],
    routes: buildDefaultRoutes(),
    routeChanges: [],
    aiHistory: [],
    lastAiMinute: -999,
    acknowledgedAlerts: new Set(),
  };
}

let state: EngineState = emptyState();

export function getVenue() {
  return STADIUM_A;
}

export function resetSimulation() {
  state = emptyState();
}

export function setSpeed(mult: number) {
  state.speed = mult;
}

export function startSimulation() {
  if (state.status === 'completed' || state.status === 'error') {
    state = emptyState();
  }
  state.status = 'running';
  pushTimeline('simulation', 'Simulation started', 'Live crowd simulation is now running.');
}

export function pauseSimulation() {
  if (state.status === 'running') {
    state.status = 'paused';
    pushTimeline('simulation', 'Simulation paused', 'Operator paused the simulation.');
  }
}

export function resumeSimulation() {
  if (state.status === 'paused') {
    state.status = 'running';
    pushTimeline('simulation', 'Simulation resumed', 'Operator resumed the simulation.');
  }
}

export function getStatus() {
  return state.status;
}

export function getSimTimeMin() {
  return state.simTimeMin;
}

// --- Emergency trigger ----------------------------------------------------

export function triggerEmergency(
  type: EmergencyEvent['type'],
  nodeId: string,
): void {
  if (state.emergency?.active) return;
  const node = NODE_MAP[nodeId];
  // close edges around the node
  const closed = STADIUM_A.edges
    .filter((e) => e.from === nodeId || e.to === nodeId)
    .map((e) => e.id);
  closed.forEach((id) => {
    state.disabledEdges.add(id);
    if (state.edges[id]) state.edges[id].status = 'emergency-closed';
  });
  state.emergency = {
    id: `em-${Date.now()}`,
    type,
    location: node.label,
    nodeId,
    atMinute: state.simTimeMin,
    active: true,
    closedEdgeIds: closed,
    summary: `${typeLabel(type)} reported at ${node.label}. Affected routes disabled and rerouting initiated.`,
  };
  // recalc routes
  recomputeRoutes();
  pushTimeline('emergency', `EMERGENCY: ${typeLabel(type)} at ${node.label}`,
    `${closed.length} route segment(s) disabled. Rerouting in progress.`, 'emergency');
}

export function clearEmergency() {
  if (!state.emergency) return;
  const em = state.emergency;
  em.active = false;
  // reopen edges
  em.closedEdgeIds.forEach((id) => {
    state.disabledEdges.delete(id);
    if (state.edges[id]) state.edges[id].status = 'open';
  });
  pushTimeline('emergency', 'Emergency cleared',
    `${em.location} reopened. Routes restored.`);
  recomputeRoutes();
  state.emergency = null;
}

function typeLabel(t: EmergencyEvent['type']): string {
  const map: Record<string, string> = {
    fire: 'Fire', medical: 'Medical incident', structural: 'Structural failure',
    security: 'Security threat', 'crowd-crush': 'Crowd crush risk', 'gate-failure': 'Gate failure',
  };
  return map[t] ?? t;
}

// --- Routing --------------------------------------------------------------

function buildDefaultRoutes(): Route[] {
  const routes: Route[] = [];
  // gate-e → stage
  routes.push(makeRoute('r-ge-stage', 'gate-e', 'stage', 'East Gate → Main Stage', 'active'));
  // gate-w → stage
  routes.push(makeRoute('r-gw-stage', 'gate-w', 'stage', 'West Gate → Main Stage', 'active'));
  // gate-s → food-n
  routes.push(makeRoute('r-gs-foodn', 'gate-s', 'food-n', 'South Gate → North Food Court', 'active'));
  // exit routes
  routes.push(makeRoute('r-stage-exitn', 'stage', 'exit-n', 'Stage → North Exit', 'active'));
  routes.push(makeRoute('r-stage-exitsw', 'stage', 'exit-sw', 'Stage → SW Exit', 'active'));
  routes.push(makeRoute('r-stage-exitse', 'stage', 'exit-se', 'Stage → SE Exit', 'active'));
  return routes;
}

function makeRoute(id: string, fromId: string, toId: string, label: string,
                   status: Route['status']): Route {
  const path = shortestPath(fromId, toId) ?? [fromId, toId];
  const segments = pathToSegments(path);
  const cost = segments.reduce((s, seg) => s + (EDGE_MAP[seg.edgeId]?.cost ?? 1), 0);
  return { id, fromNodeId: fromId, toNodeId: toId, segments, status, cost, flow: 0, label };
}

function pathToSegments(path: string[]): Route['segments'] {
  const segs: Route['segments'] = [];
  for (let i = 0; i < path.length - 1; i++) {
    const e = edgeBetween(path[i], path[i + 1]);
    if (e) segs.push({ edgeId: e.id, fromNodeId: path[i], toNodeId: path[i + 1] });
  }
  return segs;
}

function recomputeRoutes() {
  // mark routes that use disabled edges as disabled, find alternatives
  const active: Route[] = [];
  const alts: Route[] = [];
  for (const r of state.routes) {
    const usesDisabled = r.segments.some((s) => state.disabledEdges.has(s.edgeId));
    if (usesDisabled && r.status !== 'disabled') {
      // find alternative
      const alt = findAlternativeRoute(r.fromNodeId, r.toNodeId);
      if (alt) {
        alts.push(alt);
        const change: RouteChange = {
          id: `rc-${Date.now()}-${r.id}`,
          atMinute: state.simTimeMin,
          reason: state.emergency?.active
            ? `Route disabled due to emergency at ${state.emergency.location}`
            : 'Route disabled due to congestion',
          fromRouteId: r.id,
          toRouteId: alt.id,
          affectedEdgeId: r.segments.find((s) => state.disabledEdges.has(s.edgeId))?.edgeId ?? '',
          redistributedFlow: r.flow,
        };
        state.routeChanges.unshift(change);
        pushTimeline('route-change', 'Route recalculated',
          `${r.label} disabled. Alternative: ${alt.label}.`);
        active.push({ ...r, status: 'disabled', flow: 0 });
      } else {
        active.push({ ...r, status: 'disabled', flow: 0 });
      }
    } else if (r.status === 'disabled' && !usesDisabled) {
      active.push({ ...r, status: 'active' });
    } else {
      active.push(r);
    }
  }
  state.routes = [...active, ...alts];
}

function findAlternativeRoute(fromId: string, toId: string): Route | null {
  const path = shortestPath(fromId, toId);
  if (!path || path.length < 2) return null;
  return makeRoute(`r-alt-${Date.now()}`, fromId, toId,
    `${NODE_MAP[fromId].label} → ${NODE_MAP[toId].label} (alt)`, 'recommended');
}

// --- Timeline -------------------------------------------------------------

function pushTimeline(
  kind: TimelineEntry['kind'], title: string, detail: string,
  severity?: RiskLevel,
) {
  state.timeline.unshift({
    id: `tl-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
    atMinute: state.simTimeMin,
    kind, title, detail, severity,
  });
  if (state.timeline.length > 50) state.timeline.length = 50;
}

// --- Agent spawning & movement -------------------------------------------

function spawnAgents(scenario: Scenario, dtSec: number) {
  const t = state.simTimeMin;
  for (const grp of scenario.crowdGroups) {
    if (t < grp.arrivalStartMin || t > grp.arrivalEndMin) continue;
    const window = grp.arrivalEndMin - grp.arrivalStartMin;
    const ratePerMin = grp.size / Math.max(window, 1);
    const toSpawn = ratePerMin * (dtSec / 60) * state.speed;
    const n = Math.floor(toSpawn + Math.random());
    for (let i = 0; i < n; i++) {
      if (state.agents.length >= MAX_AGENTS_RENDERED) return;
      spawnOneAgent(grp);
    }
  }
}

function spawnOneAgent(
  grp: Scenario['crowdGroups'][number],
) {
  const startNode = NODE_MAP[grp.entryGateId];
  const path = shortestPath(grp.entryGateId, grp.destinationNodeId);
  if (!path || path.length < 2) return;
  const firstEdge = edgeBetween(path[0], path[1]);
  if (!firstEdge) return;
  const agent: SimAgent = {
    id: state.nextAgentId++,
    x: startNode.x + (Math.random() - 0.5) * 20,
    y: startNode.y + (Math.random() - 0.5) * 20,
    vx: 0, vy: 0,
    groupId: grp.id,
    fromNodeId: path[0],
    toNodeId: path[1],
    edgeId: firstEdge.id,
    progress: 0,
    speed: 40 + Math.random() * 30, // logical units / sec
  };
  state.agents.push(agent);
  state.totalEntered++;
}

function moveAgents(dtSec: number) {
  const remaining: SimAgent[] = [];
  for (const a of state.agents) {
    const edge = state.edges[a.edgeId];
    if (!edge || state.disabledEdges.has(a.edgeId)) {
      // edge closed under agent — replan
      replanAgent(a);
      if (a.edgeId) remaining.push(a);
      continue;
    }
    const from = NODE_MAP[a.fromNodeId];
    const to = NODE_MAP[a.toNodeId];
    if (!from || !to) continue;
    const dx = to.x - from.x;
    const dy = to.y - from.y;
    const len = Math.hypot(dx, dy);
    if (len < 0.1) { advanceAgent(a); if (a.edgeId) remaining.push(a); continue; }
    // slow down on congested edges
    const congestionFactor = 1 - edge.density * 0.6;
    const step = (a.speed * congestionFactor * dtSec * state.speed) / len;
    a.progress += step;
    if (a.progress >= 1) {
      advanceAgent(a);
    } else {
      a.x = from.x + dx * a.progress;
      a.y = from.y + dy * a.progress;
      a.vx = dx / len;
      a.vy = dy / len;
      remaining.push(a);
    }
  }
  state.agents = remaining;
}

function advanceAgent(a: SimAgent) {
  // arrived at toNode
  const arrivedAt = a.toNodeId;
  // if destination reached, remove
  const grp = DEFAULT_SCENARIO_LOCAL?.crowdGroups.find((g) => g.id === a.groupId);
  if (grp && arrivedAt === grp.destinationNodeId) {
    state.totalExited++;
    return; // agent leaves sim
  }
  // continue along path
  replanAgent(a, arrivedAt);
}

let DEFAULT_SCENARIO_LOCAL: Scenario | null = null;

function replanAgent(a: SimAgent, atNodeId?: string) {
  const here = atNodeId ?? a.toNodeId;
  const grp = DEFAULT_SCENARIO_LOCAL?.crowdGroups.find((g) => g.id === a.groupId);
  if (!grp) return;
  const path = shortestPath(here, grp.destinationNodeId);
  if (!path || path.length < 2) return;
  const e = edgeBetween(path[0], path[1]);
  if (!e) return;
  a.fromNodeId = path[0];
  a.toNodeId = path[1];
  a.edgeId = e.id;
  a.progress = 0;
  const from = NODE_MAP[path[0]];
  a.x = from.x;
  a.y = from.y;
}

// --- Edge flow / density --------------------------------------------------

function updateEdgeMetrics() {
  // reset
  for (const id in state.edges) {
    state.edges[id].flow = 0;
  }
  // count agents per edge
  const counts: Record<string, number> = {};
  for (const a of state.agents) {
    counts[a.edgeId] = (counts[a.edgeId] ?? 0) + 1;
  }
  for (const id in counts) {
    const e = state.edges[id];
    if (!e) continue;
    const cap = e.capacity;
    e.density = Math.min(1, counts[id] / Math.max(cap * 0.85, 30));
    e.flow = Math.round(counts[id] * 2);
    if (e.status === 'emergency-closed') continue;
    if (e.status === 'closed') continue;
    if (e.density > 0.8) e.status = 'congested';
    else if (e.density <= 0.7) e.status = 'open';
  }
}

// --- Metrics --------------------------------------------------------------

function computeMetrics(scenario: Scenario): CrowdMetrics {
  const active = state.agents.length;
  let totalDensity = 0;
  let n = 0;
  for (const id in state.edges) {
    const e = state.edges[id];
    if (e.status === 'closed' || e.status === 'emergency-closed') continue;
    totalDensity += e.density;
    n++;
  }
  const avgDensity = n ? totalDensity / n : 0;
  const flowRate = Math.round(
    Object.values(state.edges).reduce((s, e) => s + e.flow, 0),
  );
  const avgSpeed = active
    ? state.agents.reduce((s, a) => s + Math.hypot(a.vx, a.vy), 0) / active * 20
    : 0;
  // queue growth — derivative of active count (approximated)
  const queueGrowth = active > 0 ? Math.max(0, (active - state.totalExited) * 0.02) : 0;
  const capUtil = Math.min(1, active / 16000);
  const queueLengths: Record<string, number> = {};
  for (const g of scenario.entryDistribution) {
    queueLengths[g.gateId] = Math.round(
      state.agents.filter((a) => a.fromNodeId === g.gateId).length * 0.3,
    );
  }
  return {
    peopleCount: active,
    avgDensity,
    flowRate,
    avgSpeed,
    queueGrowth,
    capacityUtilization: capUtil,
    queueLengths,
  };
}

// --- Safety ---------------------------------------------------------------

function computeSafety(metrics: CrowdMetrics): SafetyState {
  const bottlenecks: Bottleneck[] = [];
  for (const id in state.edges) {
    const e = state.edges[id];
    if (e.status === 'closed' || e.status === 'emergency-closed') continue;
    if (e.density > 0.7) {
      const risk: RiskLevel = e.density > 0.9 ? 'critical'
        : e.density > 0.8 ? 'high' : 'moderate';
      const nodeLabel = NODE_MAP[e.to].label;
      const ttc = e.density > 0.85
        ? Math.max(1, Math.round((1 - e.density) * 60))
        : null;
      bottlenecks.push({
        id: `bn-${e.id}`,
        edgeId: e.id,
        nodeLabel,
        location: nodeLabel,
        currentDensity: e.density,
        capacityUtilization: e.density,
        risk,
        timeToCriticalMin: ttc,
        predictedEscalation: e.density > 0.78 && e.density < 0.9,
        recommendedAction: findRedirect(e.id),
        redirectToEdgeId: findRedirectEdge(e.id),
      });
    }
  }
  bottlenecks.sort((a, b) => b.currentDensity - a.currentDensity);

  const predicted: Bottleneck[] = bottlenecks
    .filter((b) => b.predictedEscalation)
    .slice(0, 3)
    .map((b) => ({ ...b, id: `pred-${b.id}` }));

  const reliefEdgesFlow = Object.values(state.edges)
    .filter((e) => ['exit-se', 'exit-sw', 'exit-n'].includes(e.to) && e.flow > 0)
    .reduce((acc, e) => acc + e.flow, 0);

  const baseRisk = bottlenecks.length > 0
    ? Math.round((bottlenecks[0].currentDensity * 0.45 + metrics.avgDensity * 0.35 + Math.min(1, metrics.capacityUtilization * 2.5) * 0.2) * 100)
    : Math.round(metrics.avgDensity * 100);

  const reliefDiscount = Math.min(35, Math.round(reliefEdgesFlow * 0.05 + (state.disabledEdges.size > 0 ? 20 : 0)));
  const riskScore = Math.min(100, Math.max(5, baseRisk - reliefDiscount));
  const riskLevel: RiskLevel = state.emergency?.active && state.disabledEdges.size === 0 ? 'emergency'
    : riskScore >= 80 ? 'critical'
    : riskScore >= 55 ? 'high'
    : riskScore >= 30 ? 'moderate'
    : 'low';

  const ttc = bottlenecks.find((b) => b.timeToCriticalMin != null)?.timeToCriticalMin ?? null;

  const alerts: SafetyAlert[] = [];
  for (const b of bottlenecks.slice(0, 3)) {
    const key = `alert-${b.edgeId}`;
    if (!state.acknowledgedAlerts.has(key)) {
      alerts.push({
        id: key,
        severity: b.risk,
        title: `Bottleneck: ${b.location}`,
        message: `${b.location} at ${Math.round(b.capacityUtilization * 100)}% capacity. ${b.recommendedAction}`,
        atMinute: state.simTimeMin,
        acknowledged: false,
      });
    }
  }
  if (state.emergency?.active) {
    alerts.unshift({
      id: `alert-em-${state.emergency.id}`,
      severity: 'emergency',
      title: `EMERGENCY: ${state.emergency.location}`,
      message: state.emergency.summary,
      atMinute: state.emergency.atMinute,
      acknowledged: false,
    });
  }

  return {
    riskScore, riskLevel, bottlenecks: bottlenecks.slice(0, 6),
    predictedBottlenecks: predicted, timeToCriticalMin: ttc, alerts,
  };
}

function findRedirect(edgeId: string): string {
  const e = state.edges[edgeId];
  if (!e) return 'Monitor and prepare to redirect flow.';
  // find a parallel-ish alternative edge from the same from-node
  const alt = STADIUM_A.edges.find(
    (x) => x.id !== edgeId && x.from === e.from && x.status === 'open' && x.density < 0.5,
  );
  return alt
    ? `Redirect incoming crowd toward ${NODE_MAP[alt.to].label}.`
    : 'Monitor and prepare to redirect flow.';
}

function findRedirectEdge(edgeId: string): string | undefined {
  const e = state.edges[edgeId];
  if (!e) return undefined;
  const alt = STADIUM_A.edges.find(
    (x) => x.id !== edgeId && x.from === e.from && x.status === 'open' && x.density < 0.5,
  );
  return alt?.id;
}

// --- AI analyst -----------------------------------------------------------

function maybeGenerateAI(safety: SafetyState, metrics: CrowdMetrics): AIState {
  let stage: AIRecommendation | null = null;
  // generate every 30 sim-minutes or on emergency
  const shouldGenerate =
    state.emergency?.active ||
    safety.bottlenecks.some((b) => b.risk === 'critical' || b.risk === 'high') ||
    (state.simTimeMin - state.lastAiMinute >= 30);

  if (shouldGenerate && state.simTimeMin - state.lastAiMinute >= 5) {
    state.lastAiMinute = state.simTimeMin;
    stage = generateRecommendation(safety, metrics);
    state.aiHistory.unshift(stage);
    if (state.aiHistory.length > 8) state.aiHistory.length = 8;
    pushTimeline('ai-recommendation', 'AI Safety analysis updated',
      stage.headline, stage.riskLevel);
  }

  return {
    scenario: {
      rawText: '',
      stage: 'idle',
      extracted: null,
      notes: [],
    },
    analyst: {
      stage: 'complete',
      current: stage ?? state.aiHistory[0] ?? null,
      history: state.aiHistory,
    },
  };
}

function generateRecommendation(safety: SafetyState, metrics: CrowdMetrics): AIRecommendation {
  if (state.emergency?.active) {
    return {
      id: `ai-${Date.now()}`,
      atMinute: state.simTimeMin,
      riskLevel: 'emergency',
      headline: `Emergency at ${state.emergency.location} — evacuation in progress`,
      explanation: `${state.emergency.summary} Affected routes have been disabled and alternative paths calculated. Crowd redistribution is active. Current active population is ${metrics.peopleCount.toLocaleString()}.`,
      recommendedAction: `Direct all crowd flow away from ${state.emergency.location}. Prioritize ${NODE_MAP['exit-n'].label}, ${NODE_MAP['exit-sw'].label}, and ${NODE_MAP['exit-se'].label}. Monitor density at alternative corridors for secondary bottlenecks.`,
      confidence: 'high',
      basis: 'Active emergency event, disabled routes, and current crowd distribution.',
    };
  }
  const bn = safety.bottlenecks[0];
  if (bn) {
    const pct = Math.round(bn.capacityUtilization * 100);
    return {
      id: `ai-${Date.now()}`,
      atMinute: state.simTimeMin,
      riskLevel: bn.risk,
      headline: `${bn.risk === 'critical' ? 'Critical' : 'High'} congestion detected at ${bn.location}`,
      explanation: `${bn.location} is currently operating at ${pct}% of its capacity. Continued inflow is expected to increase queue formation and reduce crowd movement speed. Current average flow rate is ${metrics.flowRate} people/min.`,
      recommendedAction: bn.recommendedAction + (bn.timeToCriticalMin
        ? ` Estimated time to critical conditions: ${formatMin(bn.timeToCriticalMin)}.`
        : ''),
      confidence: bn.risk === 'critical' ? 'high' : 'medium',
      basis: `Bottleneck detection on ${bn.location}, density ${pct}%, risk score ${safety.riskScore}/100.`,
    };
  }
  return {
    id: `ai-${Date.now()}`,
    atMinute: state.simTimeMin,
    riskLevel: safety.riskLevel,
    headline: 'Crowd conditions are within normal parameters',
    explanation: `All monitored corridors are operating below capacity. Current population is ${metrics.peopleCount.toLocaleString()} with an average density of ${Math.round(metrics.avgDensity * 100)}%. No bottlenecks detected.`,
    recommendedAction: 'Continue routine monitoring. No intervention required at this time.',
    confidence: 'high',
    basis: 'All edge densities below threshold. No bottlenecks detected.',
  };
}

// --- AI scenario interpretation (called from service) ---------------------

export function interpretScenarioText(text: string): {
  extracted: Partial<Scenario>; notes: string[];
} {
  const lower = text.toLowerCase();
  const extracted: Partial<Scenario> = {};
  const notes: string[] = [];
  const missingFields: string[] = [];
  const unresolvedLocations: string[] = [];
  const provenance: Record<string, string> = {};
  const incidents: Scenario['incidents'] = [];

  // crowd size
  const sizeMatch = text.match(/([\d,]+)\s*(?:people|attendees|persons|visitors|crowd|spectators)/i);
  if (sizeMatch) {
    extracted.crowdSize = parseInt(sizeMatch[1].replace(/,/g, ''), 10);
    extracted.crowdSizeOrigin = 'explicit';
    provenance.crowdSize = 'explicit';
    notes.push(`Explicit crowd size: ${extracted.crowdSize?.toLocaleString()}`);
  } else {
    extracted.crowdSize = 20000;
    extracted.crowdSizeOrigin = 'default';
    provenance.crowdSize = 'default';
    missingFields.push('crowd_size');
    notes.push('Crowd size not specified — defaulted to 20,000');
  }

  // time
  const timeMatch = text.match(/(\d{1,2}(?::\d{2})?)\s*(am|pm)\b/i);
  if (timeMatch) {
    const rawTime = timeMatch[1];
    const isPm = timeMatch[2].toLowerCase() === 'pm';
    let h = 0, m = 0;
    if (rawTime.includes(':')) {
      const parts = rawTime.split(':');
      h = parseInt(parts[0], 10);
      m = parseInt(parts[1], 10);
    } else {
      h = parseInt(rawTime, 10);
    }
    if (isPm && h < 12) h += 12;
    if (!isPm && h === 12) h = 0;
    extracted.timing = {
      startMinutesOfDay: h * 60 + m,
      durationMin: 180,
      arrivalPattern: 'surge',
      departurePattern: 'surge',
    };
    extracted.timingOrigin = 'explicit';
    provenance.timing = 'explicit';
    notes.push(`Event start: ${formatClock(h * 60 + m)}`);
  } else {
    extracted.timing = {
      startMinutesOfDay: 1140, // 19:00
      durationMin: 180,
      arrivalPattern: 'surge',
      departurePattern: 'surge',
    };
    extracted.timingOrigin = 'default';
    provenance.timing = 'default';
    missingFields.push('event_start_time');
    notes.push('Event start time not specified — defaulted to 19:00');
  }

  // gate distribution
  if (/east\s*gate/i.test(lower) && /west\s*gate/i.test(lower)) {
    extracted.entryDistribution = [
      { gateId: 'gate-e', fraction: 0.55 },
      { gateId: 'gate-w', fraction: 0.30 },
      { gateId: 'gate-s', fraction: 0.15 },
    ];
    extracted.entryDistributionOrigin = 'explicit';
    provenance.entryDistribution = 'explicit';
    notes.push('Primary entries: East & West Gates');
  } else if (/east\s*gate/i.test(lower)) {
    extracted.entryDistribution = [
      { gateId: 'gate-e', fraction: 0.60 },
      { gateId: 'gate-w', fraction: 0.25 },
      { gateId: 'gate-s', fraction: 0.15 },
    ];
    extracted.entryDistributionOrigin = 'explicit';
    provenance.entryDistribution = 'explicit';
    notes.push('Primary entry: East Gate (60%)');
  } else if (/west\s*gate/i.test(lower)) {
    extracted.entryDistribution = [
      { gateId: 'gate-w', fraction: 0.60 },
      { gateId: 'gate-e', fraction: 0.25 },
      { gateId: 'gate-s', fraction: 0.15 },
    ];
    extracted.entryDistributionOrigin = 'explicit';
    provenance.entryDistribution = 'explicit';
    notes.push('Primary entry: West Gate (60%)');
  } else {
    extracted.entryDistribution = [
      { gateId: 'gate-e', fraction: 0.55 },
      { gateId: 'gate-w', fraction: 0.30 },
      { gateId: 'gate-s', fraction: 0.15 },
    ];
    extracted.entryDistributionOrigin = 'default';
    provenance.entryDistribution = 'default';
    missingFields.push('entry_distribution');
    notes.push('Gate distribution not specified — balanced default applied');
  }

  // event type
  if (/music\s*festival|festival/i.test(lower)) {
    extracted.name = 'Music Festival';
    notes.push('Event type: Music Festival');
  } else if (/concert|gig|show|performance/i.test(lower)) {
    extracted.name = 'Concert';
    notes.push('Event type: Concert');
  } else if (/sport|match|game|tournament/i.test(lower)) {
    extracted.name = 'Sporting Event';
    notes.push('Event type: Sporting Event');
  }

  // Incidents
  let incCount = 1;
  // Medical collapse
  if (/\b(?:collapse|collapsed|collapses|medical\s+(?:emergency|assistance|incident))\b/i.test(lower)) {
    incidents.push({
      id: `inc-${incCount++}`,
      type: 'medical',
      description: 'Attendee collapsed near front stage requesting medical assistance',
      reported_location: 'front stage',
      resolved_node_id: 'stage',
      resolved_edge_id: null,
      severity: 'emergency',
      source: 'security',
      verification_status: 'reported',
      operational_constraints: ['medical_access_required', 'corridor_priority'],
      recommended_response: 'Dispatch medical response team to Main Stage',
      current_status: 'active',
    });
    notes.push('Preserved Medical Emergency near front stage');
  }

  // Camera density observation
  if (/\b(?:increasing\s+crowd\s+density|high\s+density|density\s+surge|camera\s+observations?)\b/i.test(lower)) {
    incidents.push({
      id: `inc-${incCount++}`,
      type: 'observation',
      description: 'Camera observations show increasing crowd density near front stage',
      reported_location: 'front stage',
      resolved_node_id: 'stage',
      resolved_edge_id: null,
      severity: 'high',
      source: 'camera_observation',
      verification_status: 'observed',
      operational_constraints: ['density_monitoring'],
      recommended_response: 'Monitor front-stage density and prepare crowd diversion',
      current_status: 'active',
    });
    notes.push('Preserved Camera Density Observation at front stage');
  }

  // Restricted corridor
  if (/\b(?:restricted\s+movement|restricted\s+corridor|medical\s+access\s+corridor)\b/i.test(lower)) {
    incidents.push({
      id: `inc-${incCount++}`,
      type: 'restricted-corridor',
      description: 'Restricted movement along medical access corridor',
      reported_location: 'medical access corridor',
      resolved_node_id: null,
      resolved_edge_id: 'e-stage-medical',
      severity: 'moderate',
      source: 'camera_observation',
      verification_status: 'observed',
      operational_constraints: ['restricted_movement', 'capacity_reduced'],
      recommended_response: 'Keep medical access corridor clear of general flow',
      current_status: 'active',
    });
    notes.push('Preserved Restricted Corridor: Medical Access Corridor');
  }

  // Entrance congestion
  if (/\b(?:congestion\s+near\s+(?:the\s+)?main\s+entrance|moderate\s+congestion|entrance\s+congestion)\b/i.test(lower)) {
    incidents.push({
      id: `inc-${incCount++}`,
      type: 'congestion',
      description: 'Moderate congestion near main entrance',
      reported_location: 'main entrance',
      resolved_node_id: 'gate-e',
      resolved_edge_id: 'e-ge-je',
      severity: 'moderate',
      source: 'camera_observation',
      verification_status: 'observed',
      operational_constraints: ['congestion', 'queue_monitoring'],
      recommended_response: 'Meter main entrance inflow and advise West Gate entry',
      current_status: 'active',
    });
    notes.push('Preserved Main Entrance Congestion Observation');
  }

  extracted.incidents = incidents;
  extracted.missingFields = missingFields;
  extracted.unresolvedLocations = unresolvedLocations;
  extracted.parameterProvenance = provenance;

  return { extracted, notes };
}

// --- Helpers --------------------------------------------------------------

function formatMin(m: number): string {
  if (m == null) return '—';
  const mm = Math.round(m);
  return `${String(Math.floor(mm / 60)).padStart(2, '0')}:${String(mm % 60).padStart(2, '0')}`;
}

function formatClock(minOfDay: number): string {
  const m = ((minOfDay % 1440) + 1440) % 1440;
  return `${String(Math.floor(m / 60)).padStart(2, '0')}:${String(Math.round(m % 60)).padStart(2, '0')}`;
}

// --- Main tick ------------------------------------------------------------

export function tick(scenario: Scenario, dtSec: number): SimSnapshot {
  if (state.status !== 'running') {
    const idleMetrics: CrowdMetrics = {
      peopleCount: 0, avgDensity: 0, flowRate: 0, avgSpeed: 0,
      queueGrowth: 0, capacityUtilization: 0, queueLengths: {},
    };
    return snapshot(scenario, idleMetrics,
      { riskScore: 0, riskLevel: 'low', bottlenecks: [], predictedBottlenecks: [],
        timeToCriticalMin: null, alerts: [] },
      { activeRoutes: state.routes, alternativeRoutes: [], disabledEdges: [...state.disabledEdges], recentChanges: state.routeChanges },
      { scenario: { rawText: '', stage: 'idle', extracted: null, notes: [] },
        analyst: { stage: 'idle', current: null, history: state.aiHistory } });
  }
  DEFAULT_SCENARIO_LOCAL = scenario;
  state.simTimeMin += (dtSec / 60) * state.speed;
  // spawn
  spawnAgents(scenario, dtSec);
  // move
  moveAgents(dtSec);
  // edge metrics
  updateEdgeMetrics();
  // metrics
  const metrics = computeMetrics(scenario);
  // safety
  const safety = computeSafety(metrics);
  // routing state
  const routing: RoutingState = {
    activeRoutes: state.routes.filter((r) => r.status === 'active' || r.status === 'congested'),
    alternativeRoutes: state.routes.filter((r) => r.status === 'recommended'),
    disabledEdges: [...state.disabledEdges],
    recentChanges: state.routeChanges.slice(0, 5),
  };
  // update route flows
  for (const r of state.routes) {
    r.flow = r.segments.reduce((s, seg) => s + (state.edges[seg.edgeId]?.flow ?? 0), 0);
  }
  // AI
  const ai = maybeGenerateAI(safety, metrics);
  // event end?
  if (state.simTimeMin >= scenario.timing.durationMin) {
    state.status = 'completed';
    pushTimeline('simulation', 'Simulation completed',
      `Event concluded. ${state.totalExited.toLocaleString()} people exited.`);
  }
  return snapshot(scenario, metrics, safety, routing, ai);
}

function snapshot(
  _scenario: Scenario,
  metrics: CrowdMetrics,
  safety: SafetyState,
  routing: RoutingState,
  ai: AIState,
): SimSnapshot {
  return {
    simulation: {
      status: state.status,
      simTimeMin: state.simTimeMin,
      speedMultiplier: state.speed,
      agents: state.agents,
      totalActive: state.agents.length,
      totalEntered: state.totalEntered,
      totalExited: state.totalExited,
    },
    metrics,
    safety,
    routing,
    ai,
    emergency: state.emergency,
    timeline: state.timeline.slice(0, 30),
  };
}

export function acknowledgeAlert(id: string) {
  state.acknowledgedAlerts.add(id);
}

// expose live edges for the map renderer
export function getLiveEdges(): Record<string, VenueEdge> {
  return state.edges;
}

export function getLiveAgents(): SimAgent[] {
  return state.agents;
}

export function interveneSimulation(payload: {
  action: 'restrict' | 'open_bypass' | 'divert' | 'reopen' | 'clear';
  edgeId?: string;
  targetNodeId?: string;
  reason?: string;
}) {
  const { action, edgeId, targetNodeId, reason } = payload;
  const target = targetNodeId || 'exit-se';

  if (action === 'restrict') {
    if (edgeId) {
      state.disabledEdges.add(edgeId);
      if (state.edges[edgeId]) {
        state.edges[edgeId].status = 'congested';
      }
    }
  } else if (action === 'open_bypass') {
    if (edgeId) {
      state.disabledEdges.delete(edgeId);
      if (state.edges[edgeId]) {
        state.edges[edgeId].status = 'open';
      }
    }
  } else if (action === 'divert') {
    if (edgeId) {
      state.disabledEdges.add(edgeId);
    }
    // Divert a portion of agents to the target exit
    for (const a of state.agents) {
      if (a.edgeId === edgeId || a.id % 2 === 0) {
        const path = shortestPath(a.fromNodeId, target);
        if (path && path.length >= 2) {
          const e = edgeBetween(path[0], path[1]);
          if (e) {
            a.toNodeId = path[1];
            a.edgeId = e.id;
          }
        }
      }
    }
  } else if (action === 'reopen' || action === 'clear') {
    state.disabledEdges.clear();
    for (const id in state.edges) {
      state.edges[id].status = 'open';
    }
  }

  // Record in timeline
  state.timeline.unshift({
    id: `tl-int-${Date.now()}`,
    atMinute: state.simTimeMin,
    kind: 'route-change',
    title: `OPERATOR: ${action.toUpperCase()} ${edgeId ?? target}`,
    summary: reason || `Intervention applied: ${action} towards ${target}`,
    severity: action === 'restrict' ? 'high' : 'low',
  });
}

// format helpers exported for UI
export { formatMin, formatClock };

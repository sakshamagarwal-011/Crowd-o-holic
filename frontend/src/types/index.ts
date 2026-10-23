// ===========================================================================
// Domain type definitions — backend contract abstraction
// The UI consumes these typed models. Mock services conform to the same shape
// so swapping in a real backend requires no component-level changes.
// ===========================================================================

// --- Venue graph ----------------------------------------------------------

export type NodeKind =
  | 'entry'
  | 'exit'
  | 'junction'
  | 'facility'
  | 'stage'
  | 'medical'
  | 'food';

export interface VenueNode {
  id: string;
  label: string;
  kind: NodeKind;
  x: number; // canvas-space coords (0..1000 logical units)
  y: number;
  capacity: number;
  /** kind-specific label, e.g. "East Gate", "North Corridor Junction" */
  description?: string;
}

export interface VenueEdge {
  id: string;
  from: string; // node id
  to: string;   // node id
  width: number;       // walkway width in meters
  capacity: number;    // max people per minute
  length: number;      // meters
  /** controlled traversal cost — lower is preferred by the router */
  cost: number;
  status: 'open' | 'congested' | 'closed' | 'emergency-closed' | 'recommended';
  flow: number;        // current people/min (0..capacity)
  density: number;     // 0..1 fraction of capacity
}

export interface Venue {
  id: string;
  name: string;
  width: number;  // logical width
  height: number; // logical height
  nodes: VenueNode[];
  edges: VenueEdge[];
}

// --- Scenario -------------------------------------------------------------

export interface EntryDistribution {
  gateId: string;
  fraction: number; // 0..1 share of total crowd
}

export interface CrowdGroup {
  id: string;
  name: string;
  size: number;
  entryGateId: string;
  destinationNodeId: string;
  arrivalStartMin: number; // minutes after event start
  arrivalEndMin: number;
}

export interface EventTiming {
  startMinutesOfDay: number; // e.g. 19*60 = 1140
  durationMin: number;
  arrivalPattern: 'gradual' | 'surge' | 'sustained' | 'peak-early';
  departurePattern: 'gradual' | 'surge' | 'sustained';
}

export interface SpecialCondition {
  id: string;
  type: 'gate-closure' | 'restricted-corridor' | 'obstruction'
      | 'emergency' | 'inflow-surge' | 'capacity-reduction';
  targetId: string; // node or edge id
  label: string;
  /** minutes after event start when the condition takes effect */
  atMinute: number;
}

export interface Incident {
  id: string;
  type: 'medical' | 'fire' | 'security' | 'structural' | 'crowd-crush' | 'gate-failure' | 'congestion' | 'restricted-corridor' | 'observation' | 'other';
  description: string;
  reported_location: string;
  resolved_node_id?: string | null;
  resolved_edge_id?: string | null;
  unresolved?: boolean;
  severity: RiskLevel;
  source: 'user_report' | 'camera_observation' | 'security' | 'staff' | 'sensor';
  verification_status: 'reported' | 'observed' | 'confirmed' | 'unverified';
  at_minute?: number;
  operational_constraints?: string[];
  recommended_response?: string;
  current_status: 'active' | 'pending' | 'resolved';
}

export interface Scenario {
  id: string;
  name: string;
  naturalLanguage?: string;
  venueId: string;
  crowdSize: number;
  crowdSizeOrigin?: 'explicit' | 'inferred' | 'default' | 'missing' | 'user_modified';
  entryDistribution: EntryDistribution[];
  entryDistributionOrigin?: 'explicit' | 'inferred' | 'default' | 'missing' | 'user_modified';
  crowdGroups: CrowdGroup[];
  timing: EventTiming;
  timingOrigin?: 'explicit' | 'inferred' | 'default' | 'missing' | 'user_modified';
  entryRate: number; // people per minute aggregate
  exitRate: number;
  specialConditions: SpecialCondition[];
  incidents?: Incident[];
  parameterProvenance?: Record<string, string>;
  missingFields?: string[];
  unresolvedLocations?: string[];
  clarifications?: string[];
}

// --- Simulation state -----------------------------------------------------

export type SimulationStatus = 'idle' | 'running' | 'paused' | 'completed' | 'error';

export interface SimAgent {
  id: number;
  x: number;
  y: number;
  vx: number;
  vy: number;
  groupId: string;
  // internal pathing state — not visualized directly
  fromNodeId: string;
  toNodeId: string;
  edgeId: string;
  progress: number; // 0..1 along current edge
  speed: number;
}

export interface SimulationState {
  status: SimulationStatus;
  simTimeMin: number;       // simulated minutes since event start
  speedMultiplier: number;
  agents: SimAgent[];
  totalActive: number;
  totalEntered: number;
  totalExited: number;
}

// --- Metrics --------------------------------------------------------------

export interface CrowdMetrics {
  peopleCount: number;
  avgDensity: number;       // 0..1
  flowRate: number;         // people/min aggregate
  avgSpeed: number;         // m/s
  queueGrowth: number;      // people/min (positive = growing)
  capacityUtilization: number; // 0..1
  queueLengths: Record<string, number>; // per-gate queue length
}

// --- Safety ---------------------------------------------------------------

export type RiskLevel = 'low' | 'moderate' | 'high' | 'critical' | 'emergency';

export interface Bottleneck {
  id: string;
  edgeId: string;
  nodeLabel: string;
  location: string;
  currentDensity: number;      // 0..1
  capacityUtilization: number; // 0..1
  risk: RiskLevel;
  timeToCriticalMin: number | null; // null when not applicable
  predictedEscalation: boolean;
  recommendedAction: string;
  redirectToEdgeId?: string;
}

export interface SafetyState {
  riskScore: number;       // 0..100
  riskLevel: RiskLevel;
  bottlenecks: Bottleneck[];
  predictedBottlenecks: Bottleneck[];
  timeToCriticalMin: number | null;
  alerts: SafetyAlert[];
}

export interface SafetyAlert {
  id: string;
  severity: RiskLevel;
  title: string;
  message: string;
  atMinute: number;
  acknowledged: boolean;
}

// --- Routing --------------------------------------------------------------

export interface RouteSegment {
  edgeId: string;
  fromNodeId: string;
  toNodeId: string;
}

export interface Route {
  id: string;
  fromNodeId: string;
  toNodeId: string;
  segments: RouteSegment[];
  status: 'active' | 'congested' | 'alternative' | 'disabled' | 'recommended';
  cost: number;
  flow: number;
  label: string;
}

export interface RouteChange {
  id: string;
  atMinute: number;
  reason: string;
  fromRouteId: string;
  toRouteId: string;
  affectedEdgeId: string;
  redistributedFlow: number;
}

export interface RoutingState {
  activeRoutes: Route[];
  alternativeRoutes: Route[];
  disabledEdges: string[];
  recentChanges: RouteChange[];
}

// --- AI -------------------------------------------------------------------

export type AIProcessingStage =
  | 'idle' | 'understanding' | 'extracting' | 'validating' | 'ready' | 'analyzing' | 'complete';

export interface AIScenarioInterpretation {
  rawText: string;
  stage: AIProcessingStage;
  extracted: Partial<Scenario> | null;
  notes: string[];
}

export interface AIRecommendation {
  id: string;
  atMinute: number;
  riskLevel: RiskLevel;
  headline: string;
  explanation: string;
  recommendedAction: string;
  confidence: 'low' | 'medium' | 'high';
  basis: string; // what simulation data this is based on
}

export interface AIState {
  scenario: AIScenarioInterpretation;
  analyst: {
    stage: AIProcessingStage;
    current: AIRecommendation | null;
    history: AIRecommendation[];
  };
}

// --- Emergency ------------------------------------------------------------

export interface EmergencyEvent {
  id: string;
  type: 'fire' | 'medical' | 'structural' | 'security' | 'crowd-crush' | 'gate-failure';
  location: string;
  nodeId: string;
  atMinute: number;
  active: boolean;
  closedEdgeIds: string[];
  summary: string;
}

// --- Timeline / history ---------------------------------------------------

export type TimelineEntryKind =
  | 'simulation' | 'bottleneck' | 'route-change' | 'emergency'
  | 'ai-recommendation' | 'alert' | 'scenario';

export interface TimelineEntry {
  id: string;
  atMinute: number;
  kind: TimelineEntryKind;
  title: string;
  detail: string;
  severity?: RiskLevel;
}

// --- Connection -----------------------------------------------------------

export type ConnectionState = 'connecting' | 'live' | 'reconnecting' | 'offline';

// --- Aggregated snapshot (what the realtime layer delivers each tick) -----

export interface SimSnapshot {
  simulation: SimulationState;
  metrics: CrowdMetrics;
  safety: SafetyState;
  routing: RoutingState;
  ai: AIState;
  emergency: EmergencyEvent | null;
  timeline: TimelineEntry[];
  incidents?: Incident[];
}

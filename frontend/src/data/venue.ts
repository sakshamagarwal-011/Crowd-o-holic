import type {
  Venue, VenueNode, VenueEdge, Scenario,
} from '@/types';

// ===========================================================================
// Venue graph — "Stadium A"
// A realistic mid-size stadium layout with entry gates, exits, junctions,
// food court, medical station, and a main stage. Coordinates are in a
// 1000×620 logical canvas space.
// ===========================================================================

const NODES: VenueNode[] = [
  // --- Entry gates (west & east) ---
  { id: 'gate-w',  label: 'West Gate',  kind: 'entry', x: 60,   y: 310, capacity: 1200, description: 'Primary west entrance' },
  { id: 'gate-e',  label: 'East Gate',  kind: 'entry', x: 940,  y: 310, capacity: 1800, description: 'Primary east entrance — high volume' },
  { id: 'gate-s',  label: 'South Gate', kind: 'entry', x: 500,  y: 580, capacity: 800,  description: 'Secondary south entrance' },

  // --- Exit gates ---
  { id: 'exit-n',  label: 'North Exit', kind: 'exit',  x: 500,  y: 45,  capacity: 2000, description: 'Emergency evacuation exit' },
  { id: 'exit-sw', label: 'SW Exit',    kind: 'exit',  x: 110,  y: 540, capacity: 900,  description: 'South-west evacuation exit' },
  { id: 'exit-se', label: 'SE Exit',    kind: 'exit',  x: 890,  y: 540, capacity: 900,  description: 'South-east evacuation exit' },

  // --- Junctions ---
  { id: 'j-w',     label: 'West Junction',   kind: 'junction', x: 220, y: 310, capacity: 1500 },
  { id: 'j-e',     label: 'East Junction',   kind: 'junction', x: 780, y: 310, capacity: 1500 },
  { id: 'j-n',     label: 'North Junction',  kind: 'junction', x: 500, y: 180, capacity: 1800 },
  { id: 'j-s',     label: 'South Junction',  kind: 'junction', x: 500, y: 440, capacity: 1600 },
  { id: 'j-nw',    label: 'NW Corridor',     kind: 'junction', x: 330, y: 210, capacity: 1000, description: 'North-west corridor junction' },
  { id: 'j-ne',    label: 'NE Corridor',     kind: 'junction', x: 670, y: 210, capacity: 1000, description: 'North-east corridor junction' },
  { id: 'j-sw',    label: 'SW Corridor',     kind: 'junction', x: 330, y: 420, capacity: 1000, description: 'South-west corridor junction' },
  { id: 'j-se',    label: 'SE Corridor',     kind: 'junction', x: 670, y: 420, capacity: 1000, description: 'South-east corridor junction' },

  // --- Facilities ---
  { id: 'food-n',  label: 'North Food Court', kind: 'food',    x: 420, y: 110, capacity: 600, description: 'Food stalls — north corridor' },
  { id: 'food-s',  label: 'South Food Court', kind: 'food',    x: 580, y: 510, capacity: 600, description: 'Food stalls — south plaza' },
  { id: 'medical', label: 'Medical Station',  kind: 'medical', x: 500, y: 310, capacity: 200, description: 'First-aid & medical' },

  // --- Stage ---
  { id: 'stage',   label: 'Main Stage',       kind: 'stage',   x: 500, y: 260, capacity: 12000, description: 'Concert main stage' },
];

// helper to build an edge with derived capacity
function edge(
  id: string, from: string, to: string,
  width: number, length: number, cost: number,
): VenueEdge {
  const capacity = Math.round(width * length * 0.6);
  return { id, from, to, width, length, cost, capacity, status: 'open', flow: 0, density: 0 };
}

const EDGES: VenueEdge[] = [
  // entries → junctions
  edge('e-gw-jw',  'gate-w',  'j-w',   6, 160, 1.0),
  edge('e-ge-je',  'gate-e',  'j-e',   7, 160, 1.0),
  edge('e-gs-js',  'gate-s',  'j-s',   5, 140, 1.2),

  // junction ring
  edge('e-jw-jnw', 'j-w',  'j-nw', 4, 130, 1.1),
  edge('e-jw-jsw', 'j-w',  'j-sw', 4, 130, 1.1),
  edge('e-je-jne', 'j-e',  'j-ne', 4, 130, 1.1),
  edge('e-je-jse', 'j-e',  'j-se', 4, 130, 1.1),
  edge('e-jnw-jn', 'j-nw', 'j-n',  5, 180, 1.0),
  edge('e-jne-jn', 'j-ne', 'j-n',  5, 180, 1.0),
  edge('e-jsw-js', 'j-sw', 'j-s',  5, 180, 1.0),
  edge('e-jse-js', 'j-se', 'j-s',  5, 180, 1.0),

  // north corridor (the bottleneck-prone corridor)
  edge('e-jn-foodn', 'j-n',   'food-n', 3, 90,  1.3),
  edge('e-foodn-exitn', 'food-n','exit-n', 4, 80, 1.0),

  // central
  edge('e-jn-stage',  'j-n',   'stage',   6, 90,  0.8),
  edge('e-js-stage',  'j-s',   'stage',   6, 90,  0.8),
  edge('e-jw-stage',  'j-w',   'stage',   4, 180, 1.2),
  edge('e-je-stage',  'j-e',   'stage',   4, 180, 1.2),

  // medical
  edge('e-stage-medical', 'stage',  'medical', 3, 60, 1.5),

  // south food
  edge('e-js-foods',  'j-s',   'food-s',  3, 90,  1.3),

  // exits
  edge('e-jsw-exitsw', 'j-sw', 'exit-sw', 4, 160, 1.0),
  edge('e-jse-exitse', 'j-se', 'exit-se', 4, 160, 1.0),
  edge('e-foods-exitsw','food-s','exit-sw',3, 200, 1.2),
  edge('e-foods-exitse','food-s','exit-se',3, 200, 1.2),
];

export const STADIUM_A: Venue = {
  id: 'venue-stadium-a',
  name: 'Stadium A',
  width: 1000,
  height: 620,
  nodes: NODES,
  edges: EDGES,
};

export const NODE_MAP: Record<string, VenueNode> = Object.fromEntries(
  STADIUM_A.nodes.map((n) => [n.id, n]),
);

export const EDGE_MAP: Record<string, VenueEdge> = Object.fromEntries(
  STADIUM_A.edges.map((e) => [e.id, e]),
);

export function edgesFromNode(nodeId: string): VenueEdge[] {
  return STADIUM_A.edges.filter((e) => e.from === nodeId || e.to === nodeId);
}

export function neighborsOf(nodeId: string): string[] {
  return STADIUM_A.edges
    .filter((e) => e.status !== 'closed' && e.status !== 'emergency-closed')
    .filter((e) => e.from === nodeId || e.to === nodeId)
    .map((e) => (e.from === nodeId ? e.to : e.from));
}

// BFS shortest path (by edge cost) — used by the mock sim for agent pathing
export function shortestPath(fromId: string, toId: string): string[] | null {
  if (fromId === toId) return [fromId];
  const visited = new Set<string>([fromId]);
  const queue: { id: string; path: string[] }[] = [{ id: fromId, path: [fromId] }];
  while (queue.length) {
    const { id, path } = queue.shift()!;
    for (const nb of neighborsOf(id)) {
      if (visited.has(nb)) continue;
      const newPath = [...path, nb];
      if (nb === toId) return newPath;
      visited.add(nb);
      queue.push({ id: nb, path: newPath });
    }
  }
  return null;
}

export function edgeBetween(aId: string, bId: string): VenueEdge | undefined {
  return STADIUM_A.edges.find(
    (e) => (e.from === aId && e.to === bId) || (e.from === bId && e.to === aId),
  );
}

// ===========================================================================
// Default scenario
// ===========================================================================

export const DEFAULT_SCENARIO: Scenario = {
  id: 'scenario-default',
  name: 'Evening Concert',
  naturalLanguage:
    'A concert with 20,000 people starts at 7 PM. Most people enter through the east gate and food stalls are near the north corridor.',
  venueId: STADIUM_A.id,
  crowdSize: 20000,
  entryDistribution: [
    { gateId: 'gate-e', fraction: 0.55 },
    { gateId: 'gate-w', fraction: 0.30 },
    { gateId: 'gate-s', fraction: 0.15 },
  ],
  crowdGroups: [
    { id: 'g-front',  name: 'Front-of-stage crowd', size: 9000, entryGateId: 'gate-e', destinationNodeId: 'stage',  arrivalStartMin: -60, arrivalEndMin: 0 },
    { id: 'g-mid',    name: 'Mid-field crowd',      size: 7000, entryGateId: 'gate-e', destinationNodeId: 'stage',  arrivalStartMin: -45, arrivalEndMin: 10 },
    { id: 'g-west',   name: 'West-side crowd',      size: 2500, entryGateId: 'gate-w', destinationNodeId: 'stage',  arrivalStartMin: -50, arrivalEndMin: 5 },
    { id: 'g-food',   name: 'Food-court visitors',  size: 1500, entryGateId: 'gate-s', destinationNodeId: 'food-n', arrivalStartMin: -40, arrivalEndMin: 20 },
  ],
  timing: {
    startMinutesOfDay: 19 * 60, // 19:00
    durationMin: 180,
    arrivalPattern: 'surge',
    departurePattern: 'surge',
  },
  entryRate: 600,  // people per minute aggregate at peak
  exitRate: 800,
  specialConditions: [],
};

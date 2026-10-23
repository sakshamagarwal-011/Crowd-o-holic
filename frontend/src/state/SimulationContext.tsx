import type {
  Scenario, SimSnapshot, ConnectionState, AIProcessingStage,
  EmergencyEvent,
} from '@/types';
import {
  DEFAULT_SCENARIO, STADIUM_A,
} from '@/data/venue';
import {
  tick, resetSimulation, startSimulation, pauseSimulation,
  resumeSimulation, setSpeed, triggerEmergency, clearEmergency,
  interpretScenarioText, acknowledgeAlert, getLiveEdges, getLiveAgents,
} from '@/services/mockEngine';
import type { VenueEdge, SimAgent } from '@/types';
import {
  createContext, useContext, useEffect, useRef, useState, useCallback,
  type ReactNode,
} from 'react';
import {
  isBackendConfigured,
  createSimulationWebSocket,
  apiStart, apiPause, apiResume, apiReset, apiSetSpeed,
  apiTriggerEmergency, apiClearEmergency, apiParseScenario, apiApplyScenario,
  apiIntervene, apiGetMitigationPlan,
  type InterventionPayload, type MitigationPlanResponse,
} from '@/services/backendClient';

// ===========================================================================
// Central real-time state layer
// Two modes:
//   1. BACKEND mode: WebSocket to FastAPI backend (VITE_BACKEND_URL set)
//   2. MOCK mode:   Local rAF tick loop (fallback, development default)
//
// All components use the same API regardless of mode.
// Components never open their own connections.
// ===========================================================================

const SIMULATION_ID = 'default';

interface SimulationApi {
  // state
  snapshot: SimSnapshot | null;
  connection: ConnectionState;
  scenario: Scenario;
  liveEdges: Record<string, VenueEdge>;
  liveAgents: SimAgent[];

  // simulation controls
  start: () => void;
  pause: () => void;
  resume: () => void;
  reset: () => void;
  setSpeedMult: (m: number) => void;

  // scenario
  setScenario: (s: Scenario) => void;
  interpretScenario: (text: string) => void;
  applyExtractedScenario: () => void;
  aiStage: AIProcessingStage;
  aiNotes: string[];
  aiExtracted: Partial<Scenario> | null;

  // emergency & mitigation
  triggerEm: (type: EmergencyEvent['type'], nodeId: string) => void;
  clearEm: () => void;
  intervene: (payload: InterventionPayload) => Promise<void>;
  getMitigationPlan: (corridorFocus?: string) => Promise<MitigationPlanResponse | null>;
  activeRestrictions: string[];

  // alerts
  ackAlert: (id: string) => void;

  // map selection
  selectedNodeId: string | null;
  selectedEdgeId: string | null;
  selectNode: (id: string | null) => void;
  selectEdge: (id: string | null) => void;

  // map layer toggles
  layers: { crowd: boolean; density: boolean; bottlenecks: boolean; routes: boolean; heatmap: boolean };
  toggleLayer: (k: keyof SimulationApi['layers']) => void;
}

const Ctx = createContext<SimulationApi | null>(null);

const IDLE_SNAPSHOT_DELAY = 800;

export function SimulationProvider({ children }: { children: ReactNode }) {
  const [snapshot, setSnapshot] = useState<SimSnapshot | null>(null);
  const [connection, setConnection] = useState<ConnectionState>('connecting');
  const [scenario, setScenarioState] = useState<Scenario>(DEFAULT_SCENARIO);
  const [aiStage, setAiStage] = useState<AIProcessingStage>('idle');
  const [aiNotes, setAiNotes] = useState<string[]>([]);
  const [aiExtracted, setAiExtracted] = useState<Partial<Scenario> | null>(null);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(null);
  const [activeRestrictions, setActiveRestrictions] = useState<string[]>([]);
  const [layers, setLayers] = useState({
    crowd: true,
    density: false,
    bottlenecks: true,
    routes: true,
    heatmap: false,
  });

  const scenarioRef = useRef(scenario);
  scenarioRef.current = scenario;
  const lastTickRef = useRef(performance.now());

  // ── Backend WebSocket mode ────────────────────────────────────────────────
  useEffect(() => {
    if (!isBackendConfigured) return; // use mock mode instead

    const cleanup = createSimulationWebSocket(
      SIMULATION_ID,
      (msg) => {
        const { type, payload } = msg as { type: string; payload: unknown };
        if (type === 'simulation.updated' && payload) {
          setSnapshot(payload as SimSnapshot);
        } else if (type === 'connection.status') {
          const { status } = payload as { status: string };
          if (status === 'live') setConnection('live');
        }
      },
      // The socket client exposes an internal "error" state; present it as
      // the dashboard's supported offline state.
      (status) => setConnection(status === 'error' ? 'offline' : status),
    );

    return cleanup;
  }, []);

  // ── Mock tick loop mode (when no backend configured) ──────────────────────
  useEffect(() => {
    if (isBackendConfigured) return; // backend mode active

    const t = setTimeout(() => setConnection('live'), IDLE_SNAPSHOT_DELAY);
    return () => clearTimeout(t);
  }, []);

  useEffect(() => {
    if (isBackendConfigured) return; // backend mode active

    let raf = 0;
    const loop = (now: number) => {
      const dt = Math.min(0.1, (now - lastTickRef.current) / 1000);
      lastTickRef.current = now;
      const snap = tick(scenarioRef.current, dt);
      setSnapshot(snap);
      raf = requestAnimationFrame(loop);
    };
    raf = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(raf);
  }, []);

  // live edge/agent refs (read each render from engine or backend snapshot)
  const liveEdges = isBackendConfigured
    ? (((snapshot as unknown as { edges?: Record<string, VenueEdge> })?.edges ||
        (snapshot?.routing as unknown as { edges?: Record<string, VenueEdge> })?.edges) ?? getLiveEdges())
    : getLiveEdges();

  const liveAgents = isBackendConfigured ? (snapshot?.simulation?.agents ?? []) : getLiveAgents();

  // ── Controls — dual mode ──────────────────────────────────────────────────

  const start = useCallback(() => {
    if (isBackendConfigured) {
      apiStart(SIMULATION_ID).catch(console.error);
    } else {
      startSimulation();
    }
  }, []);

  const pause = useCallback(() => {
    if (isBackendConfigured) {
      apiPause(SIMULATION_ID).catch(console.error);
    } else {
      pauseSimulation();
    }
  }, []);

  const resume = useCallback(() => {
    if (isBackendConfigured) {
      apiResume(SIMULATION_ID).catch(console.error);
    } else {
      resumeSimulation();
    }
  }, []);

  const reset = useCallback(() => {
    if (isBackendConfigured) {
      apiReset(SIMULATION_ID).catch(console.error);
      setSnapshot(null);
    } else {
      resetSimulation();
      setSnapshot(null);
    }
  }, []);

  const setSpeedMult = useCallback((m: number) => {
    if (isBackendConfigured) {
      apiSetSpeed(SIMULATION_ID, m).catch(console.error);
    } else {
      setSpeed(m);
    }
  }, []);

  const setScenario = useCallback((s: Scenario) => {
    setScenarioState(s);
    if (isBackendConfigured) {
      apiApplyScenario(SIMULATION_ID, s as unknown as Record<string, unknown>).catch(console.error);
    } else {
      resetSimulation();
    }
  }, []);

  const applyExtractedScenario = useCallback(() => {
    if (!aiExtracted) return;
    setScenarioState((prev) => {
      const updated: Scenario = {
        ...prev,
        name: aiExtracted.name || prev.name,
        crowdSize: aiExtracted.crowdSize ?? prev.crowdSize,
        crowdSizeOrigin: aiExtracted.crowdSizeOrigin || prev.crowdSizeOrigin,
        entryDistribution: aiExtracted.entryDistribution || prev.entryDistribution,
        entryDistributionOrigin: aiExtracted.entryDistributionOrigin || prev.entryDistributionOrigin,
        timing: aiExtracted.timing || prev.timing,
        timingOrigin: aiExtracted.timingOrigin || prev.timingOrigin,
        crowdGroups: aiExtracted.crowdGroups || prev.crowdGroups,
        incidents: aiExtracted.incidents || prev.incidents || [],
        parameterProvenance: aiExtracted.parameterProvenance || prev.parameterProvenance,
        missingFields: aiExtracted.missingFields || prev.missingFields,
        unresolvedLocations: aiExtracted.unresolvedLocations || prev.unresolvedLocations,
        clarifications: aiExtracted.clarifications || prev.clarifications,
        naturalLanguage: aiExtracted.naturalLanguage || prev.naturalLanguage,
      };
      if (isBackendConfigured) {
        apiApplyScenario(SIMULATION_ID, updated as unknown as Record<string, unknown>).catch(console.error);
      } else {
        resetSimulation();
      }
      return updated;
    });
  }, [aiExtracted]);

  // ── AI scenario interpretation ────────────────────────────────────────────

  const interpretScenario = useCallback((text: string) => {
    setAiStage('understanding');

    if (isBackendConfigured) {
      // Real AI backend call — show pipeline stages while waiting
      setTimeout(() => setAiStage('extracting'), 400);
      setTimeout(() => setAiStage('validating'), 800);

      apiParseScenario(text)
        .then((result) => {
          if (result.success && result.parsed) {
            // Convert backend ParsedScenario to rich frontend Scenario
            const parsed = result.parsed as Record<string, unknown>;
            const extracted: Partial<Scenario> = {
              name: (parsed.name as string) || 'Event',
              crowdSize: parsed.crowdSize as number,
              crowdSizeOrigin: (parsed.crowdSize_origin as Scenario['crowdSizeOrigin']) || 'explicit',
              entryDistribution: parsed.entryDistribution as Scenario['entryDistribution'],
              entryDistributionOrigin: (parsed.entryDistribution_origin as Scenario['entryDistributionOrigin']) || 'default',
              timing: parsed.timing as Scenario['timing'],
              timingOrigin: (parsed.timing_origin as Scenario['timingOrigin']) || 'default',
              crowdGroups: parsed.crowdGroups as Scenario['crowdGroups'],
              incidents: (parsed.incidents as Scenario['incidents']) || [],
              parameterProvenance: (parsed.parameter_provenance as Record<string, string>) || {},
              missingFields: (parsed.missing_fields as string[]) || [],
              unresolvedLocations: (parsed.unresolved_locations as string[]) || [],
              clarifications: (parsed.clarifications as string[]) || [],
              naturalLanguage: text,
            };
            setAiExtracted(extracted);
            setAiNotes([`AI provider: ${result.provider}`, ...result.notes]);
            setAiStage('ready');
          } else {
            setAiStage('idle');
          }
        })
        .catch(() => {
          // Fallback to mock interpretation
          const { extracted, notes } = interpretScenarioText(text);
          setAiExtracted(extracted);
          setAiNotes(notes);
          setAiStage('ready');
        });
    } else {
      // Mock mode — local interpretation
      setTimeout(() => setAiStage('extracting'), 400);
      setTimeout(() => {
        const { extracted, notes } = interpretScenarioText(text);
        setAiExtracted(extracted);
        setAiNotes(notes);
        setAiStage('validating');
      }, 900);
      setTimeout(() => setAiStage('ready'), 1400);
    }
  }, []);

  // ── Emergency ─────────────────────────────────────────────────────────────

  const triggerEm = useCallback(
    (type: EmergencyEvent['type'], nodeId: string) => {
      if (isBackendConfigured) {
        apiTriggerEmergency(SIMULATION_ID, type, nodeId).catch(console.error);
      } else {
        triggerEmergency(type, nodeId);
      }
    },
    [],
  );

  const clearEm = useCallback(() => {
    if (isBackendConfigured) {
      apiClearEmergency(SIMULATION_ID).catch(console.error);
    } else {
      clearEmergency();
    }
  }, []);

  const intervene = useCallback(async (payload: InterventionPayload) => {
    if (isBackendConfigured) {
      try {
        const res = await apiIntervene(SIMULATION_ID, payload);
        if (res?.restricted_edges) {
          setActiveRestrictions(res.restricted_edges);
        }
        return;
      } catch (err) {
        console.warn('Backend intervene failed, falling back to local state:', err);
      }
    }
    // Local / fallback state handling
    if (payload.action === 'restrict' && payload.edgeId) {
      setActiveRestrictions((prev) => Array.from(new Set([...prev, payload.edgeId!])));
    } else if (payload.action === 'reopen' || payload.action === 'clear') {
      setActiveRestrictions([]);
    }
  }, []);

  const getMitigationPlan = useCallback(async (corridorFocus?: string): Promise<MitigationPlanResponse | null> => {
    if (isBackendConfigured) {
      try {
        const plan = await apiGetMitigationPlan(SIMULATION_ID, corridorFocus);
        if (plan?.restricted_edges) {
          setActiveRestrictions(plan.restricted_edges);
        }
        return plan;
      } catch (err) {
        console.warn('Backend mitigation API failed, using tactician fallback:', err);
      }
    }

    // Deterministic fallback plan
    const isEast = corridorFocus === 'east' || corridorFocus === 'gate-e' || corridorFocus === 'e-ge-je';
    return isEast ? {
      status: 'success',
      model: 'Tactician Engine (Local)',
      situation_assessment: 'Bhaari bheed East Gate (e-ge-je) se enter ho rahi hai, jisse East Junction (j-e) block ho raha hai.',
      tactical_strategy: 'East Gate inflow ko meter/restrict karein, aur public ko South-East Exit (exit-se) tatha North Exit (exit-n) bypass ki taraf divert karein.',
      actions: [
        {
          id: 'act-1',
          action_type: 'restrict',
          edge_id: 'e-ge-je',
          target_node_id: 'exit-se',
          title: 'Throttle / Meter East Gate Inflow (e-ge-je)',
          instruction: 'East Gate turnstiles ko 50% restrict karein taaki East Junction par crowd crush ka risk na bane.',
          expected_outcome: 'East corridor arrival flow 50% reduce hoga aur concourse queue control mein rahegi.',
        },
        {
          id: 'act-2',
          action_type: 'open_bypass',
          edge_id: 'e-ge-je',
          target_node_id: 'exit-se',
          title: 'Open South-East Exit Relief Bypass (exit-se)',
          instruction: 'SE Corridor (j-se) ke zariye South-East Exit (exit-se) khol kar 900 people/hour ko direct evacuate karein.',
          expected_outcome: 'East concourse se direct 900 log per hour evacuate ho kar bahar nikal jayenge.',
        },
        {
          id: 'act-3',
          action_type: 'divert',
          edge_id: 'e-ge-je',
          target_node_id: 'exit-n',
          title: 'Divert Stage-bound East Flow to North Exit (exit-n)',
          instruction: 'NE Corridor (j-ne -> j-n) ke through crowd ko North Exit (exit-n) bypass par reroute karein.',
          expected_outcome: '2,000/hr capacity North bypass open ho kar East-Stage corridor congestion khatam karega.',
        },
        {
          id: 'act-4',
          action_type: 'divert',
          edge_id: 'e-ge-je',
          target_node_id: 'gate-s',
          title: 'Divert Peripheral Flow to South Gate Plaza (gate-s)',
          instruction: 'Security stewards deploy karke peripheral public ko South Gate (gate-s) ki taraf guide karein.',
          expected_outcome: 'Southern boundary par crowd distribute ho kar primary bottleneck ko relief degi.',
        },
      ],
      restricted_edges: ['e-ge-je'],
    } : {
      status: 'success',
      model: 'Tactician Engine (Local)',
      situation_assessment: 'Corridor bottleneck detected approaching junction nodes.',
      tactical_strategy: 'Isolate congested approach corridor, close inflow, aur crowd ko North Exit bypass (exit-n) tatha South Gate ki taraf divert karein.',
      actions: [
        {
          id: 'act-1',
          action_type: 'restrict',
          edge_id: 'e-gw-jw',
          target_node_id: 'exit-n',
          title: 'Restrict Inflow on West Corridor (e-gw-jw)',
          instruction: 'Close corridor e-gw-jw to prevent further pedestrian queue compression into junction.',
          expected_outcome: 'Stops arrival surge and limits maximum corridor density.',
        },
        {
          id: 'act-2',
          action_type: 'open_bypass',
          edge_id: 'e-gw-jw',
          target_node_id: 'exit-n',
          title: 'Open North Exit Relief Bypass (exit-n)',
          instruction: 'Open auxiliary North Exit turnstiles (capacity 2,000/hr) and guide crowd through northern concourse.',
          expected_outcome: 'Relieves pressure by evacuating up to 2,000 people/hour.',
        },
        {
          id: 'act-3',
          action_type: 'divert',
          edge_id: 'e-gw-jw',
          target_node_id: 'exit-sw',
          title: 'Divert West Flow to South-West Exit (exit-sw)',
          instruction: 'Guide West concourse visitors towards South-West Exit (exit-sw).',
          expected_outcome: 'Disperses up to 900 people/hour through secondary southwest gate.',
        },
      ],
      restricted_edges: ['e-gw-jw'],
    };
  }, []);

  const ackAlert = useCallback((id: string) => {
    acknowledgeAlert(id);
  }, []);

  // ── Map selection ─────────────────────────────────────────────────────────

  const selectNode = useCallback((id: string | null) => {
    setSelectedNodeId(id);
    setSelectedEdgeId(null);
  }, []);

  const selectEdge = useCallback((id: string | null) => {
    setSelectedEdgeId(id);
    setSelectedNodeId(null);
  }, []);

  const toggleLayer = useCallback((k: keyof typeof layers) => {
    setLayers((prev) => ({ ...prev, [k]: !prev[k] }));
  }, []);

  const api: SimulationApi = {
    snapshot, connection, scenario, liveEdges, liveAgents,
    start, pause, resume, reset, setSpeedMult,
    setScenario, interpretScenario, applyExtractedScenario, aiStage, aiNotes, aiExtracted,
    triggerEm, clearEm, intervene, getMitigationPlan, activeRestrictions, ackAlert,
    selectedNodeId, selectedEdgeId, selectNode, selectEdge,
    layers, toggleLayer,
  };

  return <Ctx.Provider value={api}>{children}</Ctx.Provider>;
}

export function useSimulation(): SimulationApi {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error('useSimulation must be used within SimulationProvider');
  return ctx;
}

export { STADIUM_A };

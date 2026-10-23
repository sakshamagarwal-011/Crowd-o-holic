/**
 * Backend API client — all HTTP calls to the FastAPI backend.
 * Used by SimulationContext when VITE_BACKEND_URL is configured.
 */

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL as string | undefined;
const WS_URL = import.meta.env.VITE_WS_URL as string | undefined;

export const isBackendConfigured = Boolean(BACKEND_URL);

// ── REST helpers ──────────────────────────────────────────────────────────────

async function apiCall<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const res = await fetch(`${BACKEND_URL}${path}`, {
    headers: { 'Content-Type': 'application/json', ...opts.headers },
    ...opts,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${path} → ${res.status}: ${text}`);
  }
  return res.json();
}

// ── Simulation lifecycle ──────────────────────────────────────────────────────

export async function apiStart(simId: string): Promise<void> {
  await apiCall(`/api/simulations/${simId}/start`, { method: 'POST' });
}

export async function apiPause(simId: string): Promise<void> {
  await apiCall(`/api/simulations/${simId}/pause`, { method: 'POST' });
}

export async function apiResume(simId: string): Promise<void> {
  await apiCall(`/api/simulations/${simId}/resume`, { method: 'POST' });
}

export async function apiReset(simId: string): Promise<void> {
  await apiCall(`/api/simulations/${simId}/reset`, { method: 'POST' });
}

export async function apiApplyScenario(
  simId: string,
  scenario: Record<string, unknown>,
): Promise<void> {
  await apiCall(`/api/simulations/${simId}/scenario`, {
    method: 'POST',
    body: JSON.stringify({ scenario }),
  });
}

export async function apiSetSpeed(simId: string, multiplier: number): Promise<void> {
  await apiCall(`/api/simulations/${simId}/speed`, {
    method: 'POST',
    body: JSON.stringify({ multiplier }),
  });
}

// ── Emergency ─────────────────────────────────────────────────────────────────

export async function apiTriggerEmergency(
  simId: string,
  type: string,
  nodeId: string,
): Promise<void> {
  await apiCall(`/api/simulations/${simId}/emergency`, {
    method: 'POST',
    body: JSON.stringify({ type, node_id: nodeId }),
  });
}

export async function apiClearEmergency(simId: string): Promise<void> {
  await apiCall(`/api/simulations/${simId}/emergency`, { method: 'DELETE' });
}

export interface InterventionPayload {
  action: 'divert' | 'restrict' | 'close' | 'open_bypass' | 'open_exit' | 'reopen' | 'clear';
  edgeId?: string;
  nodeId?: string;
  targetNodeId?: string;
  reason?: string;
}

export interface MitigationAction {
  id: string;
  action_type: 'restrict' | 'close' | 'divert' | 'open_bypass' | 'meter' | 'reopen';
  edge_id?: string;
  node_id?: string;
  target_node_id?: string;
  title: string;
  instruction: string;
  expected_outcome: string;
}

export interface MitigationPlanResponse {
  status: string;
  model: string;
  situation_assessment: string;
  tactical_strategy: string;
  actions: MitigationAction[];
  restricted_edges: string[];
}

export async function apiIntervene(
  simId: string,
  payload: InterventionPayload,
): Promise<{ status: string; action: string; diverted_to: string; restricted_edges: string[]; disabled_edges?: string[] }> {
  return apiCall(`/api/simulations/${simId}/intervene`, {
    method: 'POST',
    body: JSON.stringify({
      action: payload.action,
      edge_id: payload.edgeId,
      node_id: payload.nodeId,
      target_node_id: payload.targetNodeId,
      reason: payload.reason,
    }),
  });
}

export async function apiGetMitigationPlan(simId: string, corridorFocus?: string): Promise<MitigationPlanResponse> {
  return apiCall<MitigationPlanResponse>(`/api/simulations/${simId}/mitigate-ai`, {
    method: 'POST',
    body: JSON.stringify({ corridor_focus: corridorFocus }),
  });
}


// ── AI Scenario Parsing ───────────────────────────────────────────────────────

export interface ParseResult {
  success: boolean;
  parsed: Record<string, unknown> | null;
  stage: string;
  notes: string[];
  error?: string;
  provider: string;
}

export async function apiParseScenario(text: string): Promise<ParseResult> {
  return apiCall<ParseResult>('/api/scenarios/parse', {
    method: 'POST',
    body: JSON.stringify({ text }),
  });
}

// ── TinyFish live intelligence (server-side credential) ─────────────────────

export interface IntelligenceSource {
  title: string;
  url: string;
  snippet: string;
  site_name: string;
}

export interface IntelligenceSearchResult {
  query: string;
  results: IntelligenceSource[];
  disclaimer: string;
}

export async function apiSearchIntelligence(query: string): Promise<IntelligenceSearchResult> {
  return apiCall<IntelligenceSearchResult>('/api/intelligence/search', {
    method: 'POST',
    body: JSON.stringify({ query }),
  });
}

// ── WebSocket connection ──────────────────────────────────────────────────────

export function createSimulationWebSocket(
  simId: string,
  onMessage: (data: unknown) => void,
  onStatus: (status: 'connecting' | 'live' | 'error') => void,
): () => void {
  const wsBase = WS_URL || BACKEND_URL?.replace(/^http/, 'ws') || '';
  const url = `${wsBase}/ws/simulations/${simId}`;

  let ws: WebSocket | null = null;
  let retryTimer: ReturnType<typeof setTimeout> | null = null;
  let closed = false;

  function connect() {
    if (closed) return;
    onStatus('connecting');
    ws = new WebSocket(url);

    ws.onopen = () => {
      onStatus('live');
    };

    ws.onmessage = (evt) => {
      try {
        const msg = JSON.parse(evt.data);
        onMessage(msg);
      } catch {
        // ignore malformed messages
      }
    };

    ws.onerror = () => {
      onStatus('error');
    };

    ws.onclose = () => {
      if (!closed) {
        onStatus('connecting');
        retryTimer = setTimeout(connect, 2000);
      }
    };
  }

  connect();

  // Return cleanup function
  return () => {
    closed = true;
    if (retryTimer) clearTimeout(retryTimer);
    ws?.close();
  };
}

export function sendWsMessage(ws: WebSocket | null, message: unknown): void {
  if (ws?.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify(message));
  }
}

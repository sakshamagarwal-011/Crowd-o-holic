# Crowd-O-Holic — Real-Time Crowd Flow Optimisation & Safety Dashboard

<p align="center">
  <img src="assets/crowd-flow-hero.png" alt="Crowd-O-Holic Operations Dashboard & Telemetry" width="100%" />
</p>

> **Crowd-O-Holic** is an enterprise-grade crowd-flow simulation, real-time telemetry, and operational safety dashboard. It empowers venue commanders and event operators to explore pedestrian dynamics across complex topologies, track corridor density fluctuations, anticipate bottlenecks before queues develop, simulate emergency contingencies, dispatch tactical crowd mitigation SOPs, and query live open-source incident intelligence via multi-provider LLMs.

**Project status:** Prototype / decision-support decision platform. Includes an interactive Stadium topology (`venue-stadium-a`), synthetic agent micro-physics, deterministic risk calculations, multi-provider AI assistants, and exportable executive pitch deck tooling.

---

## Contents

- [Overview](#overview)
- [Problem statement](#problem-statement)
- [Key capabilities](#key-capabilities)
- [How it works](#how-it-works)
- [Architecture](#architecture)
- [Technology stack](#technology-stack)
- [Repository structure](#repository-structure)
- [Requirements](#requirements)
- [Run locally](#run-locally)
  - [Option A: Frontend demo mode (no backend required)](#option-a-frontend-demo-mode-no-backend-required)
  - [Option B: Frontend with FastAPI backend](#option-b-frontend-with-fastapi-backend)
- [Environment configuration](#environment-configuration)
  - [Frontend environment](#frontend-frontendenv)
  - [Backend environment variables](#backend-environment-variables)
  - [AI Providers (Ollama, OpenRouter, Hugging Face)](#ai-provider-configuration)
  - [Live Situational Intelligence (TinyFish)](#live-public-source-intelligence-tinyfish)
- [Tactical Crowd Mitigation](#tactical-crowd-mitigation)
- [API reference](#api-reference)
- [WebSocket updates](#websocket-updates)
- [Simulation and safety concepts](#simulation-and-safety-concepts)
- [Tests and code quality](#tests-and-code-quality)
- [Deployment guide](#deployment-guide)
- [Troubleshooting](#troubleshooting)
- [Limitations and responsible use](#limitations-and-responsible-use)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

Crowd-O-Holic delivers a mission-critical command center experience featuring dual primary operational views: a dynamic vector **Venue Topology Map** and a high-density **Corridor Heatmap & Density Telemetry Matrix**. Supporting panels offer real-time operational controls, proactive crowd mitigations, live open-source situational intelligence, bottleneck forecasting, emergency containment exercises, alternative route calculations, and AI-assisted scenario interpretation.

The repository is organized into a clean, decoupled full-stack architecture:

1. **Frontend** (`frontend/`) — A modern React 18, TypeScript, and Vite single-page dashboard styled with custom command-center dark tokens. Includes both a client-side mock simulation engine for standalone deployment and a resilient WebSocket/REST client connecting to the backend.
2. **Backend** (`backend/`) — A high-performance Python FastAPI service housing a deterministic graph-based agent simulation engine, mathematical risk calculator, dynamic Dijkstra rerouting, natural-language entity resolver, tactical crowd mitigation engine, and multi-provider AI layer (Ollama local GPU, OpenRouter, Hugging Face Hub, and Mock).
3. **Visual Assets** (`assets/`) — High-resolution architecture graphics, diagrams, and dashboard hero captures.

## Problem statement

Large gathering venues — including athletic stadiums, music festivals, transport hubs, conventions, and metropolitan transit plazas — suffer from uneven crowd distribution and sudden surges. Chokepoints, gate malfunctions, medical crises, and restricted egress pathways can trigger stampedes or lethal crowd crush within minutes. Operations teams require immediate visibility into developing density anomalies, automated SOP recommendations, and actionable intelligence to divert pedestrian streams safely.

Crowd-O-Holic solves this by providing a unified **simulation-based decision-support cockpit** that models physical crowd dynamics, detects chokepoints, dispatches tactical mitigations, and integrates real-time web intelligence.

## Key capabilities

### 1. Operations Command Center & Dual-View Canvas
- **Live Map View:** Interactive canvas rendering nodes (gates, junctions, food courts, stages, medical stations, exits) and directional edges with moving agent micro-particles, active evacuation paths, and alternative bypasses.
- **Corridor Heatmap & Telemetry View:** Real-time density matrix detailing capacity utilization, occupant count, and surge fluctuation vectors (surging, easing, stable) across all venue corridors.
- **Corridor Categorization & Filtering:** Instant filtering across Entrance, Ring, Central, Connector, Facilities, Exit, and Emergency corridors.
- **Camera Context Wall:** Expandable multi-camera context drawer providing contextual video monitor previews alongside topological telemetry.

### 2. Proactive Tactical Crowd Mitigation
- **SOP Action Dispatch:** One-click deployment of standard operating procedures:
  - *Gate Metering:* Restrict entry corridor inflow by up to 50% to prevent concourse flooding.
  - *Stanchion & Barrier Deployment:* Enforce serpentine switchbacks to slow surge velocity.
  - *Directional Audio Guidance:* Broadcast high-decibel acoustic wayfinding toward low-density exits.
  - *Emergency Lane Clearance:* Isolate and clear medical corridors (`stage ↔ medical`) for first-responders.
  - *Dynamic Egress Routing:* Automatically re-route upstream pedestrian flow toward underutilized perimeter exits (`exit-se`, `exit-sw`, `exit-n`).
- **AI-Driven Mitigation Formulator:** Queries local or remote LLMs to analyze active bottleneck telemetry and output structured operational directives and crowd dispersal recommendations.

### 3. Multi-Provider AI Architecture
- **Flexible Provider Modes:** Configure `AI_PROVIDER_MODE` to `auto`, `ollama`, `openrouter`, `huggingface`, or `mock`.
- **Local GPU Acceleration (Ollama):** High-speed, private, offline inference utilizing local models such as `qwen2.5:3b`.
- **OpenRouter API Support:** Direct integration with state-of-the-art hosted models such as `openai/gpt-4o-mini`.
- **Hugging Face Inference:** Serverless cloud execution using Hugging Face endpoints.
- **Deterministic Mock Provider:** Built-in zero-dependency fallback ensuring offline demonstrations and continuous integration test pipelines pass reliably without API keys.
- **Venue Graph Natural Language Resolver (`app/graph/resolver.py`):** Translates freeform incident descriptions (e.g., *"heavy crush near the medical corridor"*, *"suspected fire at front stage"*) into validated graph elements without hallucinating invalid node identifiers.

### 4. Live Open-Source Situational Intelligence
- **TinyFish AI Web Integration:** Secure server-side search and content-fetching pipeline enabling operators to query live transit advisories, severe weather warnings, and local emergency bulletins without leaking credentials to client browsers.
- **Public-Source Verification:** Built-in disclaimer tags and clean source attribution preserving operational safety standards.

---

## How it works

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                             OPERATIONS USER                                 │
│          Configures Scenario  ·  Toggles Heatmap  ·  Triggers SOPs          │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                        ┌──────────────┴──────────────┐
                        ▼                             ▼
              [Frontend Mock Engine]         [FastAPI Backend]
                 (Local Browser)            REST API + WebSocket
                                                      │
         ┌────────────────────────────────────────────┴─────────────────────────────┐
         ▼                                            ▼                             ▼
   [Venue Graph]                             [Risk & Bottleneck Engine]      [AI Provider Layer]
- Nodes & Directional Edges                 - Density & Utilization %       - Ollama (Local GPU)
- Dynamic Dijkstra Router                   - Queue Growth (people/min)     - OpenRouter / HF
- Location NLP Resolver                     - Deterministic Risk Score      - TinyFish Intelligence
```

1. **Scenario Ingestion:** Operators enter scenario parameters or natural-language incident reports. The AI provider extracts structured parameters and resolves locations via the graph alias engine.
2. **Agent Physics & Queue Simulation:** Synthetic crowds enter via weighted gates and traverse target destinations based on dynamic shortest-path Dijkstra algorithms.
3. **Telemetry & Risk Evaluation:** The risk engine monitors corridor load, flags persistent chokepoints, and calculates composite risk levels (`low`, `moderate`, `high`, `critical`, `emergency`).
4. **Realtime Broadcast:** Snapshot deltas are streamed at 2.0 Hz over WebSockets directly to the React dashboard.
5. **Mitigation & Rerouting:** Operators trigger mitigation actions or simulated emergencies, dynamically restricting edges and forcing agents onto calculated alternative bypasses.

---

## Architecture

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Browser / Frontend                                │
│                     React 18 + TypeScript + Vite                            │
│                                                                             │
│  Operations Rail      Dual-View Canvas        Safety Desk                   │
│  ├── Run Controls     ├── Vector Venue Map    ├── Emergency Incident Desk   │
│  ├── Mode Switcher    ├── Corridor Heatmap    ├── Live Intelligence (TinyFish)│
│  ├── AI Scenario Desk ├── Agent Micro-Physics ├── Tactical Crowd Mitigation │
│  └── Layer Toggles    └── Camera Drawer       ├── Bottleneck Telemetry      │
│                                               └── Dynamic Route Alternative │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                      ┌────────────────┴────────────────┐
                      │                                 │
               Local Demo Mode                    Backend Mode
                mockEngine.ts                   REST + WebSockets
                                                        │
┌───────────────────────────────────────────────────────┴─────────────────────┐
│                             FastAPI Backend                                 │
│                                                                             │
│  API Routes               Simulation Engine        Deterministic Services   │
│  ├── /health              ├── State Manager        ├── Venue Graph & Nodes  │
│  ├── /api/venues          ├── Agent Particle Queue ├── Risk Threshold Engine│
│  ├── /api/scenarios       ├── Inflow Generator     ├── Bottleneck Detector  │
│  ├── /api/simulations     └── Movement Stepper     └── Dynamic Router       │
│  ├── /api/emergency                                                         │
│  │   └── /mitigate-ai                                                       │
│  ├── /api/intelligence    Multi-Provider AI Layer  WebSocket Broadcaster    │
│  │   ├── /search          ├── Ollama (qwen2.5:3b)  └── 2 Hz Live Telemetry  │
│  │   └── /fetch           ├── OpenRouter (GPT-4o)      Broadcaster          │
│  └── /ws/simulations      ├── Hugging Face Hub                              │
│                           └── Mock Fallback                                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Technology stack

| Domain | Technologies & Libraries |
|---|---|
| **Frontend Framework** | React 18, TypeScript, Vite 5 |
| **Styling & Icons** | Vanilla CSS Tokens, Tailwind CSS, Lucide React |
| **Backend Framework** | FastAPI (ASGI), Uvicorn |
| **Backend Language** | Python 3.11+ |
| **Validation & Settings** | Pydantic v2, Pydantic-Settings |
| **AI Providers** | Ollama (`qwen2.5:3b`), OpenRouter (`gpt-4o-mini`), Hugging Face Hub, Mock Provider |
| **Live Intelligence** | TinyFish Search & Fetch API Client |
| **Realtime Telemetry** | WebSockets (`websockets` / FastAPI WebSocket) |
| **Database & ORM** | SQLAlchemy 2.0, aiosqlite (SQLite-compatible persistence), Alembic |
| **Testing** | `pytest`, `pytest-asyncio`, `httpx` |

---

## Repository structure

```text
Crowd-O-Holic/
├── assets/                             # High-resolution architectural screenshots & hero media
│   └── crowd-flow-hero.png
├── frontend/                           # React 18 + Vite frontend application
│   ├── src/
│   │   ├── components/
│   │   │   ├── ai/                     # AIScenarioAssistant & AISafetyAnalyst
│   │   │   ├── analytics/              # CorridorHeatmapPanel & Density Telemetry
│   │   │   ├── emergency/              # EmergencyPanel & EmergencyBanner
│   │   │   ├── layout/                 # Header & ConnectionOverlay
│   │   │   ├── metrics/                # MetricsPanel & legacyDensity
│   │   │   ├── routing/                # RoutePanel & path alternative visualizers
│   │   │   ├── safety/                 # AlertPanel, BottleneckPanel, CrowdMitigationPanel,
│   │   │   │                           # LiveIntelligencePanel, Timeline
│   │   │   ├── scenario/               # ScenarioConfig & SimulationControls
│   │   │   └── venue/                  # VenueMap, CameraWall, Inspector, LayerToggles
│   │   ├── data/                       # Stadium A topology, nodes, edges, gates, exits
│   │   ├── services/
│   │   │   ├── backendClient.ts        # Typed HTTP/WebSocket communications
│   │   │   └── mockEngine.ts           # Browser-based deterministic simulation engine
│   │   ├── state/                      # SimulationContext & reducer state
│   │   ├── types/                      # TypeScript schemas (Venue, Agent, Risk, Metrics)
│   │   ├── utils/                      # Color ramps, formatters, and node inspectors
│   │   ├── App.tsx                     # Main layout & canvas switcher (Map vs Heatmap)
│   │   ├── index.css                   # Command-center dark design tokens
│   │   └── main.tsx
│   ├── .env.example
│   ├── package.json
│   └── vite.config.ts
│
├── backend/                            # FastAPI backend application
│   ├── app/
│   │   ├── ai/                         # Multi-provider LLM integrations
│   │   │   ├── huggingface_provider.py # Hugging Face serverless client
│   │   │   ├── mock_provider.py        # Offline zero-token deterministic mock
│   │   │   ├── ollama_provider.py      # Local GPU Ollama client (qwen2.5:3b)
│   │   │   ├── openrouter_provider.py  # OpenRouter cloud client
│   │   │   ├── prompts.py              # Structured prompt contracts
│   │   │   ├── provider.py             # Abstract base AIProvider class
│   │   │   └── schemas.py              # Pydantic schemas for parameter extraction
│   │   ├── api/
│   │   │   ├── routes/                 # Health, venues, scenarios, simulations,
│   │   │   │                           # emergency, intelligence endpoints
│   │   │   └── websocket.py            # Realtime snapshot WebSocket route
│   │   ├── core/                       # Settings, structured logging, exception handlers
│   │   ├── db/                         # Database models & SQLite session management
│   │   ├── emergency/                  # Emergency incident tracker
│   │   ├── graph/                      # VenueGraph, edge weights & NLP Location Resolver
│   │   ├── metrics/                    # Venue flow, density, throughput calculations
│   │   ├── realtime/                   # Broadcast loop & active WebSocket connections
│   │   ├── risk/                       # Thresholds, bottleneck detector, risk engine
│   │   ├── routing/                    # Dynamic Dijkstra shortest path algorithm
│   │   ├── seed/                       # Demo venue seed data (Stadium A)
│   │   ├── services/                   # Venue, simulation, AI, and TinyFish services
│   │   └── simulation/                 # Agent generator, queue physics, movement engine
│   ├── tests/                          # Automated backend test suites
│   ├── pyproject.toml
│   └── uv.lock
│
├── start-backend.bat                   # Convenient Windows launcher script
├── .gitignore
└── README.md
```


---

## Requirements

Install these before running the project:

- **Git** (for cloning/version control).
- **Node.js** with npm (a current LTS release is recommended).
- **Python 3.11 or newer**.
- A terminal such as PowerShell, Windows Terminal, macOS Terminal, or a Linux shell.
- Optional: a Hugging Face token if you want to use the configured hosted AI provider.

No NVIDIA GPU is required for the standard frontend demo or the deterministic backend simulation. The optional hosted AI provider uses a remote service rather than requiring a local GPU.

---

## Run locally

### 1. Get the source code

Clone your repository (replace the URL with your actual GitHub repository URL):

```bash
git clone https://github.com/<YOUR-USERNAME>/Crowd-O-Holic.git
cd Crowd-O-Holic
```

If you downloaded a ZIP instead, extract it and open the extracted project root in VS Code. The root should contain both `frontend/` and `backend/`.

### Option A: Frontend demo mode (no backend required)

This is the quickest way to open the dashboard. The frontend `.env.example` explicitly supports running with empty backend URLs, allowing local mock/simulation mode.

**Terminal 1 — install frontend dependencies**

```bash
cd frontend
npm install
```

Create a local `.env` file from the example if one does not already exist.

**Windows PowerShell:**

```powershell
Copy-Item .env.example .env
```

**macOS / Linux:**

```bash
cp .env.example .env
```

Keep these values empty for local mock mode:

```dotenv
VITE_BACKEND_URL=
VITE_WS_URL=
```

Start the development server:

```bash
npm run dev
```

Open the local URL printed by Vite, usually `http://localhost:5173`.

To create a production frontend build:

```bash
npm run build
```

To preview the built frontend locally:

```bash
npm run preview
```

### Option B: Frontend with FastAPI backend

Use this mode to run the server-side simulation and API.

#### 1. Start the backend

Open a terminal at the project root.

**Windows PowerShell:**

```powershell
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e .
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

If PowerShell blocks activation, you can avoid activation and call the environment's Python directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

**macOS / Linux:**

```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e .
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The backend should be available at:

- API root: `http://127.0.0.1:8000/`
- Health check: `http://127.0.0.1:8000/health`
- Interactive API docs: `http://127.0.0.1:8000/docs`
- WebSocket: `ws://127.0.0.1:8000/ws/simulations/default`

The app startup code prepares a default simulation for `venue-stadium-a`.

#### 2. Configure the frontend to use the backend

Open a **second terminal**:

```bash
cd frontend
npm install
```

Create or edit `frontend/.env`:

```dotenv
VITE_BACKEND_URL=http://127.0.0.1:8000
VITE_WS_URL=ws://127.0.0.1:8000
```

Then start the frontend:

```bash
npm run dev
```

Open the Vite URL, usually `http://localhost:5173`.

> Vite reads environment variables when its dev server starts. If you change `frontend/.env`, stop and restart `npm run dev`.

#### 3. Verify the backend

Open `http://127.0.0.1:8000/health`. A healthy response should resemble:

```json
{
  "status": "ok",
  "version": "0.1.0",
  "ai_mode": "mock"
}
```

The `ai_mode` value may differ if you configure another provider. You can also open `/docs` to inspect and try the available API routes.

---

## Environment configuration

### Frontend (`frontend/.env`)

| Variable | Purpose | Local example |
|---|---|---|
| `VITE_BACKEND_URL` | Base URL for the FastAPI HTTP API | `http://127.0.0.1:8000` |
| `VITE_WS_URL` | Base URL used to form WebSocket connections | `ws://127.0.0.1:8000` |

Leave both blank for the frontend-only mock mode, as described in `.env.example`.

Vite variables prefixed with `VITE_` are exposed to browser-side code. **Never put secrets or private API tokens in frontend environment variables.**

### Backend environment variables

The backend uses `pydantic-settings`. Settings may be provided through environment variables or a `.env` file loaded relative to the backend process's working directory.

| Variable | Default / example | Purpose |
|---|---|---|
| `APP_NAME` | `Crowd Flow Optimiser` | Application display name |
| `APP_VERSION` | `0.1.0` | API version |
| `DEBUG` | `false` | Debug setting |
| `LOG_LEVEL` | `INFO` | Logging level |
| `CORS_ORIGINS` | Localhost origins | Allowed browser origins; configure for your deployed frontend |
| `AI_PROVIDER_MODE` | `auto` | `auto`, `ollama`, `openrouter`, `huggingface`, or `mock` |
| `OLLAMA_BASE_URL` | `http://127.0.0.1:11434` | Ollama local instance URL for GPU inference |
| `OLLAMA_MODEL` | `qwen2.5:3b` | Local model name running in Ollama |
| `OPENROUTER_API_KEY` | empty | Server-only OpenRouter API key |
| `OPENROUTER_MODEL` | `openai/gpt-4o-mini` | OpenRouter model identifier |
| `HF_TOKEN` | empty | Optional Hugging Face access token |
| `HF_MODEL` | `Qwen/Qwen2.5-7B-Instruct` | Model identifier for Hugging Face provider |
| `AI_TIMEOUT` | `30.0` | AI request timeout in seconds |
| `TINYFISH_API_KEY` | empty | Optional server-only key for TinyFish live intelligence search |
| `TINYFISH_TIMEOUT` | `20.0` | Timeout in seconds for TinyFish requests |
| `TINYFISH_MAX_RESULTS` | `5` | Maximum search results returned by TinyFish |
| `AI_COOLDOWN_SIM_MINUTES` | `5.0` | Minimum simulation-time interval between AI calls |
| `SIMULATION_TIMESTEP` | `1.0` | Real-time seconds per simulation tick |
| `MAX_SIMULATION_DURATION` | `300.0` | Maximum configured simulation duration in minutes |
| `REALTIME_UPDATE_HZ` | `2.0` | Target WebSocket broadcast rate |
| `MAX_AGENTS_RENDERED` | `1400` | Frontend visual particle rendering cap |
| `DATABASE_URL` | `sqlite+aiosqlite:///./crowd_sim.db` | SQLite database connection string |
| `PERSISTENCE_FREQUENCY` | `10` | Summary persistence frequency in simulation ticks |

The backend also defines environment-configurable thresholds for risk density, utilisation, bottleneck detection, routing costs, and route stability in `backend/app/core/config.py`.

### AI Provider Configuration & Priority

The backend implements a flexible provider selector (`app/services/ai_service.py`):

1. **Auto Discovery (`AI_PROVIDER_MODE=auto`):**
   - Automatically probes local Ollama at `http://127.0.0.1:11434/api/tags`. If reachable, switches to GPU-accelerated local Ollama.
   - If Ollama is offline but `OPENROUTER_API_KEY` is present, switches to OpenRouter (`openai/gpt-4o-mini`).
   - If `HF_TOKEN` is present, switches to Hugging Face Hub.
   - Otherwise, safely falls back to `mock` mode with zero token cost.
2. **Local GPU Ollama Mode:**
   ```dotenv
   AI_PROVIDER_MODE=ollama
   OLLAMA_BASE_URL=http://127.0.0.1:11434
   OLLAMA_MODEL=qwen2.5:3b
   ```
3. **OpenRouter Mode:**
   ```dotenv
   AI_PROVIDER_MODE=openrouter
   OPENROUTER_API_KEY=your_key_here
   OPENROUTER_MODEL=openai/gpt-4o-mini
   ```
4. **Hugging Face Mode:**
   ```dotenv
   AI_PROVIDER_MODE=huggingface
   HF_TOKEN=your_token_here
   HF_MODEL=Qwen/Qwen2.5-7B-Instruct
   ```
5. **Deterministic Mock Mode:**
   ```dotenv
   AI_PROVIDER_MODE=mock
   ```

### Live Public-Source Intelligence (TinyFish)

The Safety Desk includes a dedicated **Live Intelligence** search panel powered by TinyFish AI for monitoring external context (transit disruptions, severe weather, crowd notices) during mass events:

```dotenv
TINYFISH_API_KEY=your_tinyfish_key_here
TINYFISH_TIMEOUT=20.0
TINYFISH_MAX_RESULTS=5
```

All requests route through `backend/app/api/routes/intelligence.py` so keys are never exposed to browser clients.

---

## Tactical Crowd Mitigation

The dashboard features an integrated **Tactical Crowd Mitigation Panel** (`CrowdMitigationPanel.tsx`) directly tied to the simulation engine and backend solver:

- **Targeted Corridor Focus:** Auto-focus on peak bottleneck or manually target sectors (`East Gate`, `West Corridor`, `North Food Concourse`).
- **Tactical Actions:**
  - *Gate Inflow Metering:* Restrict entry corridor capacity to 50% to prevent crush at internal security checkpoints.
  - *Stanchions & Switchbacks:* Apply speed-dampening flow restrictions on surging concourses.
  - *Directional Audio / PA Guidance:* Broadcast instructions guiding crowds toward designated high-capacity egress points (`exit-se`, `exit-sw`, `exit-n`).
  - *Clear Emergency Priority Lane:* Isolate `stage ↔ medical` corridor (`e-stage-medical`) exclusively for EMS carts.
- **AI-Generated Mitigation Directives (`POST /api/simulations/{id}/mitigate-ai`):** Prompts the active LLM to generate an immediate, multi-step incident response plan with estimated dispersal times.


---

## API reference

The interactive Swagger UI is served at `http://127.0.0.1:8000/docs`.

### Health & Venues

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | Service status, software version, and active AI mode |
| `GET` | `/` | API root metadata |
| `GET` | `/api/venues` | List venue definitions |
| `GET` | `/api/venues/{venue_id}` | Retrieve venue topology graph with nodes, coordinates, and capacities |

### Scenarios & AI Processing

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/api/scenarios/parse` | Natural-language scenario and incident parameter extractor |

### Simulations & Interventions

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/api/simulations` | Create a new simulation run |
| `GET` | `/api/simulations` | List active simulation IDs |
| `GET` | `/api/simulations/{id}` | Summary counters and state |
| `GET` | `/api/simulations/{id}/state` | Full state snapshot (agents, queues, metrics, safety) |
| `POST` | `/api/simulations/{id}/start` | Start or resume simulation loop |
| `POST` | `/api/simulations/{id}/pause` | Pause simulation loop |
| `POST` | `/api/simulations/{id}/resume` | Resume paused simulation |
| `POST` | `/api/simulations/{id}/stop` | Stop simulation |
| `POST` | `/api/simulations/{id}/reset` | Reset simulation state |
| `POST` | `/api/simulations/{id}/speed` | Update speed multiplier (`0.5x` to `5.0x`) |
| `POST` | `/api/simulations/{id}/mitigate-ai` | Generate AI-driven tactical crowd mitigation plan |

### Emergency & Intelligence

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/api/simulations/{id}/emergency` | Activate emergency at venue node (`fire`, `medical`, `security`, `crowd-crush`) |
| `DELETE` | `/api/simulations/{id}/emergency` | Clear active emergency state |
| `POST` | `/api/intelligence/search` | Search public-source intelligence via TinyFish AI |
| `POST` | `/api/intelligence/fetch` | Fetch sanitized full text of public advisories |


Example request:

```json
{
  "type": "fire",
  "node_id": "REPLACE_WITH_A_VALID_NODE_ID"
}
```

Use a node ID that exists in the selected venue graph. The supported emergency type strings documented in the backend route are `fire`, `medical`, `structural`, `security`, `crowd-crush`, and `gate-failure`.

### WebSocket

| Type | Endpoint | Purpose |
|---|---|---|
| WebSocket | `/ws/simulations/{simulation_id}` | Receives connection status and simulation update events; may also accept client control messages |

The WebSocket endpoint sends a connection event and an initial snapshot when a valid simulation connection is established. The `default` simulation ID has special handling for creating a default simulation if needed.

---

## WebSocket updates

Backend mode uses a WebSocket connection to stream simulation snapshots to the UI.

Local development URL:

```text
ws://127.0.0.1:8000/ws/simulations/default
```

For a deployed HTTPS site, the corresponding secure WebSocket scheme is normally `wss://`. Set the frontend's `VITE_WS_URL` to the backend's public base URL using the appropriate scheme, for example:

```dotenv
VITE_BACKEND_URL=https://your-backend.example.com
VITE_WS_URL=wss://your-backend.example.com
```

Replace the example hostname with the real backend URL. Ensure the hosting platform supports WebSockets and that its proxy/timeouts are configured appropriately.

---

## Simulation and safety concepts

The following concepts are implemented across the backend modules and configuration. Their output is intended for simulation and demonstration.

- **Venue graph:** Nodes and edges represent locations and connections through a venue.
- **Agents:** Synthetic entities represent people moving through the graph.
- **Queues and movement:** Simulation logic models movement and queuing at the venue level.
- **Density:** A crowding indicator used by the risk engine.
- **Utilisation:** A measure of how much of a configured capacity is being used.
- **Risk levels:** Configurable thresholds classify crowd conditions into severity levels.
- **Bottlenecks:** Detection considers density, utilisation, queue growth, and persistence across ticks.
- **Dynamic routing:** Candidate paths are evaluated using baseline, congestion, risk, and capacity weights.
- **Route stability:** Cooldown and minimum-improvement settings help avoid excessive route changes.
- **Emergency state:** A simulated incident can affect venue state and routing decisions.
- **Reproducibility:** Simulation creation accepts a seed, making repeatable scenarios possible when the underlying implementation remains deterministic.

Default backend risk thresholds include density values of `0.35`, `0.60`, `0.80`, and `0.90` for progressively more severe levels; utilisation thresholds include `0.50`, `0.70`, and `0.85`. These are configuration defaults for the prototype, **not validated public-safety standards**. Tune and validate all thresholds against appropriate domain expertise and venue-specific data before any real-world use.

---

## AI provider configuration

The backend defines an AI provider interface with mock and Hugging Face implementations.

### Mock mode

Mock mode is useful for local development, repeatable demos, and testing without external model credentials.

```dotenv
AI_PROVIDER_MODE=mock
```

### Hugging Face mode

To use the hosted provider:

1. Create or obtain a Hugging Face access token with the permissions required by the selected model/provider.
2. Store it in the backend environment as `HF_TOKEN`.
3. Set `HF_MODEL` if you want to use a different supported model identifier.
4. Configure `AI_PROVIDER_MODE=huggingface` or use `auto` to select the provider when a token is present.
5. Restart the backend and inspect its logs and `/health` response.

Do not place the token in `frontend/.env`, source code, screenshots, or a public repository. Hosted inference is subject to model availability, provider permissions, latency, and rate limits. The rest of the simulation should be tested independently of the AI provider.

## Live public-source intelligence (TinyFish)

The Safety Desk includes an optional **Live intelligence** panel for researching public transport, weather, event, or crowd-safety context. It uses TinyFish Search through the backend, so the TinyFish API key is never exposed in the browser.

1. Copy `backend/.env.example` to `backend/.env`.
2. Set `TINYFISH_API_KEY` in `backend/.env` using your own key.
3. Restart the backend and use the Live intelligence search box in the Safety Desk.

Search results are public-source context, not verified operational instructions. Confirm material information with venue operators and official agencies before acting on it. The backend returns a clear `503` status when the key has not been configured.

---

## Tests and code quality

Run backend tests from the `backend/` directory with the virtual environment activated:

```bash
pytest
```

For more verbose output:

```bash
pytest -v
```

The repository includes tests for API behaviour, simulation behaviour, graph logic, risk calculations, and AI provider behaviour. Test outcomes depend on the installed dependencies and the current source state.

Frontend checks are available from the `frontend/` directory:

```bash
npm run typecheck
npm run lint
npm run build
```

These commands respectively check TypeScript types, run ESLint, and create a production build. Resolve reported errors before deploying.

---

## Deployment guide

The application is split into a static frontend and a long-running API backend. They can be deployed separately.

### Frontend deployment

Suitable static hosting options include Netlify, Vercel, or another static host that supports Vite builds.

Typical settings:

- **Base directory:** `frontend`
- **Build command:** `npm run build`
- **Publish/output directory:** `dist`
- **Environment variables:**
  - `VITE_BACKEND_URL=https://YOUR-BACKEND-DOMAIN`
  - `VITE_WS_URL=wss://YOUR-BACKEND-DOMAIN`

If you intend to use only the frontend mock mode, leave both backend URL variables empty.

After changing Vite environment variables on the hosting platform, trigger a new build because Vite embeds these values into the generated client bundle.

### Backend deployment

Suitable hosting options include Render or another Python ASGI host that supports persistent web services and WebSockets.

Typical setup:

- **Root directory:** `backend`
- **Build/install command:** `pip install -e .`
- **Start command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

Set backend environment variables in the host's dashboard rather than committing them. At minimum, configure:
- `CORS_ORIGINS` to allow the deployed frontend origin.
- `AI_PROVIDER_MODE` and `HF_TOKEN` as needed.
- `DATABASE_URL` if you want a database location other than the default.

**Important deployment checks:**
1. Verify the host's Python version is 3.11 or newer.
2. Confirm the service binds to the platform-provided `$PORT`.
3. Test `/health` and `/docs` after deployment.
4. Configure CORS to include the exact frontend origin. The default CORS list is for local development and will not automatically include a deployed domain.
5. Confirm WebSocket connections work end-to-end through the hosting proxy.
6. Check whether the host's filesystem is persistent before relying on a local SQLite file for durable storage.
7. Review logging, exception handling, resource limits, and authentication before making the API publicly accessible.
8. Run the backend tests and frontend build before each release.

### Deployment environment examples

Frontend:

```dotenv
VITE_BACKEND_URL=https://your-backend.example.com
VITE_WS_URL=wss://your-backend.example.com
```

Backend:

```dotenv
CORS_ORIGINS=["https://your-frontend.example.com"]
AI_PROVIDER_MODE=mock
```

These are examples only. Use your actual deployed hostnames. Confirm how your hosting provider expects list-valued environment variables such as `CORS_ORIGINS` to be formatted.

---

## Troubleshooting

### Frontend cannot connect to backend
- Confirm the backend process is running and `/health` responds.
- Confirm `VITE_BACKEND_URL` uses the correct HTTP(S) base URL.
- Confirm `VITE_WS_URL` uses `ws://` locally or `wss://` for a secure deployed site.
- Restart Vite after editing the frontend `.env`.
- Check browser developer tools for CORS, HTTP, or WebSocket errors.

### CORS errors
- Add the exact frontend origin to the backend `CORS_ORIGINS` setting.
- Include the correct scheme and hostname; a different port counts as a different origin.
- Restart the backend after changing its environment.

### Backend fails to start
- Check that Python 3.11+ is installed.
- Ensure the terminal is in the `backend/` directory when running `uvicorn app.main:app`.
- Activate the intended virtual environment and install dependencies with `pip install -e .`.
- Read the first traceback error; later errors may be consequences of the first failure.

### AI calls fail
- Set `AI_PROVIDER_MODE=mock` to isolate the rest of the application from hosted AI availability.
- If using Hugging Face, verify `HF_TOKEN`, model access, network availability, and provider rate limits.
- Inspect backend logs for the actual provider error.

### Browser shows a blank page or stale UI
- Check the browser console.
- Run `npm run typecheck`, `npm run lint`, and `npm run build`.
- Confirm you opened the Vite URL printed in the terminal.
- Restart the development server after environment changes.

### Port is already in use
- Stop the process using port `5173` or `8000`, or choose a different port and update the frontend URLs accordingly.

### Frontend looks live but data is simulated
That is expected in mock/demo mode. The presence of moving agents, camera-context panels, or real-time UI updates does not by itself mean that physical CCTV or live venue sensors are connected.

---

## Limitations and responsible use

Crowd-O-Holic is a prototype for learning, simulation, and demonstration. It should not be the sole basis for evacuation, crowd-control, security, medical, or other emergency decisions.

Current repository scope includes a demo venue, synthetic/simulated agents, simulation metrics, routing, risk indicators, and optional AI-assisted interpretation. It does not establish that the project currently includes:
- Live CCTV stream ingestion.
- Computer-vision person detection or tracking.
- Camera calibration or conversion from pixels to real-world density.
- A validated model of pedestrian behaviour for a specific venue.
- Validated thresholds or certification for public-safety use.
- A production-grade alert delivery, authentication, audit, or access-control system.

Before real deployment, work with qualified crowd-safety professionals and venue operators; validate the simulation using measured venue geometry and observed data; assess false positives and false negatives; secure the API; test failure modes; and ensure operators can override system recommendations. Do not present simulated values as actual observed crowd counts.

---

## Roadmap ideas

Potential future extensions (not claims about current functionality):

- Integrate authorised CCTV/video sources or prerecorded footage.
- Add a computer-vision pipeline for detection and tracking, with privacy-aware processing.
- Calibrate camera views to estimate real-world density and flow.
- Support venue-specific floor plans, gates, capacities, and pedestrian connections.
- Compare predicted metrics against labelled or observed crowd data.
- Add authenticated operator roles, audit logs, and controlled emergency workflows.
- Add automated integration tests for REST and WebSocket behaviour.
- Add deployment health checks, monitoring, and documented backup/recovery procedures.
- Improve accessibility, responsive layouts, and operator usability.
- Add exportable scenario reports and replayable simulation sessions.

## Contributing

Contributions, bug reports, and improvement ideas are welcome.

Suggested workflow:

1. Fork the repository.
2. Create a feature branch.
3. Make a focused change and document any configuration updates.
4. Run backend tests and frontend checks.
5. Open a pull request with a clear description, screenshots where useful, and test results.

Please do not include API tokens, `.env` files, private CCTV footage, personal data, or other sensitive information in commits or issue attachments.

## License

No license file was present in the supplied project archive. Until a license is added, assume that standard copyright applies and that reuse, modification, and redistribution are not automatically granted. Add an appropriate `LICENSE` file if you want to define open-source permissions.

---

## Acknowledgements

Built as a software prototype exploring crowd-flow simulation, venue operations visualisation, risk indicators, dynamic routing, and AI-assisted scenario analysis.

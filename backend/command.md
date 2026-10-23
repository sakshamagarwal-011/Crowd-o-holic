# Crowd-o-holic — Codex Backend Implementation Command

## 0. Mission

You are the primary implementation agent for the **Crowd-o-holic / Crowd Flow Optimiser** repository.

Your job is to build and integrate the complete backend and AI layer into the existing repository so that the **existing frontend works end-to-end**.

This file is an execution/engineering instruction for Codex.

The repository already contains an existing frontend created by another team member. Treat that frontend as an existing product surface, not as a disposable prototype.

The authoritative backend architecture is defined in:

```text
backend/context.md
```

Read it completely before making architectural or implementation changes.

Also read:

```text
backend/command.md
```

if this file is being used as the project command file, and inspect any existing project instructions before modifying code.

---

# 1. Absolute Rules

These rules have priority throughout implementation.

1. Read `backend/context.md` completely before coding.
2. Inspect the entire repository before making changes.
3. Inspect the entire existing frontend before designing backend API contracts.
4. Do not blindly replace or rewrite existing frontend functionality.
5. Do not create a disconnected demo backend.
6. Build the backend around the existing frontend's actual API/service/type requirements.
7. Preserve the authoritative architecture from `context.md`.
8. The deterministic simulation/decision loop is the core product.
9. AI is not authoritative for simulation, risk, capacity, or routing calculations.
10. AI failure must never stop the deterministic simulation.
11. Do not put simulation logic inside API route handlers.
12. Do not put risk logic inside WebSocket handlers.
13. Do not make frontend components independently calculate authoritative simulation values.
14. Use one centralized real-time communication layer.
15. Keep active simulation state in the simulation/application layer.
16. Avoid database writes on every simulation tick.
17. Do not hardcode venue layouts, scenarios, API secrets, risk thresholds, or routing weights.
18. Use configuration/environment variables for tunable behavior.
19. Use deterministic seeds for reproducible demo simulations.
20. Do not create duplicate frontend or backend applications.
21. Do not create unnecessary architectural abstractions.
22. Keep the application runnable after every major implementation phase.
23. Run tests/type checks/build checks after meaningful changes.
24. Fix errors before moving to the next phase.
25. Do not stop at scaffolding; implement working end-to-end behavior.

---

# 2. Authoritative Product Loop

The central product is:

```text
Crowd
  ↓
Movement
  ↓
Metrics
  ↓
Risk
  ↓
Routing
  ↓
Crowd Redistribution
  ↓
Metrics
  ↓
Risk
  ↓
AI Interpretation
  ↓
Real-Time Frontend
```

Do not turn this project into a CRUD application with a simulation attached.

CRUD, persistence, REST, WebSocket, AI, and frontend integration are supporting systems around the simulation/decision loop.

---

# 3. Authoritative Backend Pipeline

Normal flow:

```text
User Scenario
    ↓
Scenario Validation / Normalization
    ↓
Scenario Intelligence
    ↓
Structured Scenario Parameters
    ↓
Venue Graph
    ↓
Crowd Generation
    ↓
Destination Selection
    ↓
Crowd / Flow Simulation
    ↓
Queue Simulation
    ↓
Crowd Metrics
    ↓
Risk & Bottleneck Analysis
    ↓
Dynamic Routing
    ↓
Flow Redistribution
    ↓
Updated Simulation
    ↓
AI Safety Analysis
    ↓
Real-Time State Broadcast
    ↓
Frontend Dashboard
```

Emergency flow:

```text
Emergency Event
    ↓
Validate Emergency
    ↓
Modify Venue / Capacity State
    ↓
Recalculate Affected Routes
    ↓
Redistribute Crowd
    ↓
Run Simulation
    ↓
Metrics
    ↓
Risk
    ↓
AI Safety Analysis
    ↓
Real-Time Update
    ↓
Frontend
```

---

# 4. First Action: Repository Audit

Before creating or changing implementation files, inspect:

```text
frontend/
backend/
backend/context.md
backend/command.md
```

Also inspect:

- package manifests
- Python configuration
- TypeScript configuration
- existing environment examples
- existing API/service files
- existing frontend mock services
- frontend types/interfaces
- frontend hooks
- frontend state management
- frontend WebSocket code
- frontend API clients
- existing tests
- existing backend files
- README files
- build scripts

Do not make assumptions from filenames alone.

---

# 5. Frontend Is the Integration Contract

The existing frontend must continue to work.

Inspect every frontend feature that requires backend functionality.

Find:

- fetch calls
- Axios calls
- API clients
- WebSocket connections
- mock services
- hooks
- stores
- state transitions
- TypeScript interfaces
- request types
- response types
- event types
- loading states
- error states
- simulation controls
- emergency controls
- venue map requirements
- bottleneck displays
- route displays
- risk displays
- AI recommendation displays

Create an internal mapping:

```text
Frontend feature
    ↓
Frontend file/component
    ↓
API/WebSocket dependency
    ↓
Request contract
    ↓
Response/event contract
    ↓
Backend module
```

Do not invent a new API if the frontend already expects a compatible endpoint.

If endpoint names must be adapted, prefer the smallest integration change possible.

---

# 6. Frontend Preservation Rules

Do not:

- redesign the UI
- replace the frontend framework
- remove working components
- remove existing features
- rewrite the frontend from scratch
- replace state management without necessity
- replace existing mock boundaries unnecessarily

If the frontend currently uses mock data:

```text
Frontend
   ↓
Existing service boundary
   ↓
Mock data
```

replace the implementation behind that boundary with:

```text
Frontend
   ↓
Existing service boundary
   ↓
Real Backend
```

Keep a fallback/mock development mode where useful.

---

# 7. Backend Architecture

Use a modular architecture following `backend/context.md`.

A suitable structure is:

```text
backend/
├── app/
│   ├── main.py
│   │
│   ├── api/
│   │   ├── routes/
│   │   │   ├── scenarios.py
│   │   │   ├── venues.py
│   │   │   ├── simulations.py
│   │   │   ├── routes.py
│   │   │   ├── emergencies.py
│   │   │   └── health.py
│   │   └── websocket.py
│   │
│   ├── core/
│   │   ├── config.py
│   │   ├── logging.py
│   │   └── errors.py
│   │
│   ├── domain/
│   │   ├── venue/
│   │   ├── scenario/
│   │   ├── crowd/
│   │   ├── simulation/
│   │   ├── metrics/
│   │   ├── risk/
│   │   ├── routing/
│   │   ├── emergency/
│   │   └── ai/
│   │
│   ├── services/
│   │   ├── scenario_service.py
│   │   ├── venue_service.py
│   │   ├── simulation_service.py
│   │   ├── metrics_service.py
│   │   ├── risk_service.py
│   │   ├── routing_service.py
│   │   ├── emergency_service.py
│   │   └── ai_service.py
│   │
│   ├── simulation/
│   │   ├── engine.py
│   │   ├── crowd_generator.py
│   │   ├── destination_selector.py
│   │   ├── movement.py
│   │   ├── queues.py
│   │   └── state.py
│   │
│   ├── graph/
│   │   ├── graph.py
│   │   ├── nodes.py
│   │   ├── edges.py
│   │   ├── capacity.py
│   │   └── pathfinding.py
│   │
│   ├── ai/
│   │   ├── provider.py
│   │   ├── config.py
│   │   ├── huggingface_provider.py
│   │   ├── mock_provider.py
│   │   ├── scenario_parser.py
│   │   ├── safety_analyst.py
│   │   ├── prompts.py
│   │   └── schemas.py
│   │
│   ├── realtime/
│   │   ├── connection_manager.py
│   │   ├── broadcaster.py
│   │   └── events.py
│   │
│   ├── persistence/
│   │   ├── database.py
│   │   ├── models/
│   │   └── repositories/
│   │
│   └── schemas/
│
├── demo/
│   ├── venues/
│   ├── scenarios/
│   ├── emergencies/
│   └── seed_data.py
│
├── tests/
├── migrations/
├── .env
├── .env.example
├── pyproject.toml
└── README.md
```

Adapt the exact structure to the repository if an equivalent structure already exists.

Do not create duplicate modules simply because the names differ.

---

# 8. Implementation Order

Implement in this order.

## Phase 1 — Foundation

Build:

- configuration
- logging
- errors
- domain models
- Pydantic schemas
- venue graph
- basic API
- health endpoint
- application startup
- environment configuration

Verify the backend starts.

---

## Phase 2 — Venue Graph

Implement:

- venue
- nodes
- edges
- directional edges where needed
- node capacity
- edge capacity
- service rates
- edge status
- occupancy
- dynamic cost
- enabled/disabled state

Graph must support:

- normal paths
- disabled paths
- emergency closures
- dynamic route costs

Do not hardcode a single venue into the graph engine.

---

## Phase 3 — Scenario

Implement:

- scenario creation
- scenario validation
- normalization
- event schedule
- crowd size
- entry configuration
- exit configuration
- destination preferences
- special conditions
- simulation duration
- simulation timestep
- random seed

Validate:

- IDs
- numeric ranges
- rates
- references to venue entities
- event times
- simulation settings

---

# 9. Deterministic Simulation Core

Implement the simulation independently of HTTP.

The engine should conceptually expose:

```text
initialize()
step()
run()
pause()
resume()
reset()
stop()
get_state()
```

Simulation lifecycle:

```text
created
initialized
running
paused
completed
stopped
failed
```

Every simulation has a unique ID.

Multiple simulations must remain isolated.

Never use mutable global state for active simulations.

---

# 10. Crowd Generator

Support aggregated flow groups where possible.

Do not create heavyweight individual-person objects unless required.

Crowd/group properties should support:

- id
- current node/position
- destination
- route
- speed
- group size
- state
- entry time
- target arrival
- current edge
- queue state

States:

```text
waiting
moving
queued
arrived
exited
rerouting
```

Crowd generation must use:

- total crowd size
- entry gates
- entry rates
- arrival timing
- groups
- initial destinations

Use a deterministic random seed.

---

# 11. Destination Selection

Destination selection may use:

- scenario configuration
- venue layout
- group preferences
- event schedule
- facility locations
- current conditions

Destinations must be changeable when routing needs to redistribute flow.

---

# 12. Movement Simulation

For every simulation timestep:

```text
1. Update arrivals
2. Update destinations
3. Calculate available movement
4. Apply capacity constraints
5. Move crowd
6. Update queues
7. Update occupancy
8. Calculate metrics
9. Detect bottlenecks
10. Calculate risk
11. Update route costs
12. Recalculate routes when required
13. Apply redistribution
14. Publish state
```

Avoid unnecessary full-world recalculation.

Keep the engine independent from HTTP and WebSocket code.

---

# 13. Queue Simulation

Track:

- queue size
- queue growth rate
- queue location
- service/flow rate
- waiting time where available
- capacity
- saturation

Queue growth must feed the risk engine.

---

# 14. Metrics

At minimum calculate:

- people count
- density
- flow rate
- average speed
- queue growth
- capacity utilization

Capacity utilization:

```text
current_load / capacity
```

Protect against invalid/zero capacity.

Do not allow the frontend to become the authoritative calculator.

---

# 15. Risk Engine

Risk is deterministic.

Inputs can include:

- density
- capacity utilization
- flow rate
- speed reduction
- queue growth
- bottleneck severity
- predicted congestion
- time-to-critical
- emergency state

Risk output:

```text
score
severity
contributing_factors
affected_locations
timestamp
trend
time_to_critical
```

Severity:

```text
safe
low
moderate
high
critical
```

Thresholds must be configuration-driven.

Do not hide the risk formula inside API controllers.

---

# 16. Bottleneck Detection

Use configurable thresholds for:

- utilization
- density
- queue growth
- flow/capacity ratio
- speed reduction
- persistence

Avoid triggering on one noisy measurement.

Implement persistence/hysteresis.

---

# 17. Bottleneck Prediction

Initial prediction should be deterministic.

Possible inputs:

- current density
- density growth
- queue growth
- utilization
- inflow
- outflow
- capacity

Output:

```text
predicted_location
predicted_severity
estimated_time_to_critical
contributing_trend
```

If time-to-critical cannot be estimated reliably, return `null`.

Do not fabricate predictions.

Keep the module extensible for a future ML model, but do not add an unnecessary ML model now.

---

# 18. Dynamic Routing

Routing uses:

- venue graph
- edge capacity
- occupancy
- density
- risk
- disabled edges
- emergency state

Dynamic edge cost concept:

```text
base_travel_cost
+ congestion_penalty
+ risk_penalty
+ capacity_penalty
```

Make weights configurable.

Do not hardcode routing weights in controllers.

---

# 19. Pathfinding

Support an abstraction such as:

```python
find_route(graph, source, destination, edge_cost_function)
```

Use A* or Dijkstra.

Keep pathfinding replaceable.

---

# 20. Alternative Routes

Alternative route output should include:

- route nodes/edges
- estimated cost
- expected capacity
- current congestion
- risk
- status

Reject routes that are:

- disabled
- unavailable
- unsafe
- over capacity where configured

---

# 21. Flow Redistribution

When routing changes:

```text
1. Identify affected crowd groups
2. Find eligible alternatives
3. Assign new routes
4. Update expected flow
5. Re-run simulation
6. Measure whether congestion decreases
```

Prevent route oscillation using:

- route-change threshold
- minimum route stability period
- hysteresis
- cooldown

---

# 22. Emergency System

Emergency events may:

- disable an edge
- disable a node
- reduce capacity
- block a facility
- increase local risk

Flow:

```text
Emergency
→ Validate
→ Modify venue state
→ Disable/reduce capacity
→ Recalculate routes
→ Redistribute crowd
→ Metrics
→ Risk
→ AI analysis
→ Real-time broadcast
```

Emergency state must be explicit.

---

# 23. Simulation Lifecycle API

Support:

```text
POST /simulations
GET /simulations/{simulation_id}
POST /simulations/{simulation_id}/start
POST /simulations/{simulation_id}/pause
POST /simulations/{simulation_id}/resume
POST /simulations/{simulation_id}/reset
POST /simulations/{simulation_id}/stop
GET /simulations/{simulation_id}/state
```

Adapt exact endpoint names if the existing frontend already expects different names.

---

# 24. Other REST API Capabilities

Implement compatible endpoints for:

```text
Venues:
POST /venues
GET /venues
GET /venues/{venue_id}
PUT /venues/{venue_id}

Scenarios:
POST /scenarios
GET /scenarios
GET /scenarios/{scenario_id}

AI Scenario Parsing:
POST /scenarios/parse

Emergency:
POST /simulations/{simulation_id}/emergencies

Routes:
GET /simulations/{simulation_id}/routes

Health:
GET /health
```

The existing frontend contract takes precedence over these conceptual names.

---

# 25. Real-Time Communication

Use ONE centralized real-time communication mechanism.

Do not create a WebSocket per frontend component.

The real-time layer should:

- manage connections
- subscribe clients to simulation IDs
- publish simulation snapshots
- publish metrics
- publish risk
- publish bottlenecks
- publish route changes
- publish emergency events
- publish AI analysis
- handle disconnect/reconnect cleanly

Architecture:

```text
Simulation Engine
      ↓
Domain/Event Publisher
      ↓
Real-Time Connection Manager
      ↓
Connected Frontend Clients
```

The simulation engine must not know about individual frontend clients.

---

# 26. Real-Time Event Types

Use explicit predictable event types:

```text
simulation.started
simulation.paused
simulation.updated
simulation.completed

metrics.updated

risk.updated

bottleneck.detected
bottleneck.cleared

route.changed

emergency.started
emergency.updated
emergency.resolved

ai.analysis.updated

connection.status
```

Every event must have a predictable schema.

Use compact snapshots.

Do not stream unnecessary internal engine state.

---

# 27. State Snapshot

A frontend-compatible state snapshot should support:

```text
simulation_id
simulation_time
status

crowd:
  total
  active
  queued
  exited

metrics:
  density
  flow_rate
  average_speed
  queue_growth
  capacity_utilization

risk:
  score
  severity
  time_to_critical

bottlenecks

routes:
  active
  alternative
  disabled

emergency

ai:
  status
  recommendation
```

Use proper Pydantic schemas.

Do not blindly copy internal Python objects into WebSocket payloads.

---

# 28. AI Architecture — Mandatory

The AI layer must follow the architecture already established in this project.

There are exactly TWO primary LLM capabilities.

## AI Call 1 — Scenario Intelligence

```text
User Natural Language Scenario
        ↓
Preprocessing
        ↓
Qwen 2.5 7B Instruct
        ↓
Structured JSON
        ↓
Pydantic Validation
        ↓
Structured Scenario Parameters
        ↓
Deterministic Simulation
```

Example user input:

```text
Simulate an IPL match with 30,000 spectators.
Most people enter through Gate A and Gate B.
During halftime there will be heavy movement
towards food courts and restrooms.
After the match most people leave through
the south exits.
```

The model should extract information such as:

- crowd size
- event type
- entry points
- entry distribution if explicitly stated
- event phases
- destinations
- destination distribution if explicitly stated
- exits
- special conditions

Do not let the model invent exact values that were not supplied.

The output must be structured and validated.

---

# 29. AI Call 1 — Validation

Validate:

- required fields
- data types
- non-negative values
- valid rates
- valid event times
- valid venue node/gate IDs
- capacity constraints
- logical consistency

If the AI output is incomplete or invalid:

```text
Return a clear validation error.
Do not silently guess.
Do not invent critical parameters.
```

The simulation must never consume raw unvalidated LLM output.

---

# 30. AI Call 2 — Safety Analyst

Input:

```text
simulation metrics
risk score
risk severity
bottlenecks
current routes
route changes
critical/emergency events
relevant venue context
```

Pipeline:

```text
Simulation Results
        ↓
Result Aggregation
        ↓
Safety Context
        ↓
Qwen 2.5 7B Instruct
        ↓
Structured Safety Analysis
        ↓
Pydantic Validation
        ↓
Frontend / Operator
```

The Safety Analyst explains deterministic results.

It does NOT calculate:

- risk score
- density
- capacity
- bottlenecks
- routes
- alternative routes
- flow redistribution

---

# 31. AI Safety Output

Use a structured schema containing at minimum:

```text
summary
risk_explanation
affected_locations
contributing_factors
recommended_action
urgency
supporting_metrics
generated_timestamp
```

Example:

```json
{
  "summary": "High congestion is developing in the north corridor.",
  "risk_explanation": "Capacity utilization is increasing while outflow remains constrained.",
  "affected_locations": ["north_corridor"],
  "contributing_factors": [
    "high utilization",
    "increasing queue growth"
  ],
  "recommended_action": "Redirect incoming flow toward the west corridor.",
  "urgency": "high",
  "supporting_metrics": {
    "capacity_utilization": 0.87
  }
}
```

The actual values must come from the simulation/backend context.

The LLM must not invent routes or numerical measurements.

---

# 32. Hugging Face / Qwen Requirements

The current AI implementation uses:

```text
Qwen/Qwen2.5-7B-Instruct
```

through Hugging Face Inference Providers.

Use:

```python
from huggingface_hub import InferenceClient
```

Use:

```python
client.chat_completion(...)
```

Do NOT use:

```python
client.text_generation(...)
```

for this conversational Qwen implementation.

The model is an instruction/chat model and the project needs instruction-following plus structured outputs.

Required Python dependencies:

```text
huggingface-hub
pydantic
python-dotenv
pytest
```

Do not add LangChain, LlamaIndex, PyTorch, TensorFlow, scikit-learn, or other unnecessary ML frameworks for the current AI layer.

---

# 33. Hugging Face Environment Configuration

Local development uses `.env`.

Expected variables:

```env
HF_TOKEN=...
HF_MODEL=Qwen/Qwen2.5-7B-Instruct
```

The real token must NEVER be committed.

`.env.example` should contain:

```env
HF_TOKEN=
HF_MODEL=Qwen/Qwen2.5-7B-Instruct
```

Never print the full token.

Never expose the token through:

- logs
- API responses
- exceptions
- frontend payloads
- WebSocket events

---

# 34. Cloud/Codex Environment Rule

Codex cloud environments may not automatically have access to the developer's local `.env`.

Therefore:

- never depend on a committed `.env`
- never copy secrets into source code
- use environment variables/secrets configured by the execution environment
- use `HF_TOKEN` only when live Hugging Face inference is enabled
- use the mock provider by default if the secret is unavailable

The project must still build and run without a real Hugging Face token.

---

# 35. AI Provider Abstraction

Use:

```text
AIProvider
    ├── HuggingFaceAIProvider
    └── MockAIProvider
```

Conceptually:

```python
class AIProvider:
    def parse_scenario(...):
        ...

    def analyze_safety(...):
        ...
```

The simulation engine must not depend directly on Hugging Face.

The application/service layer selects the provider.

This allows:

```text
development:
MockAIProvider

live/demo with configured token:
HuggingFaceAIProvider
```

The provider must be replaceable without rewriting simulation logic.

---

# 36. Mock AI Provider

The mock provider is mandatory.

It must:

- be deterministic
- return schema-valid data
- simulate both AI calls
- work without network access
- allow the entire frontend demo to work without Hugging Face
- not hide real AI failures

Use realistic deterministic mock responses.

Do not scatter mock strings throughout controllers.

Keep mock behavior in the AI provider/demo area.

---

# 37. AI Failure Handling

AI is non-critical.

If Hugging Face fails:

```text
Simulation continues
Risk continues
Routing continues
Emergency handling continues
Frontend receives normal state
AI status becomes unavailable
```

Use:

- timeout
- bounded retry
- structured failure state
- clear logs

Never allow an AI timeout to stop the simulation.

---

# 38. Scenario Parser Failure

If natural-language parsing fails:

```text
Return validation error
Show missing/unextractable information
Allow manual structured scenario entry
```

Never invent critical values.

---

# 39. AI Integration Timing

Do NOT call a remote LLM on every simulation timestep.

That would create:

- unnecessary latency
- excessive inference cost
- unstable simulation timing
- provider dependency

AI analysis should be triggered:

- when a meaningful risk state changes
- when a bottleneck is detected
- when an emergency occurs
- when a route/risk situation materially changes
- when explicitly requested by the application

Use configurable cooldown/debouncing where appropriate.

The deterministic simulation loop must remain fast and independent.

---

# 40. AI Prompt Requirements

Keep prompt construction inside the AI layer.

Prompts must tell the model:

### Scenario parser

- extract only information supported by the input
- do not invent critical values
- return structured data
- distinguish unspecified values
- use valid JSON/schema-compatible output

### Safety analyst

- explain supplied simulation results
- preserve numerical values
- explain supplied bottlenecks
- explain supplied routing decisions
- recommend operator actions based on supplied information
- do not invent routes
- do not recalculate authoritative risk
- do not claim certainty beyond simulation evidence

Do not allow arbitrary model output to directly control simulation state.

---

# 41. Persistence

Support persistence for:

- venue layouts
- scenario definitions
- event schedules
- simulation metadata
- simulation history
- summary results

Do NOT persist every high-frequency simulation tick by default.

Use configurable snapshot/persistence frequency.

Use repository abstractions:

```text
VenueRepository
ScenarioRepository
SimulationRepository
EventRepository
```

Do not access the database directly from domain logic.

---

# 42. Local Development Database

Follow the database choice already present in the repository/context.

If no database is currently configured, choose a local-development-friendly setup that matches the project's architecture and document it.

Do not make local development unnecessarily dependent on a remote database.

Add migrations/schema setup when a real database is required.

---

# 43. Demo Data

Create dedicated demo data files.

Do NOT scatter demo values through production source code.

Provide at least:

```text
one realistic venue
one realistic scenario
one crowd configuration
one emergency scenario
```

The venue should contain meaningful:

- gates
- corridors
- junctions
- facilities
- exits
- capacities

Use a deterministic simulation seed, for example:

```text
12345
```

or another clearly documented seed.

The demo must be reproducible.

---

# 44. Frontend End-to-End Requirements

The final application should support, through the existing UI where those functions exist:

```text
Venue loading/creation
Scenario creation
Natural-language scenario parsing
Structured scenario editing
Simulation creation
Initialization
Start
Pause
Resume
Reset
Stop
State retrieval
Live crowd state
Metrics
Risk
Bottlenecks
Alternative routes
Route changes
Emergency trigger
Emergency state
AI safety analysis
Real-time updates
```

Do not add fake frontend behavior merely to make a button appear functional.

Every implemented frontend function must connect to real backend behavior or the documented mock provider.

---

# 45. API Contract

Use typed Pydantic request/response schemas.

Every endpoint must validate:

- IDs
- request shape
- numerical ranges
- enums
- references to venue entities
- simulation state transitions

Return consistent errors.

Use explicit response models.

Do not return arbitrary dictionaries when a typed schema is appropriate.

---

# 46. Health / Observability

Provide:

```text
GET /health
```

It should expose safe status information such as:

- application health
- database health if enabled
- AI provider availability
- simulation subsystem status where appropriate

Never expose secrets.

Use structured logging.

Log important events:

```text
simulation created
simulation started
simulation paused
simulation stopped
bottleneck detected
risk changed
route changed
emergency triggered
AI analysis completed
AI analysis failed
connection failure
unexpected simulation error
```

Avoid logging full high-volume state or secrets.

---

# 47. Concurrency

Multiple simulations may exist.

State must be isolated by simulation ID.

Protect against race conditions involving:

- start
- pause
- resume
- reset
- stop
- emergency
- route changes

Use application/simulation-level synchronization.

Do not use unsafe mutable global state.

---

# 48. Performance

Avoid:

- blocking API handlers
- blocking AI calls inside simulation steps
- repeated graph reconstruction
- repeated full-state serialization
- database writes every tick
- one network request per agent
- one AI request per tick

Prefer:

- in-memory active state
- batched updates
- compact snapshots
- async/background execution where appropriate
- cached graph structures
- configurable real-time update frequency
- asynchronous AI analysis

---

# 49. Testing Requirements

Implement tests for:

## Graph

- node creation
- edge creation
- capacity
- disabled routes
- pathfinding

## Simulation

- crowd generation
- movement
- destination selection
- queue formation
- capacity constraints
- lifecycle

## Metrics

- density
- flow
- speed
- queue growth
- utilization

## Risk

- thresholds
- severity
- bottleneck detection
- prediction
- time-to-critical

## Routing

- congestion-aware routes
- alternative paths
- emergency rerouting
- route stability
- redistribution

## Emergency

- edge closure
- node closure
- capacity reduction
- rerouting
- risk recalculation

## AI

- scenario parsing
- structured parsing
- Pydantic validation
- malformed model output
- missing fields
- invalid values
- safety analyst validation
- timeout
- provider failure
- mock provider

## API

- validation
- lifecycle
- state
- emergency
- scenarios
- venues
- health

## Real-Time

- connection management
- simulation subscription
- event broadcasting
- event schema

Unit tests should mock the Hugging Face provider.

Tests must not require paid/live inference by default.

---

# 50. Test the AI Layer Without Network

The default test strategy must use:

```text
MockAIProvider
```

or mocked `InferenceClient`.

Do not spend inference credits in normal test runs.

Test live Hugging Face inference separately as an optional integration test.

---

# 51. README Requirements

Update/create backend README documentation explaining:

1. prerequisites
2. Python version
3. dependency installation
4. environment variables
5. Hugging Face token setup
6. mock AI mode
7. live AI mode
8. backend startup
9. frontend startup
10. database setup
11. migrations
12. demo data loading
13. starting a demo simulation
14. triggering an emergency
15. WebSocket usage
16. running tests
17. troubleshooting

Also document that the Hugging Face token is never committed.

---

# 52. Environment Configuration

At minimum support configurable values for:

```text
simulation timestep
maximum simulation duration
risk thresholds
bottleneck thresholds
routing weights
route-change cooldown
AI timeout
AI model
AI provider mode
real-time update frequency
persistence frequency
logging level
```

Use environment/configuration.

Do not bury these as constants throughout the code.

---

# 53. Implementation Discipline

Work incrementally.

After each major phase:

1. run tests
2. run backend import checks
3. run frontend type/build checks
4. fix errors
5. verify the application still starts

Do not implement the entire backend in one unverified batch.

Suggested order:

```text
Audit
↓
Foundation
↓
Venue Graph
↓
Scenario
↓
Simulation
↓
Metrics
↓
Risk
↓
Routing
↓
Emergency
↓
Real-Time
↓
AI
↓
Persistence
↓
Frontend Integration
↓
End-to-End Testing
↓
Hardening
```

---

# 54. Git / File Safety

Before modifying files:

```text
inspect git status
inspect current branch
inspect existing changes
```

Do not discard existing user/team work.

Do not run destructive git commands.

Never run:

```text
git reset --hard
git clean -fd
```

unless explicitly instructed by the user.

Do not overwrite existing frontend work simply because another implementation is easier.

---

# 55. No Secrets in Git

Never commit:

```text
.env
HF_TOKEN
API keys
passwords
database credentials
```

Ensure `.gitignore` contains appropriate secret/environment entries.

`.env.example` contains placeholders only.

---

# 56. Definition of Done

The implementation is not complete until:

- venue can be represented as a graph
- scenario can be created and validated
- natural-language scenario parsing works
- structured scenario output is validated
- deterministic crowd flow works
- queues can form
- metrics are calculated
- bottlenecks are detected
- risk is calculated
- time-to-critical is estimated where possible
- dynamic routing responds to congestion
- crowd flow is redistributed
- emergency closures work
- simulation lifecycle works
- live state is streamed
- AI safety analysis works
- AI failure does not stop simulation
- mock AI mode works
- persistence works according to project requirements
- tests cover the core modules
- health endpoint works
- structured logs exist
- frontend consumes real backend data
- frontend real-time updates work
- existing frontend functions work end-to-end
- local demo is reproducible
- README is complete
- build/type checks pass
- tests pass

---

# 57. Final Verification Checklist

Before reporting completion, verify:

## Backend

- [ ] Starts successfully
- [ ] Health endpoint works
- [ ] API validation works
- [ ] Simulation lifecycle works
- [ ] Multiple simulations are isolated
- [ ] Simulation can run without HTTP coupling

## Simulation

- [ ] Crowd generation works
- [ ] Movement works
- [ ] Queues work
- [ ] Metrics work
- [ ] Risk works
- [ ] Bottlenecks work
- [ ] Prediction works
- [ ] Routing works
- [ ] Redistribution works
- [ ] Emergency rerouting works

## AI

- [ ] Mock provider works
- [ ] Hugging Face provider works when configured
- [ ] Qwen model configuration works
- [ ] `chat_completion()` is used
- [ ] Scenario parser returns structured validated data
- [ ] Safety analyst returns structured validated data
- [ ] AI failures are non-fatal
- [ ] No secrets are logged
- [ ] AI is not authoritative for deterministic calculations

## Real-Time

- [ ] Centralized connection manager works
- [ ] Simulation subscriptions work
- [ ] Simulation events broadcast
- [ ] Risk events broadcast
- [ ] Bottleneck events broadcast
- [ ] Route events broadcast
- [ ] Emergency events broadcast
- [ ] AI events broadcast

## Frontend

- [ ] Existing frontend starts
- [ ] Existing API/service layer works
- [ ] Existing controls work
- [ ] Venue data loads
- [ ] Scenario flow works
- [ ] Simulation controls work
- [ ] Live state updates
- [ ] Risk visualization updates
- [ ] Bottleneck visualization updates
- [ ] Routes update
- [ ] Emergency UI works
- [ ] AI recommendation appears
- [ ] Mock mode works without external services

## Quality

- [ ] Tests pass
- [ ] Type checks pass
- [ ] Frontend build passes
- [ ] Backend imports pass
- [ ] No secrets committed
- [ ] No destructive git changes
- [ ] README is updated
- [ ] No duplicate backend/frontend application exists

---

# 58. Final Instruction to Codex

Do not simply create scaffolding.

Do not stop after creating folders.

Do not implement only the API.

Do not implement only the simulation.

Do not implement only the AI.

Do not create a fake frontend demo.

Build the complete working integration.

The final architecture must preserve:

```text
Frontend
   ↕
REST / WebSocket
   ↕
Application / Services
   ↕
Deterministic Simulation Core
   ↕
Metrics → Risk → Routing → Redistribution
   ↕
AI Interpretation
```

The deterministic simulation remains the source of truth.

AI provides:

```text
Scenario Intelligence
+
Safety Interpretation
```

The application must remain functional when AI is unavailable.

The existing frontend must remain functional and become connected to the real backend.

Read `backend/context.md` completely before making changes, inspect the repository first, work incrementally, test continuously, and finish only when the complete end-to-end system is runnable.

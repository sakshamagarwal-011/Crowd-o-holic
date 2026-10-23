# Backend Context Specification

## Crowd Safety Simulation & Intelligent Venue Management System

This document is the authoritative context for building the backend of
the project.

The backend must implement the computational core of a crowd-safety
simulation and decision-support platform. It receives venue/event
scenarios, converts them into structured simulation inputs, constructs a
venue graph, simulates crowd movement and queues, computes crowd
metrics, detects and predicts bottlenecks, calculates risk, dynamically
reroutes crowd flow, handles emergency route closures, exposes live
simulation state, and provides structured information to an AI safety
analyst.

The backend should be designed as a modular system rather than a
monolithic API.

------------------------------------------------------------------------

# 1. Product Purpose

The system answers:

1.  Where is the crowd?
2.  How dense is each area?
3.  Where is congestion forming?
4.  Which areas are becoming unsafe?
5.  How quickly could a location become critical?
6.  Which routes should be changed?
7.  How can crowd flow be redistributed?
8.  What happens if a route or facility becomes unavailable?
9.  What should the venue operator do?
10. How can AI explain the current safety situation in human-readable
    language?

The backend is the source of truth for simulation state, metrics, risk,
bottlenecks, and routing.

The frontend must visualize backend results and must not independently
recreate authoritative simulation or safety calculations.

------------------------------------------------------------------------

# 2. High-Level Architecture

The logical pipeline is:

User Scenario ↓ Scenario Intelligence ↓ Structured Scenario Parameters ↓
Core Orchestrator ↓ Venue Graph ↓ Crowd Generation ↓ Destination
Selection ↓ Crowd / Flow Simulation ↓ Queue Simulation ↓ Crowd Metrics ↓
Risk & Bottleneck Analysis ↓ Dynamic Routing ↓ Updated Simulation ↓ AI
Safety Analysis ↓ Real-Time State Broadcast ↓ Frontend Dashboard

Emergency path:

Emergency Event ↓ Affected Route / Node ↓ Disable or modify capacity ↓
Recalculate routing ↓ Redistribute crowd flow ↓ Re-run simulation ↓
Update risk ↓ Broadcast changes ↓ AI safety explanation

------------------------------------------------------------------------

# 3. Backend Responsibilities

The backend is responsible for:

-   Scenario validation
-   Scenario normalization
-   Venue representation
-   Venue graph construction
-   Crowd generation
-   Agent/group representation
-   Destination assignment
-   Movement simulation
-   Queue simulation
-   Capacity constraints
-   Density calculation
-   Flow calculation
-   Speed calculation
-   Queue-growth calculation
-   Capacity-utilization calculation
-   Bottleneck detection
-   Risk scoring
-   Bottleneck prediction
-   Time-to-critical estimation
-   Dynamic edge costs
-   Pathfinding
-   Alternative route generation
-   Flow redistribution
-   Emergency route closure
-   Route recalculation
-   Simulation lifecycle
-   Real-time state streaming
-   AI scenario parsing
-   AI safety analysis
-   Persistence
-   Historical simulation storage

The backend should NOT:

-   Depend on frontend-specific state
-   Put simulation logic inside API route handlers
-   Put risk calculations inside WebSocket handlers
-   Hardcode venue layouts
-   Hardcode a single scenario
-   Treat AI output as authoritative simulation truth

------------------------------------------------------------------------

# 4. Core Design Principles

## 4.1 Modular architecture

Separate:

-   API
-   orchestration
-   domain models
-   venue graph
-   simulation
-   metrics
-   risk
-   routing
-   emergency handling
-   AI
-   real-time communication
-   persistence

Each module should have a clear responsibility.

## 4.2 Deterministic simulation support

The simulation should support a seed so that the same scenario can be
reproduced.

Example concept:

simulation_seed = 12345

If a seed is supplied, random crowd generation and destination choices
should be reproducible.

## 4.3 Backend is authoritative

The backend owns:

-   crowd state
-   density
-   flow
-   queues
-   capacity
-   risk
-   bottlenecks
-   routes

## 4.4 AI is an interpretation layer

AI may:

-   parse natural-language scenarios
-   extract parameters
-   explain risk
-   summarize bottlenecks
-   recommend operator actions

AI must not silently override deterministic simulation state.

Structured AI output must be validated before entering the simulation.

## 4.5 Simulation must remain independent of HTTP

The simulation engine should be executable independently from the API.

The API should call the simulation/application layer rather than
implement it.

------------------------------------------------------------------------

# 5. Suggested Project Structure

Use a modular structure similar to:

backend/ ├── app/ │ ├── main │ │ │ ├── api/ │ │ ├── routes/ │ │ │ ├──
scenarios │ │ │ ├── venues │ │ │ ├── simulations │ │ │ ├── routes │ │ │
├── emergencies │ │ │ └── health │ │ └── dependencies │ │ │ ├── core/ │
│ ├── configuration │ │ ├── logging │ │ └── errors │ │ │ ├── domain/ │ │
├── venue │ │ ├── scenario │ │ ├── crowd │ │ ├── simulation │ │ ├──
metrics │ │ ├── risk │ │ ├── routing │ │ ├── emergency │ │ └── ai │ │ │
├── services/ │ │ ├── scenario_service │ │ ├── venue_service │ │ ├──
simulation_service │ │ ├── metrics_service │ │ ├── risk_service │ │ ├──
routing_service │ │ ├── emergency_service │ │ └── ai_service │ │ │ ├──
simulation/ │ │ ├── engine │ │ ├── crowd_generator │ │ ├──
destination_selector │ │ ├── movement │ │ ├── queues │ │ └── state │ │ │
├── graph/ │ │ ├── graph │ │ ├── nodes │ │ ├── edges │ │ ├── capacity │
│ └── pathfinding │ │ │ ├── ai/ │ │ ├── scenario_parser │ │ ├──
safety_analyst │ │ ├── prompts │ │ └── schemas │ │ │ ├── realtime/ │ │
├── connection_manager │ │ └── broadcaster │ │ │ ├── persistence/ │ │
├── repositories │ │ ├── models │ │ └── database │ │ │ └── schemas/ │
├── tests/ ├── migrations/ ├── configuration/ ├── Dockerfile ├── compose
configuration ├── environment example └── README

Adapt the exact structure to the repository, but preserve separation of
concerns.

------------------------------------------------------------------------

# 6. Domain Model

## 6.1 Venue

A venue contains:

-   id
-   name
-   dimensions
-   nodes
-   edges
-   facilities
-   capacity information

A venue is represented as a graph.

------------------------------------------------------------------------

# 7. Venue Graph

The venue graph contains:

## Nodes

Examples:

-   Entry gate
-   Exit gate
-   Junction
-   Food facility
-   Restroom
-   Seating area
-   Event area
-   Security checkpoint
-   Emergency exit

Each node may contain:

-   id
-   type
-   position
-   capacity
-   service rate
-   current population
-   properties

## Edges

Each edge represents a traversable connection.

Properties:

-   id
-   source node
-   destination node
-   length
-   width
-   capacity
-   travel time
-   status
-   current occupancy
-   current flow
-   dynamic cost
-   enabled/disabled state

The graph should support directional edges where required.

------------------------------------------------------------------------

# 8. Capacity Model

Capacity must exist at both node and edge levels where appropriate.

Examples:

Edge capacity depends on:

-   width
-   usable area
-   movement characteristics

Node capacity may depend on:

-   physical capacity
-   service rate
-   operational constraints

The system should allow capacities to be modified during runtime.

Emergency events may disable an edge or reduce its capacity.

------------------------------------------------------------------------

# 9. Scenario Model

A scenario should contain:

-   scenario id
-   venue id
-   crowd size
-   event schedule
-   entry configuration
-   exit configuration
-   destination preferences
-   special conditions
-   simulation duration
-   simulation step
-   random seed

Example conceptual structure:

{ "venue_id": "...", "crowd_size": 20000, "event_start": "...",
"entry_rates": {...}, "exit_rates": {...}, "destinations": {...},
"special_conditions": \[...\], "simulation": { "duration": ..., "step":
..., "seed": ... } }

Validate every value before simulation.

------------------------------------------------------------------------

# 10. Scenario Intelligence

Natural-language scenario input may be processed by the AI layer.

Input:

"A concert with 20,000 people starts at 7 PM. Most attendees enter
through the east gate."

The AI should extract structured information such as:

-   crowd size
-   event start
-   primary entry
-   expected entry distribution
-   expected destinations
-   special conditions

The AI response must be constrained to a structured schema.

Never directly execute arbitrary AI-generated values.

Validation must verify:

-   required fields
-   correct data types
-   valid node/gate IDs
-   non-negative values
-   rates within valid ranges
-   capacity constraints
-   valid event times

If AI output is incomplete or invalid, return a clear validation result
rather than silently guessing.

------------------------------------------------------------------------

# 11. Crowd Model

The system should support either individual agents or aggregated flow
groups.

The implementation should be designed so the representation can scale.

## Agent / Group properties

-   id
-   current node/position
-   destination
-   route
-   speed
-   group size
-   state
-   entry time
-   target arrival
-   current edge
-   queue state

States can include:

-   waiting
-   moving
-   queued
-   arrived
-   exited
-   rerouting

------------------------------------------------------------------------

# 12. Crowd Generator

The crowd generator creates the initial population from scenario
parameters.

It should account for:

-   total crowd size
-   entry gates
-   entry rates
-   arrival timing
-   crowd groups
-   initial destinations

Avoid creating expensive heavyweight objects for every person if the
simulation scale makes that impractical.

Use aggregation where possible.

------------------------------------------------------------------------

# 13. Destination Selection

Destination selection determines where crowd groups are trying to go.

Inputs may include:

-   scenario configuration
-   venue layout
-   group preferences
-   event schedule
-   facility locations
-   current conditions

Destinations should not be permanently fixed if the routing system later
needs to redirect flow.

------------------------------------------------------------------------

# 14. Crowd Movement Simulation

The simulation advances in discrete time steps.

Conceptually:

for each simulation step:

1.  Update arrivals
2.  Update agent/group destinations
3.  Calculate available movement
4.  Apply capacity constraints
5.  Move crowd
6.  Update queues
7.  Update occupancy
8.  Calculate metrics
9.  Detect bottlenecks
10. Calculate risk
11. Update route costs
12. Recalculate routes if needed
13. Apply redistribution
14. Publish current state

The implementation should avoid unnecessary full-world recalculation
when local updates are sufficient.

------------------------------------------------------------------------

# 15. Queue Simulation

Queues occur when demand exceeds movement/service capacity.

Queue state should track:

-   queue size
-   queue growth rate
-   queue location
-   service/flow rate
-   waiting time if available
-   capacity
-   saturation

Queue growth should feed into risk detection.

------------------------------------------------------------------------

# 16. Crowd Metrics

Calculate at least:

## People Count

Current number of people in relevant areas.

## Density

People per usable area or equivalent venue-specific density
representation.

## Flow Rate

Number of people moving through a location/edge per unit time.

## Average Speed

Average movement speed of crowd groups/agents.

## Queue Growth

Change in queue size over time.

## Capacity Utilization

Current load divided by usable capacity.

Example:

utilization = current_load / capacity

Protect against zero or invalid capacity.

------------------------------------------------------------------------

# 17. Risk Engine

Risk should be calculated from deterministic simulation information.

Potential inputs:

-   density
-   capacity utilization
-   flow rate
-   speed reduction
-   queue growth
-   bottleneck severity
-   predicted congestion
-   time-to-critical
-   emergency state

The exact scoring formula should be configurable.

Do not hide the formula inside a controller.

A risk result should include:

-   score
-   severity
-   contributing factors
-   affected locations
-   timestamp
-   trend
-   time-to-critical where available

Suggested severity:

-   safe
-   low
-   moderate
-   high
-   critical

The thresholds should be configuration-driven.

------------------------------------------------------------------------

# 18. Bottleneck Detection

A bottleneck is a location where crowd demand and available capacity
create sustained congestion or unsafe pressure.

Detection may use:

-   utilization threshold
-   density threshold
-   queue growth
-   flow/capacity ratio
-   speed reduction
-   persistence over multiple simulation steps

Avoid triggering a bottleneck on a single noisy measurement.

Use configurable persistence/hysteresis.

------------------------------------------------------------------------

# 19. Bottleneck Prediction

Prediction should estimate whether a current trend is likely to become
critical.

Possible inputs:

-   current density
-   density growth
-   queue growth
-   utilization
-   inflow
-   outflow
-   capacity

The prediction result should contain:

-   predicted location
-   predicted severity
-   estimated time-to-critical
-   contributing trend

The initial implementation may use deterministic trend extrapolation
rather than machine learning.

Keep the architecture open for a future predictive model.

------------------------------------------------------------------------

# 20. Time-to-Critical

Estimate how long before a location reaches a configured critical
threshold.

If the system cannot reliably estimate it:

return null / unavailable rather than inventing a number.

------------------------------------------------------------------------

# 21. Dynamic Routing

Routing reacts to current simulation conditions.

Inputs:

-   venue graph
-   edge capacity
-   edge occupancy
-   density
-   risk
-   disabled edges
-   emergency state

Calculate a dynamic edge cost.

Conceptually:

dynamic_cost = base_travel_cost + congestion_penalty + risk_penalty +
capacity_penalty

Do not hardcode this formula in a route controller.

Make the weighting configurable.

------------------------------------------------------------------------

# 22. Pathfinding

The routing engine should support a standard shortest-path strategy such
as:

-   A\*
-   Dijkstra

The exact algorithm can be abstracted behind a pathfinding interface.

Example:

find_route( graph, source, destination, edge_cost_function )

This makes future algorithms replaceable.

------------------------------------------------------------------------

# 23. Alternative Routes

The routing engine should be able to identify viable alternatives.

An alternative route should include:

-   route edges/nodes
-   estimated cost
-   expected capacity
-   current congestion
-   risk
-   status

The system should reject routes that are:

-   disabled
-   unavailable
-   over capacity where appropriate
-   unsafe according to configured rules

------------------------------------------------------------------------

# 24. Flow Redistribution

When routing changes:

1.  Identify affected crowd groups.
2.  Determine eligible alternatives.
3.  Assign new routes.
4.  Update expected flow.
5.  Re-run simulation.
6.  Observe whether congestion decreases.

Avoid oscillation where the system continuously changes routes back and
forth.

Use:

-   route-change thresholds
-   minimum route stability period
-   hysteresis
-   cooldown

------------------------------------------------------------------------

# 25. Emergency Response

An emergency event can:

-   disable an edge
-   disable a node
-   reduce capacity
-   block a facility
-   increase risk around a location

Emergency flow:

Emergency Event ↓ Validate event ↓ Modify venue state ↓ Disable/reduce
affected route capacity ↓ Recalculate affected routes ↓ Redistribute
crowd ↓ Recalculate metrics ↓ Recalculate risk ↓ Publish update ↓
Generate AI safety analysis

Emergency state should be represented explicitly.

------------------------------------------------------------------------

# 26. Simulation Lifecycle

Implement:

-   created
-   initialized
-   running
-   paused
-   completed
-   stopped
-   failed

Operations:

-   create simulation
-   initialize
-   start
-   pause
-   resume
-   reset
-   stop
-   retrieve state

Simulation should have a unique ID.

------------------------------------------------------------------------

# 27. Simulation Engine

The simulation engine should run independently from request/response
handlers.

Possible abstraction:

SimulationEngine - initialize() - step() - run() - pause() - resume() -
reset() - stop() - get_state()

The engine should expose state snapshots.

------------------------------------------------------------------------

# 28. Simulation State Snapshot

A state snapshot should be serializable and suitable for frontend
updates.

It may contain:

-   simulation ID
-   simulation time
-   status
-   crowd summary
-   node occupancy
-   edge occupancy
-   density
-   queues
-   risk
-   bottlenecks
-   routes
-   emergency state
-   AI recommendation reference/current result

Do not transmit unnecessary raw internal state.

Use compact payloads for real-time communication.

------------------------------------------------------------------------

# 29. Real-Time Communication

Provide one centralized real-time communication mechanism.

The real-time layer should:

-   manage connections
-   subscribe clients to simulation IDs
-   publish simulation snapshots
-   publish risk alerts
-   publish route changes
-   publish emergency events
-   publish AI recommendations

Do not let the simulation engine know about individual frontend clients.

Use:

Simulation Engine ↓ Event / State Publisher ↓ Real-Time Connection
Manager ↓ Connected Clients

------------------------------------------------------------------------

# 30. Real-Time Event Types

Define explicit event types.

Examples:

-   simulation.started
-   simulation.paused
-   simulation.updated
-   simulation.completed
-   metrics.updated
-   risk.updated
-   bottleneck.detected
-   bottleneck.cleared
-   route.changed
-   emergency.started
-   emergency.updated
-   emergency.resolved
-   ai.analysis.updated
-   connection/status events where necessary

Every event should have a predictable schema.

------------------------------------------------------------------------

# 31. AI Safety Analyst

The safety analyst receives structured simulation information.

Input:

-   crowd metrics
-   risk score
-   bottlenecks
-   current routes
-   route changes
-   emergency events
-   relevant venue context

Pipeline:

Simulation Results ↓ Result Aggregation ↓ Safety Context Construction ↓
Prompt Construction ↓ Qwen Model ↓ Risk Interpretation ↓ Safety
Reasoning ↓ Recommendation Generation ↓ Output Validation ↓ Structured
AI Result

The AI should not be asked to calculate authoritative numerical risk.

The deterministic risk engine owns numerical risk.

The AI explains the result.

------------------------------------------------------------------------

# 32. AI Safety Output

Return structured output such as:

-   summary
-   risk explanation
-   affected locations
-   contributing factors
-   recommended action
-   urgency
-   supporting metrics
-   generated timestamp

Example:

{ "summary": "High congestion is developing in the north corridor.",
"risk_explanation": "Capacity utilization is increasing while outflow
remains constrained.", "affected_locations": \["north_corridor"\],
"recommended_action": "Redirect incoming flow toward the west
corridor.", "urgency": "high" }

Validate the AI response before sending it to the frontend.

------------------------------------------------------------------------

# 33. AI Failure Handling

AI is non-critical to the deterministic simulation.

If AI fails:

-   simulation continues
-   risk engine continues
-   routing continues
-   frontend receives normal simulation state
-   AI status indicates unavailable

Never allow an AI timeout to stop the simulation.

Use timeout and retry policies.

------------------------------------------------------------------------

# 34. AI Scenario Parser Failure Handling

If natural-language parsing fails:

-   return a validation error
-   show which information could not be extracted
-   allow the user to edit structured fields manually

Never invent critical scenario parameters.

------------------------------------------------------------------------

# 35. Persistence

Persistence is optional for the simulation itself but should support
reusable application data.

Store:

-   venue layouts
-   scenario definitions
-   event schedules
-   simulation metadata
-   simulation history
-   relevant summary results

Avoid storing every high-frequency simulation tick permanently by
default.

Use configurable persistence frequency or summary snapshots.

------------------------------------------------------------------------

# 36. Database Repository Layer

Do not directly access the database from domain logic.

Use repository abstractions.

Examples:

VenueRepository ScenarioRepository SimulationRepository EventRepository

This allows tests and future storage changes without rewriting domain
logic.

------------------------------------------------------------------------

# 37. API Design

Provide REST-style endpoints for management operations.

Conceptual endpoints:

## Venues

POST /venues GET /venues GET /venues/{venue_id} PUT /venues/{venue_id}

## Scenarios

POST /scenarios GET /scenarios GET /scenarios/{scenario_id}

## AI Scenario Parsing

POST /scenarios/parse

Input:

natural language

Output:

structured scenario + validation status

## Simulations

POST /simulations GET /simulations/{simulation_id} POST
/simulations/{simulation_id}/start POST
/simulations/{simulation_id}/pause POST
/simulations/{simulation_id}/resume POST
/simulations/{simulation_id}/reset POST
/simulations/{simulation_id}/stop

## State

GET /simulations/{simulation_id}/state

## Emergency

POST /simulations/{simulation_id}/emergencies

## Routes

GET /simulations/{simulation_id}/routes

Exact endpoint naming may be adapted to the existing repository.

------------------------------------------------------------------------

# 38. API Validation

Every endpoint must validate:

-   IDs
-   request structure
-   numerical ranges
-   enum values
-   references to venue entities
-   simulation state transitions

Return consistent error structures.

------------------------------------------------------------------------

# 39. Configuration

Configuration should cover:

-   simulation timestep
-   maximum simulation duration
-   risk thresholds
-   bottleneck thresholds
-   routing weights
-   route-change cooldown
-   AI timeout
-   AI model configuration
-   real-time update frequency
-   persistence behavior
-   logging level

Use environment/configuration rather than hardcoded constants.

------------------------------------------------------------------------

# 40. Performance Requirements

The backend should be designed for continuous simulation.

Avoid:

-   blocking API handlers
-   blocking AI calls inside simulation steps
-   unnecessary graph reconstruction
-   repeated full-state serialization
-   database writes every simulation tick
-   one network request per agent

Prefer:

-   in-memory active simulation state
-   batched updates
-   compact snapshots
-   asynchronous processing
-   cached graph structures
-   configurable update frequency

------------------------------------------------------------------------

# 41. Concurrency

Multiple simulations may exist.

Simulation state must be isolated by simulation ID.

Do not use mutable global simulation state.

The system should prevent race conditions around:

-   pause/resume
-   emergency events
-   route updates
-   reset
-   stop
-   concurrent control commands

Use appropriate synchronization at the application/simulation level.

------------------------------------------------------------------------

# 42. Testing

Create tests for:

## Graph

-   node creation
-   edge creation
-   capacity
-   disabled routes
-   pathfinding

## Simulation

-   crowd generation
-   movement
-   destination selection
-   queue formation
-   capacity constraints

## Metrics

-   density
-   flow
-   speed
-   queue growth
-   utilization

## Risk

-   thresholds
-   severity
-   bottleneck detection
-   prediction
-   time-to-critical

## Routing

-   congestion-aware routes
-   alternative routes
-   emergency rerouting
-   route stability

## AI

-   structured parsing
-   schema validation
-   malformed model output
-   timeout/failure
-   safety analyst output validation

## API

-   validation
-   lifecycle
-   emergency endpoint
-   state retrieval

## Real-Time

-   connection management
-   simulation subscription
-   event broadcasting

------------------------------------------------------------------------

# 43. Logging

Use structured logging.

Important events:

-   simulation created
-   simulation started
-   simulation stopped
-   bottleneck detected
-   risk changed
-   route changed
-   emergency triggered
-   AI analysis failed
-   AI analysis completed
-   connection failures
-   unexpected simulation errors

Avoid logging sensitive or unnecessarily large payloads.

------------------------------------------------------------------------

# 44. Error Handling

Create domain-specific errors where useful.

Examples:

-   VenueNotFound
-   InvalidScenario
-   InvalidSimulationState
-   SimulationNotFound
-   InvalidRoute
-   EmergencyInvalid
-   AIProcessingError
-   PathNotFound
-   CapacityConfigurationError

Convert these into consistent API responses.

------------------------------------------------------------------------

# 45. Health / Observability

Provide a health endpoint.

At minimum expose:

-   application health
-   database health if persistence is enabled
-   AI service status where relevant

Do not expose secrets.

------------------------------------------------------------------------

# 46. Docker / Local Development

The backend should be runnable consistently in development.

Provide:

-   environment example
-   container configuration if appropriate
-   database configuration
-   migration instructions
-   development startup instructions

Keep external dependencies configurable.

------------------------------------------------------------------------

# 47. Mock / Development Mode

The backend should support development without requiring the AI service
to be available.

Provide a deterministic/mock AI adapter.

Example:

AIProvider interface

Implementations:

-   HuggingFaceAIProvider
-   MockAIProvider

Similarly, keep simulation data generation deterministic for
development.

------------------------------------------------------------------------

# 48. AI Provider Abstraction

Do not tightly couple domain logic to one model provider.

Use an abstraction such as:

AIProvider ├── parse_scenario() └── analyze_safety()

The current implementation may use Qwen through the selected
model-serving/inference mechanism, but replacing it later should not
require changes to the simulation engine.

------------------------------------------------------------------------

# 49. Domain Event Architecture

Where useful, use domain events.

Examples:

BottleneckDetected RiskChanged RouteChanged EmergencyTriggered
SimulationStateChanged AIAnalysisUpdated

The event publisher should be decoupled from the core simulation logic.

This makes real-time communication and future integrations easier.

------------------------------------------------------------------------

# 50. Important Data Flow

## Normal flow

Scenario → Scenario validation → Venue graph → Crowd generation →
Destination selection → Simulation → Metrics → Risk → Routing →
Simulation update → AI interpretation → Real-time state → Frontend

## Emergency flow

Emergency → Validate → Modify graph/capacity → Recalculate routes →
Redistribute flow → Simulate → Metrics → Risk → AI analysis → Real-time
update

------------------------------------------------------------------------

# 51. Frontend Contract

The frontend expects the backend to provide enough information to
display:

-   venue nodes
-   venue edges
-   crowd/flow state
-   density
-   bottlenecks
-   risk
-   routes
-   route changes
-   emergency state
-   AI recommendations

Do not force the frontend to infer authoritative risk from raw data.

Provide explicit derived values where the backend owns the calculation.

------------------------------------------------------------------------

# 52. Example Live State

Conceptually:

{ "simulation_id": "sim_001", "time": 1240, "status": "running",

"crowd": { "total": 18420, "active": 17200, "queued": 1220, "exited": 0
},

"metrics": { "density": {...}, "flow_rate": {...}, "average_speed":
{...}, "queue_growth": {...}, "capacity_utilization": {...} },

"risk": { "score": 0.72, "severity": "high", "time_to_critical": 420 },

"bottlenecks": \[ { "location_id": "north_corridor", "severity": "high",
"utilization": 0.87 } \],

"routes": { "active": \[...\], "alternative": \[...\], "disabled":
\[...\] },

"emergency": null,

"ai": { "status": "available", "recommendation": "Redirect incoming
flow..." } }

This is illustrative; define proper schemas in the implementation.

------------------------------------------------------------------------

# 53. Development Strategy

Implement incrementally.

## Phase 1

Build:

-   project structure
-   configuration
-   domain models
-   venue graph
-   basic API
-   health endpoint

## Phase 2

Build:

-   crowd generator
-   agents/groups
-   movement
-   queues
-   simulation lifecycle

## Phase 3

Build:

-   metrics
-   risk
-   bottleneck detection
-   time-to-critical

## Phase 4

Build:

-   dynamic routing
-   alternative paths
-   redistribution
-   route stability

## Phase 5

Build:

-   emergency handling
-   real-time event architecture

## Phase 6

Build:

-   AI scenario parser
-   structured validation
-   AI safety analyst

## Phase 7

Build:

-   persistence
-   historical simulation
-   production hardening
-   tests
-   observability

Do not build the AI first. The deterministic simulation must work
independently.

------------------------------------------------------------------------

# 54. Definition of Done

The backend is considered complete when:

-   A venue can be represented as a graph.
-   A scenario can be created and validated.
-   Crowd flow can be simulated.
-   Queues can form.
-   Metrics are calculated.
-   Bottlenecks are detected.
-   Risk is calculated.
-   Time-to-critical can be estimated where possible.
-   Routes respond to congestion.
-   Crowd flow can be redistributed.
-   Emergency route closures work.
-   Simulation lifecycle works.
-   Live state can be streamed.
-   AI can parse natural-language scenarios.
-   AI can explain simulation safety results.
-   AI failure does not stop deterministic simulation.
-   Data can be persisted.
-   Tests cover core domain logic.
-   The system can run locally reproducibly.
-   The frontend can consume a clean, typed/structured API and real-time
    contract.

------------------------------------------------------------------------

# 55. Critical Architectural Rule

Do not turn this into a CRUD application with a simulation attached.

The central product is the simulation and decision loop:

Crowd → Movement → Metrics → Risk → Routing → Crowd Redistribution →
Metrics → Risk → AI Interpretation

The backend must preserve this feedback loop.

The API, database, real-time layer, and AI layer are supporting systems
around this core.

Build the system so that the simulation engine can eventually become
more sophisticated without requiring a rewrite of the API, AI, database,
or frontend integration.

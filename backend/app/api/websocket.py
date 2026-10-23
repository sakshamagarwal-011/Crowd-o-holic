from __future__ import annotations

"""
WebSocket endpoint — one centralized connection per simulation.
Frontend connects to WS /ws/simulations/{simulation_id} and receives
SimSnapshot events. All components share this single connection.
"""

import json
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.realtime.connection_manager import connection_manager
from app.realtime.broadcaster import build_snapshot
from app.realtime.events import make_connection_event, make_error_event, make_event
from app.services import simulation_service
from app.services.venue_service import get_venue_for_simulation
from app.services.ai_service import get_ai_provider
from app.simulation.generator import default_scenario_dict
from app.core.logging import get_logger

log = get_logger(__name__)

router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws/simulations/{simulation_id}")
async def websocket_endpoint(websocket: WebSocket, simulation_id: str):
    """
    WebSocket endpoint for a simulation.
    - Sends connection.status on connect
    - Sends immediate snapshot
    - Receives control messages from client (optional)
    - Handles disconnect/reconnect cleanly
    """
    await connection_manager.connect(websocket, simulation_id)

    try:
        # Ensure simulation exists — create default if needed
        try:
            engine = simulation_service.get_simulation(simulation_id)
        except Exception:
            if simulation_id == "default":
                scenario = default_scenario_dict()
                graph = get_venue_for_simulation("venue-stadium-a")
                ai = get_ai_provider()
                engine = simulation_service.create_simulation(
                    scenario=scenario,
                    graph=graph,
                    ai_provider=ai,
                    seed=42,
                    simulation_id="default",
                )
                log.info("Auto-created default simulation for WS connection")
            else:
                await connection_manager.send_to(
                    websocket,
                    make_error_event("simulation_not_found", f"Simulation '{simulation_id}' not found"),
                )
                return

        # Send connection status
        await connection_manager.send_to(
            websocket,
            make_connection_event("live", f"Connected to simulation {simulation_id}"),
        )

        # Send immediate snapshot so frontend renders immediately
        metrics, safety = engine.get_snapshot_data()
        snapshot = build_snapshot(engine.state, engine.graph, metrics, safety)
        await connection_manager.send_to(
            websocket,
            make_event("simulation.updated", snapshot),
        )

        # Listen for incoming messages (control commands from frontend)
        while True:
            try:
                raw = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                await _handle_client_message(websocket, engine, raw)
            except asyncio.TimeoutError:
                # Send keepalive
                await connection_manager.send_to(
                    websocket,
                    make_connection_event("live", "keepalive"),
                )

    except WebSocketDisconnect:
        log.info("WS client disconnected | sim=%s", simulation_id)
    except Exception as e:
        log.warning("WS error | sim=%s error=%s", simulation_id, e)
        try:
            await connection_manager.send_to(
                websocket,
                make_error_event("ws_error", str(e)),
            )
        except Exception:
            pass
    finally:
        await connection_manager.disconnect(websocket, simulation_id)


async def _handle_client_message(websocket: WebSocket, engine, raw: str) -> None:
    """Handle control messages from the frontend client."""
    try:
        msg = json.loads(raw)
        action = msg.get("action")

        if action == "start":
            try:
                engine.start()
            except ValueError as e:
                await connection_manager.send_to(
                    websocket, make_error_event("state_error", str(e))
                )
        elif action == "pause":
            try:
                engine.pause()
            except ValueError as e:
                await connection_manager.send_to(
                    websocket, make_error_event("state_error", str(e))
                )
        elif action == "resume":
            try:
                engine.resume()
            except ValueError as e:
                await connection_manager.send_to(
                    websocket, make_error_event("state_error", str(e))
                )
        elif action == "reset":
            engine.reset()
        elif action == "set_speed":
            mult = msg.get("multiplier", 1.0)
            engine.set_speed(float(mult))
        elif action == "trigger_emergency":
            from app.emergency.manager import trigger_emergency
            trigger_emergency(
                engine.state, engine.graph,
                msg.get("type", "fire"),
                msg.get("node_id", "j-n"),
            )
        elif action == "clear_emergency":
            from app.emergency.manager import clear_emergency
            clear_emergency(engine.state, engine.graph)
        elif action == "ack_alert":
            engine.acknowledge_alert(msg.get("alert_id", ""))

    except json.JSONDecodeError:
        pass
    except Exception as e:
        log.warning("WS message handling error: %s", e)

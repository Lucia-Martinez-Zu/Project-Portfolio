"""
Flask + Flask-SocketIO entry point for Yana Robots.

Run with:
    python run.py

Environment variables:
    TELEMETRY_SOURCE   "simulator" (default) or "ros2"
    UPDATE_HZ          telemetry update rate (default 5)
    PORT               server port (default 5000)
"""

from __future__ import annotations

import threading
from typing import List

from flask import Flask, jsonify, render_template
from flask_socketio import SocketIO

from .config import Config


def create_app() -> tuple[Flask, SocketIO, object]:
    """Application factory.

    Returns (app, socketio, telemetry_source).
    """
    app = Flask(
        __name__,
        template_folder="../templates",
        static_folder="../static",
    )
    app.config.from_object(Config)

    socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

    # Shared state guarded by a lock — last snapshot per robot
    state_lock = threading.Lock()
    latest_snapshot: List[dict] = []

    def on_update(robots: List[dict]) -> None:
        nonlocal latest_snapshot
        with state_lock:
            latest_snapshot = robots
        # Broadcast to every connected client
        socketio.emit("telemetry", {"robots": robots})

    # ---------- Telemetry source ----------
    source = app.config["TELEMETRY_SOURCE"].lower()
    update_hz = float(app.config["UPDATE_HZ"])

    if source == "ros2":
        from .ros_bridge import Ros2BridgeRunner

        telemetry = Ros2BridgeRunner(on_update=on_update, update_hz=update_hz)
        app.logger.info("Telemetry source: ROS 2")
    else:
        from .simulator import TelemetrySimulator

        telemetry = TelemetrySimulator(on_update=on_update, update_hz=update_hz)
        app.logger.info("Telemetry source: simulator")

    telemetry.start()

    # ---------- HTTP routes ----------
    @app.route("/")
    def index():
        return render_template(
            "index.html",
            update_hz=update_hz,
            source=source,
        )

    @app.route("/api/health")
    def health():
        return jsonify({
            "status": "ok",
            "source": source,
            "update_hz": update_hz,
        })

    @app.route("/api/snapshot")
    def snapshot():
        with state_lock:
            return jsonify({"robots": list(latest_snapshot)})

    # ---------- Socket.IO events ----------
    @socketio.on("connect")
    def on_connect():
        # Push current state to the new client immediately
        with state_lock:
            socketio.emit("telemetry", {"robots": list(latest_snapshot)})
        app.logger.info("Client connected")

    @socketio.on("disconnect")
    def on_disconnect():
        app.logger.info("Client disconnected")

    return app, socketio, telemetry

"""
Telemetry simulator for Yana Robots.

Generates realistic synthetic telemetry data for one or more mobile robots,
allowing the dashboard to be tested without an actual ROS 2 setup.

Each robot follows a Lissajous-curve path inside a virtual map and slowly
drains its battery. Random warnings are injected occasionally.
"""

from __future__ import annotations

import math
import random
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Dict, List


@dataclass
class RobotState:
    """Mutable state of a single simulated robot."""

    robot_id: str
    model: str
    color: str

    # Pose
    x: float = 0.0
    y: float = 0.0
    theta: float = 0.0

    # Velocity
    linear: float = 0.0
    angular: float = 0.0

    # Battery
    battery_level: float = 100.0  # percent
    battery_voltage: float = 12.6
    charging: bool = False

    # Status
    status: str = "idle"  # idle | moving | charging | error
    errors: List[str] = field(default_factory=list)

    # Internal
    _phase: float = 0.0  # for path generation
    _last_update: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "robot_id": self.robot_id,
            "model": self.model,
            "color": self.color,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "pose": {
                "x": round(self.x, 3),
                "y": round(self.y, 3),
                "theta": round(self.theta, 3),
            },
            "velocity": {
                "linear": round(self.linear, 3),
                "angular": round(self.angular, 3),
            },
            "battery": {
                "level": round(self.battery_level, 2),
                "voltage": round(self.battery_voltage, 2),
                "charging": self.charging,
            },
            "status": self.status,
            "errors": list(self.errors),
        }


class TelemetrySimulator:
    """Background thread that updates one or more RobotState instances.

    Parameters
    ----------
    on_update : callable
        Callback invoked with a list of robot dicts each tick.
    update_hz : float
        Update frequency in Hz. Default 5 Hz.
    """

    # Demo fleet — three Yana service robots with different roles.
    DEFAULT_FLEET = [
        {"robot_id": "YANA-D01", "model": "Delivery", "color": "#FF6B35"},
        {"robot_id": "YANA-D02", "model": "Delivery", "color": "#2EC4B6"},
        {"robot_id": "YANA-S01", "model": "Service",  "color": "#8338EC"},
    ]

    POSSIBLE_ERRORS = [
        "Lectura LiDAR fuera de rango",
        "IMU desviación en yaw",
        "Voltaje de batería bajo",
        "Pérdida temporal de odometría",
        "Obstáculo detectado en zona crítica",
    ]

    def __init__(
        self,
        on_update: Callable[[List[dict]], None],
        update_hz: float = 5.0,
        fleet: List[Dict] | None = None,
    ):
        self.on_update = on_update
        self.dt = 1.0 / update_hz
        self.update_hz = update_hz

        fleet = fleet or self.DEFAULT_FLEET
        self.robots: Dict[str, RobotState] = {}
        for i, spec in enumerate(fleet):
            state = RobotState(**spec)
            state.battery_level = random.uniform(60.0, 100.0)
            state._phase = i * 1.7  # offset starting positions
            state.x = 5.0 * math.cos(state._phase)
            state.y = 5.0 * math.sin(state._phase)
            self.robots[state.robot_id] = state

        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run, name="telemetry-simulator", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2.0)

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------
    def _run(self) -> None:
        next_tick = time.time()
        while not self._stop.is_set():
            now = time.time()
            for robot in self.robots.values():
                self._update_robot(robot, now)

            try:
                self.on_update([r.to_dict() for r in self.robots.values()])
            except Exception as exc:  # pragma: no cover — defensive
                # We never want a callback failure to kill the simulator.
                print(f"[simulator] on_update failed: {exc}")

            next_tick += self.dt
            sleep_for = max(0.0, next_tick - time.time())
            time.sleep(sleep_for)

    # ------------------------------------------------------------------
    # Per-robot physics
    # ------------------------------------------------------------------
    def _update_robot(self, robot: RobotState, now: float) -> None:
        elapsed = now - robot._last_update
        robot._last_update = now
        robot._phase += self.dt * 0.4  # advance path phase

        # Lissajous-style motion inside a 20 x 20 meter virtual map.
        prev_x, prev_y = robot.x, robot.y
        robot.x = 7.0 * math.sin(1.3 * robot._phase + 0.5)
        robot.y = 5.0 * math.sin(0.7 * robot._phase)

        dx = robot.x - prev_x
        dy = robot.y - prev_y
        distance = math.hypot(dx, dy)
        robot.linear = distance / max(self.dt, 1e-3)

        new_theta = math.atan2(dy, dx) if distance > 1e-4 else robot.theta
        # angular velocity = wrapped angle difference / dt
        angle_diff = math.atan2(math.sin(new_theta - robot.theta),
                                math.cos(new_theta - robot.theta))
        robot.angular = angle_diff / max(self.dt, 1e-3)
        robot.theta = new_theta

        # Battery dynamics
        if robot.charging:
            robot.battery_level = min(100.0, robot.battery_level + elapsed * 2.0)
            if robot.battery_level >= 99.5:
                robot.charging = False
        else:
            # ~0.05 % per tick at 5 Hz ≈ slow drain
            drain = 0.04 + 0.02 * abs(robot.linear)
            robot.battery_level = max(0.0, robot.battery_level - drain * elapsed)
            if robot.battery_level < 15.0 and random.random() < 0.001:
                robot.charging = True  # auto-dock
                robot.status = "charging"

        robot.battery_voltage = 11.0 + 1.6 * (robot.battery_level / 100.0)

        # Status logic
        if robot.charging:
            robot.status = "charging"
        elif robot.linear > 0.05:
            robot.status = "moving"
        else:
            robot.status = "idle"

        # Random warnings (low probability)
        if random.random() < 0.002:
            error = random.choice(self.POSSIBLE_ERRORS)
            if error not in robot.errors:
                robot.errors.append(error)
                robot.status = "warning"
        # Auto-clear old errors
        if robot.errors and random.random() < 0.01:
            robot.errors.pop(0)

    # ------------------------------------------------------------------
    # Snapshot
    # ------------------------------------------------------------------
    def snapshot(self) -> List[dict]:
        return [r.to_dict() for r in self.robots.values()]

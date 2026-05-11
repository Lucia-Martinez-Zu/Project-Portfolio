"""
ROS 2 ↔ Flask bridge.

This module is imported only when ``TELEMETRY_SOURCE=ros2``. It subscribes to
a configurable set of topics and pushes the consolidated state to the same
``on_update`` callback used by the simulator, so the rest of the app does not
care about the source of the data.

Topics consumed (defaults, can be remapped):
  - /odom               (nav_msgs/Odometry)
  - /battery_state      (sensor_msgs/BatteryState)
  - /diagnostics        (diagnostic_msgs/DiagnosticArray)

If ``rclpy`` is not installed this file will raise ``ImportError`` cleanly,
so the user knows they need a ROS 2 environment.
"""

from __future__ import annotations

import math
import threading
from datetime import datetime, timezone
from typing import Callable, List

try:
    import rclpy
    from rclpy.node import Node
    from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
    from nav_msgs.msg import Odometry
    from sensor_msgs.msg import BatteryState
    from diagnostic_msgs.msg import DiagnosticArray
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "ROS 2 (rclpy + standard message packages) is required for the ROS 2 "
        "bridge. Either install ROS 2 Humble (or newer) or run with "
        "TELEMETRY_SOURCE=simulator."
    ) from exc


def _quat_to_yaw(qx: float, qy: float, qz: float, qw: float) -> float:
    siny_cosp = 2.0 * (qw * qz + qx * qy)
    cosy_cosp = 1.0 - 2.0 * (qy * qy + qz * qz)
    return math.atan2(siny_cosp, cosy_cosp)


class TelemetryBridge(Node):
    """ROS 2 node that aggregates telemetry for a single robot."""

    def __init__(self, robot_id: str = "robot-001",
                 model: str = "ROS2", color: str = "#FF6B35"):
        super().__init__("yana_telemetry_bridge")

        qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            history=HistoryPolicy.KEEP_LAST,
            depth=10,
        )

        self.robot_id = robot_id
        self.model = model
        self.color = color

        self._state = {
            "robot_id": robot_id,
            "model": model,
            "color": color,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "pose": {"x": 0.0, "y": 0.0, "theta": 0.0},
            "velocity": {"linear": 0.0, "angular": 0.0},
            "battery": {"level": 100.0, "voltage": 12.6, "charging": False},
            "status": "idle",
            "errors": [],
        }
        self._lock = threading.Lock()

        self.create_subscription(Odometry, "/odom", self._on_odom, qos)
        self.create_subscription(
            BatteryState, "/battery_state", self._on_battery, qos
        )
        self.create_subscription(
            DiagnosticArray, "/diagnostics", self._on_diagnostics, qos
        )

        self.get_logger().info(
            f"Yana Robots bridge subscribed for robot {robot_id}"
        )

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------
    def _on_odom(self, msg: Odometry) -> None:
        with self._lock:
            p = msg.pose.pose.position
            q = msg.pose.pose.orientation
            v = msg.twist.twist
            self._state["pose"] = {
                "x": round(p.x, 3),
                "y": round(p.y, 3),
                "theta": round(_quat_to_yaw(q.x, q.y, q.z, q.w), 3),
            }
            self._state["velocity"] = {
                "linear": round(v.linear.x, 3),
                "angular": round(v.angular.z, 3),
            }
            if abs(v.linear.x) > 0.05:
                self._state["status"] = "moving"
            else:
                self._state["status"] = "idle"

    def _on_battery(self, msg: BatteryState) -> None:
        with self._lock:
            level = msg.percentage * 100.0 if msg.percentage <= 1.0 else msg.percentage
            self._state["battery"] = {
                "level": round(float(level), 2),
                "voltage": round(float(msg.voltage), 2),
                "charging": msg.power_supply_status == 1,  # POWER_SUPPLY_STATUS_CHARGING
            }
            if msg.power_supply_status == 1:
                self._state["status"] = "charging"

    def _on_diagnostics(self, msg: DiagnosticArray) -> None:
        with self._lock:
            errors: List[str] = []
            for entry in msg.status:
                # level: 0 OK, 1 WARN, 2 ERROR, 3 STALE
                if entry.level >= 1:
                    errors.append(f"{entry.name}: {entry.message}")
            self._state["errors"] = errors[:5]
            if errors:
                self._state["status"] = "warning"

    # ------------------------------------------------------------------
    # Snapshot accessor used by the publisher loop
    # ------------------------------------------------------------------
    def snapshot(self) -> List[dict]:
        with self._lock:
            self._state["timestamp"] = datetime.now(timezone.utc).isoformat()
            return [dict(self._state)]


class Ros2BridgeRunner:
    """
    Spawns rclpy in a background thread and periodically publishes the
    current state to the ``on_update`` callback at ``update_hz``.
    """

    def __init__(
        self,
        on_update: Callable[[List[dict]], None],
        update_hz: float = 5.0,
        robot_id: str = "robot-001",
    ):
        self.on_update = on_update
        self.update_hz = update_hz
        self.robot_id = robot_id

        self._stop = threading.Event()
        self._spin_thread: threading.Thread | None = None
        self._publish_thread: threading.Thread | None = None
        self._node: TelemetryBridge | None = None

    def start(self) -> None:
        rclpy.init(args=None)
        self._node = TelemetryBridge(robot_id=self.robot_id)

        self._spin_thread = threading.Thread(
            target=rclpy.spin, args=(self._node,), daemon=True,
            name="ros2-spin",
        )
        self._spin_thread.start()

        self._publish_thread = threading.Thread(
            target=self._publish_loop, daemon=True, name="ros2-publish",
        )
        self._publish_thread.start()

    def _publish_loop(self) -> None:
        import time
        period = 1.0 / self.update_hz
        while not self._stop.is_set():
            try:
                self.on_update(self._node.snapshot())
            except Exception as exc:  # pragma: no cover
                print(f"[ros2_bridge] on_update failed: {exc}")
            time.sleep(period)

    def stop(self) -> None:
        self._stop.set()
        if self._node is not None:
            self._node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()

    def snapshot(self) -> List[dict]:
        return self._node.snapshot() if self._node else []

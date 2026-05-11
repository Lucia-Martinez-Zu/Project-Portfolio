#!/usr/bin/env python3
"""
ROS 2 publisher that emits synthetic telemetry on the topics the bridge
subscribes to: /odom, /battery_state, /diagnostics.

Use this to test the dashboard with a real ROS 2 environment without
requiring a physical robot. Run from a sourced ROS 2 Humble (or newer)
shell:

    python3 telemetry_publisher.py
"""

import math
import time

import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
from sensor_msgs.msg import BatteryState
from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue
from geometry_msgs.msg import Quaternion


def yaw_to_quaternion(yaw: float) -> Quaternion:
    q = Quaternion()
    q.x = 0.0
    q.y = 0.0
    q.z = math.sin(yaw / 2.0)
    q.w = math.cos(yaw / 2.0)
    return q


class FakeRobot(Node):
    def __init__(self):
        super().__init__("yana_fake_robot")
        self.odom_pub = self.create_publisher(Odometry, "/odom", 10)
        self.batt_pub = self.create_publisher(BatteryState, "/battery_state", 10)
        self.diag_pub = self.create_publisher(DiagnosticArray, "/diagnostics", 10)

        self.create_timer(0.1, self.tick)  # 10 Hz

        self.t0 = time.time()
        self.battery = 100.0
        self.get_logger().info("Fake robot publishing synthetic telemetry")

    def tick(self):
        t = time.time() - self.t0

        # Odometry
        x = 7.0 * math.sin(1.3 * t * 0.4 + 0.5)
        y = 5.0 * math.sin(0.7 * t * 0.4)
        yaw = math.atan2(math.cos(0.7 * t * 0.4), math.cos(1.3 * t * 0.4 + 0.5))

        odom = Odometry()
        odom.header.stamp = self.get_clock().now().to_msg()
        odom.header.frame_id = "odom"
        odom.child_frame_id = "base_link"
        odom.pose.pose.position.x = x
        odom.pose.pose.position.y = y
        odom.pose.pose.position.z = 0.0
        odom.pose.pose.orientation = yaw_to_quaternion(yaw)
        odom.twist.twist.linear.x = 0.5 + 0.3 * math.sin(t)
        odom.twist.twist.angular.z = 0.4 * math.cos(t)
        self.odom_pub.publish(odom)

        # Battery
        self.battery = max(0.0, self.battery - 0.01)
        batt = BatteryState()
        batt.header.stamp = odom.header.stamp
        batt.percentage = self.battery / 100.0
        batt.voltage = 11.0 + 1.6 * (self.battery / 100.0)
        batt.power_supply_status = (
            BatteryState.POWER_SUPPLY_STATUS_CHARGING
            if self.battery < 15.0
            else BatteryState.POWER_SUPPLY_STATUS_DISCHARGING
        )
        self.batt_pub.publish(batt)

        # Occasional diagnostic
        if int(t) % 30 == 0 and t - int(t) < 0.1:
            diag = DiagnosticArray()
            diag.header.stamp = odom.header.stamp
            entry = DiagnosticStatus()
            entry.level = DiagnosticStatus.WARN
            entry.name = "lidar/health"
            entry.message = "Reading out of range (sample warning)"
            entry.values.append(KeyValue(key="device", value="rplidar_a2"))
            diag.status.append(entry)
            self.diag_pub.publish(diag)


def main():
    rclpy.init()
    node = FakeRobot()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()

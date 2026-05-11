"""Application configuration."""

import os


class Config:
    """Base configuration."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me")

    # Telemetry source: "simulator" or "ros2"
    TELEMETRY_SOURCE = os.environ.get("TELEMETRY_SOURCE", "simulator")

    # Update rate at which telemetry is broadcasted to clients
    UPDATE_HZ = float(os.environ.get("UPDATE_HZ", "5"))

    # ROS 2 specific (only used when TELEMETRY_SOURCE == "ros2")
    ROS_DOMAIN_ID = int(os.environ.get("ROS_DOMAIN_ID", "0"))
    ROS_NAMESPACE = os.environ.get("ROS_NAMESPACE", "")

    # Server
    HOST = os.environ.get("HOST", "0.0.0.0")
    PORT = int(os.environ.get("PORT", "5000"))
    DEBUG = os.environ.get("FLASK_DEBUG", "0") == "1"

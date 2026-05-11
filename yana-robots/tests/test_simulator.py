"""Smoke tests for the telemetry simulator.

Run with:
    pip install pytest
    pytest tests/
"""

import time

from app.simulator import TelemetrySimulator


def test_default_fleet_has_three_robots():
    sim = TelemetrySimulator(on_update=lambda _: None)
    snapshot = sim.snapshot()
    assert len(snapshot) == 3
    ids = {r["robot_id"] for r in snapshot}
    assert ids == {"YANA-D01", "YANA-D02", "YANA-S01"}


def test_snapshot_schema():
    sim = TelemetrySimulator(on_update=lambda _: None)
    robot = sim.snapshot()[0]
    for key in (
        "robot_id", "model", "color", "timestamp",
        "pose", "velocity", "battery", "status", "errors",
    ):
        assert key in robot

    assert {"x", "y", "theta"} == set(robot["pose"].keys())
    assert {"linear", "angular"} == set(robot["velocity"].keys())
    assert {"level", "voltage", "charging"} == set(robot["battery"].keys())


def test_robots_actually_move():
    """After a few ticks, at least one robot must have changed pose."""
    received = []

    sim = TelemetrySimulator(on_update=received.append, update_hz=20)
    sim.start()
    time.sleep(0.4)
    sim.stop()

    assert len(received) >= 3, f"Expected several updates, got {len(received)}"

    first = {r["robot_id"]: (r["pose"]["x"], r["pose"]["y"]) for r in received[0]}
    last  = {r["robot_id"]: (r["pose"]["x"], r["pose"]["y"]) for r in received[-1]}

    moved = sum(1 for k in first if first[k] != last[k])
    assert moved >= 1, "No robot moved during the test window"


def test_battery_decreases_over_time():
    received = []
    sim = TelemetrySimulator(on_update=received.append, update_hz=50)
    sim.start()
    time.sleep(0.5)
    sim.stop()

    first_levels = {r["robot_id"]: r["battery"]["level"] for r in received[0]}
    last_levels  = {r["robot_id"]: r["battery"]["level"] for r in received[-1]}
    # At least one robot should have lost battery (charging is rare in the window)
    drained = sum(1 for k in first_levels if last_levels[k] < first_levels[k])
    assert drained >= 1

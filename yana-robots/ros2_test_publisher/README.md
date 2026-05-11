# ROS 2 Test Publisher

Synthetic ROS 2 publisher used to exercise the bridge end-to-end without
needing a physical robot.

## Requirements
- ROS 2 Humble (or newer)
- Python 3.10+

## Run

```bash
# In a ROS 2-sourced terminal
source /opt/ros/humble/setup.bash
python3 telemetry_publisher.py
```

In another terminal, run the dashboard with the ROS 2 source enabled:

```bash
source /opt/ros/humble/setup.bash
TELEMETRY_SOURCE=ros2 python run.py
```

You should see live odometry, battery and diagnostic events flowing into the
dashboard at http://localhost:5000.

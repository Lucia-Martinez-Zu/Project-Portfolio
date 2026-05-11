/**
 * Yana Robots — main client.
 *
 * Connects to the Flask-SocketIO server and renders incoming telemetry.
 */

(() => {
  // ----------------------------------------------------------------------
  //  State
  // ----------------------------------------------------------------------
  const state = {
    robots: new Map(),       // robot_id -> latest snapshot
    selectedId: null,
    history: new Map(),      // robot_id -> { battery: [], linear: [], angular: [], ts: [] }
    events: [],              // {ts, robot, level, msg}
    maxHistory: 60,
    maxEvents: 80,
  };

  // ----------------------------------------------------------------------
  //  DOM refs
  // ----------------------------------------------------------------------
  const dom = {
    list:        document.getElementById("robot-list"),
    dot:         document.getElementById("connection-dot"),
    status:      document.getElementById("connection-label"),
    kpiRobot:    document.getElementById("kpi-robot"),
    kpiBattery:  document.getElementById("kpi-battery"),
    kpiSpeed:    document.getElementById("kpi-speed"),
    kpiStatus:   document.getElementById("kpi-status"),
    eventLog:    document.getElementById("event-log"),
    clearBtn:    document.getElementById("clear-events"),
    legend:      document.getElementById("map-legend"),
  };

  // ----------------------------------------------------------------------
  //  Charts and map (provided by charts.js / map.js)
  // ----------------------------------------------------------------------
  const batteryChart  = YanaCharts.createBatteryChart("battery-chart");
  const velocityChart = YanaCharts.createVelocityChart("velocity-chart");
  const map           = YanaMap.create("map-canvas");

  // ----------------------------------------------------------------------
  //  Socket connection
  // ----------------------------------------------------------------------
  const socket = io({ transports: ["websocket", "polling"] });

  socket.on("connect", () => {
    dom.dot.classList.remove("dot-off");
    dom.dot.classList.add("dot-on");
    dom.status.textContent = "Connected";
  });
  socket.on("disconnect", () => {
    dom.dot.classList.remove("dot-on");
    dom.dot.classList.add("dot-off");
    dom.status.textContent = "Disconnected";
  });

  socket.on("telemetry", payload => {
    const robots = payload.robots || [];
    for (const robot of robots) {
      ingest(robot);
    }
    render();
  });

  // ----------------------------------------------------------------------
  //  Ingest a snapshot
  // ----------------------------------------------------------------------
  function ingest(robot) {
    const id = robot.robot_id;
    const previous = state.robots.get(id);
    state.robots.set(id, robot);

    // Build history per-robot
    if (!state.history.has(id)) {
      state.history.set(id, {
        battery: [], linear: [], angular: [], ts: [],
      });
    }
    const hist = state.history.get(id);
    hist.battery.push(robot.battery.level);
    hist.linear.push(robot.velocity.linear);
    hist.angular.push(robot.velocity.angular);
    hist.ts.push(robot.timestamp);

    while (hist.battery.length > state.maxHistory) {
      hist.battery.shift();
      hist.linear.shift();
      hist.angular.shift();
      hist.ts.shift();
    }

    // Detect new errors → event log
    if (previous) {
      const prev = new Set(previous.errors || []);
      for (const err of robot.errors || []) {
        if (!prev.has(err)) {
          pushEvent(robot.robot_id, "warn", err);
        }
      }
      if (previous.battery.charging !== robot.battery.charging) {
        pushEvent(
          robot.robot_id,
          "info",
          robot.battery.charging ? "Started charging" : "Resumed mission"
        );
      }
      if (previous.status !== robot.status && robot.status === "error") {
        pushEvent(robot.robot_id, "error", "Robot transitioned to ERROR state");
      }
    }

    if (state.selectedId === null) state.selectedId = id;
  }

  // ----------------------------------------------------------------------
  //  Event log
  // ----------------------------------------------------------------------
  function pushEvent(robotId, level, msg) {
    const ts = new Date().toLocaleTimeString();
    state.events.unshift({ ts, robot: robotId, level, msg });
    while (state.events.length > state.maxEvents) state.events.pop();
  }

  dom.clearBtn.addEventListener("click", () => {
    state.events = [];
    renderEvents();
  });

  // ----------------------------------------------------------------------
  //  Render
  // ----------------------------------------------------------------------
  function render() {
    renderRobotList();
    renderKpis();
    renderCharts();
    renderMap();
    renderEvents();
  }

  function renderRobotList() {
    if (state.robots.size === 0) return;
    dom.list.innerHTML = "";
    for (const robot of state.robots.values()) {
      const el = document.createElement("div");
      el.className = "robot-item";
      if (robot.robot_id === state.selectedId) el.classList.add("active");
      el.innerHTML = `
        <div class="row">
          <span class="robot-id" style="color:${robot.color}">●</span>
          <span class="robot-id">${escapeHtml(robot.robot_id)}</span>
          <span class="status-pill status-${robot.status}">${robot.status}</span>
        </div>
        <div class="row" style="margin-top:4px">
          <span class="robot-model">${escapeHtml(robot.model)}</span>
          <span class="robot-model">${robot.battery.level.toFixed(0)} %</span>
        </div>
        <div class="battery-bar">
          <span style="width:${robot.battery.level}%; background:${batteryColor(robot.battery.level)}"></span>
        </div>
      `;
      el.addEventListener("click", () => {
        state.selectedId = robot.robot_id;
        render();
      });
      dom.list.appendChild(el);
    }
  }

  function renderKpis() {
    const robot = state.robots.get(state.selectedId);
    if (!robot) return;
    dom.kpiRobot.textContent   = robot.robot_id;
    dom.kpiBattery.textContent = `${robot.battery.level.toFixed(1)} %`;
    dom.kpiBattery.style.color = batteryColor(robot.battery.level);
    dom.kpiSpeed.textContent   = `${Math.abs(robot.velocity.linear).toFixed(2)} m/s`;
    dom.kpiStatus.innerHTML    = `<span class="status-pill status-${robot.status}">${robot.status}</span>`;
  }

  function renderCharts() {
    const id = state.selectedId;
    if (!id) return;
    const hist = state.history.get(id);
    if (!hist) return;
    YanaCharts.update(batteryChart, hist.battery, hist.ts);
    YanaCharts.updateVelocity(velocityChart, hist.linear, hist.angular, hist.ts);
  }

  function renderMap() {
    const robots = Array.from(state.robots.values());
    map.draw(robots, state.selectedId);

    // Legend
    dom.legend.innerHTML = "";
    for (const r of robots) {
      const el = document.createElement("div");
      el.className = "map-legend-item";
      el.innerHTML = `<span class="swatch" style="background:${r.color}"></span>${escapeHtml(r.robot_id)}`;
      dom.legend.appendChild(el);
    }
  }

  function renderEvents() {
    if (state.events.length === 0) {
      dom.eventLog.innerHTML = `<div class="empty">No events yet</div>`;
      return;
    }
    dom.eventLog.innerHTML = state.events.map(e => `
      <div class="event ${e.level}">
        <span class="ts">${e.ts}</span>
        <span class="robot">${escapeHtml(e.robot)}</span>
        <span class="msg">${escapeHtml(e.msg)}</span>
      </div>`).join("");
  }

  // ----------------------------------------------------------------------
  //  Helpers
  // ----------------------------------------------------------------------
  function batteryColor(level) {
    if (level < 20) return "var(--red)";
    if (level < 40) return "var(--yellow)";
    return "var(--green)";
  }

  function escapeHtml(s) {
    return String(s)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }
})();

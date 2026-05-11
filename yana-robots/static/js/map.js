/**
 * Simple 2D top-down map.
 *
 * - World coordinates: ±10 m on each axis.
 * - Robots are drawn as colored discs with heading indicator.
 * - A trailing path of recent positions is preserved per robot.
 */

window.YanaMap = (function () {
  const TRAIL_LENGTH = 40;

  function create(canvasId) {
    const canvas = document.getElementById(canvasId);
    const ctx = canvas.getContext("2d");
    const trails = new Map();   // robot_id -> [{x,y}]

    function resize() {
      const rect = canvas.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      canvas.width  = rect.width  * dpr;
      canvas.height = rect.height * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }

    window.addEventListener("resize", resize);
    resize();

    /**
     * Translate world coords (meters) to canvas coords (pixels).
     */
    function worldToScreen(wx, wy, w, h) {
      // World spans roughly -10 .. 10 in both axes
      const margin = 24;
      const sx = margin + ((wx + 10) / 20) * (w - 2 * margin);
      const sy = margin + ((10 - wy) / 20) * (h - 2 * margin);
      return [sx, sy];
    }

    function drawGrid(w, h) {
      ctx.strokeStyle = "#1c2230";
      ctx.lineWidth = 1;
      ctx.beginPath();
      const margin = 24;
      const innerW = w - 2 * margin;
      const innerH = h - 2 * margin;
      const step = innerW / 8;

      for (let i = 0; i <= 8; i++) {
        const x = margin + i * step;
        ctx.moveTo(x, margin);
        ctx.lineTo(x, h - margin);
      }
      const stepY = innerH / 8;
      for (let i = 0; i <= 8; i++) {
        const y = margin + i * stepY;
        ctx.moveTo(margin, y);
        ctx.lineTo(w - margin, y);
      }
      ctx.stroke();

      // Outer frame
      ctx.strokeStyle = "#262C38";
      ctx.lineWidth = 1;
      ctx.strokeRect(margin, margin, innerW, innerH);

      // Origin cross
      ctx.strokeStyle = "#3a4252";
      ctx.beginPath();
      const [ox, oy] = worldToScreen(0, 0, w, h);
      ctx.moveTo(ox - 6, oy);
      ctx.lineTo(ox + 6, oy);
      ctx.moveTo(ox, oy - 6);
      ctx.lineTo(ox, oy + 6);
      ctx.stroke();

      // Axis labels
      ctx.fillStyle = "#5C6373";
      ctx.font = "10px ui-monospace, monospace";
      ctx.fillText("0,0", ox + 8, oy - 4);
      ctx.fillText("+10 m", w - margin - 32, oy - 4);
      ctx.fillText("+10 m", ox + 4, margin + 12);
    }

    function drawRobot(robot, isSelected, w, h) {
      const trail = trails.get(robot.robot_id);
      if (trail && trail.length > 1) {
        ctx.strokeStyle = robot.color + "55";  // alpha-ish
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        for (let i = 0; i < trail.length; i++) {
          const [tx, ty] = worldToScreen(trail[i].x, trail[i].y, w, h);
          if (i === 0) ctx.moveTo(tx, ty);
          else ctx.lineTo(tx, ty);
        }
        ctx.stroke();
      }

      const [sx, sy] = worldToScreen(robot.pose.x, robot.pose.y, w, h);
      const radius = isSelected ? 9 : 6;

      // Outer halo for selected
      if (isSelected) {
        ctx.fillStyle = robot.color + "33";
        ctx.beginPath();
        ctx.arc(sx, sy, radius + 6, 0, Math.PI * 2);
        ctx.fill();
      }

      // Body
      ctx.fillStyle = robot.color;
      ctx.beginPath();
      ctx.arc(sx, sy, radius, 0, Math.PI * 2);
      ctx.fill();

      // Heading indicator
      ctx.strokeStyle = "white";
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(sx, sy);
      ctx.lineTo(
        sx + Math.cos(robot.pose.theta) * (radius + 6),
        sy - Math.sin(robot.pose.theta) * (radius + 6),
      );
      ctx.stroke();

      // Label
      ctx.fillStyle = "#E6E9EF";
      ctx.font = "11px ui-monospace, monospace";
      ctx.fillText(robot.robot_id, sx + radius + 6, sy + 3);
    }

    function draw(robots, selectedId) {
      const rect = canvas.getBoundingClientRect();
      const w = rect.width;
      const h = rect.height;
      ctx.clearRect(0, 0, w, h);
      drawGrid(w, h);

      // Update trails
      for (const robot of robots) {
        if (!trails.has(robot.robot_id)) trails.set(robot.robot_id, []);
        const trail = trails.get(robot.robot_id);
        trail.push({ x: robot.pose.x, y: robot.pose.y });
        if (trail.length > TRAIL_LENGTH) trail.shift();
      }

      // Draw non-selected first so the selected one is on top
      for (const robot of robots) {
        if (robot.robot_id !== selectedId) drawRobot(robot, false, w, h);
      }
      const selected = robots.find(r => r.robot_id === selectedId);
      if (selected) drawRobot(selected, true, w, h);
    }

    return { draw };
  }

  return { create };
})();

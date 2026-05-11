/**
 * Chart.js wrappers for Yana Robots.
 *
 * Exposes a tiny `YanaCharts` namespace so app.js doesn't have to know
 * the chart library specifics.
 */

window.YanaCharts = (function () {
  const COLOR_TEXT = "#8C93A3";
  const COLOR_GRID = "#262C38";
  const COLOR_ACCENT = "#FF6B35";
  const COLOR_GREEN  = "#2EC4B6";
  const COLOR_PURPLE = "#8338EC";

  Chart.defaults.color = COLOR_TEXT;
  Chart.defaults.font.family =
    '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
  Chart.defaults.font.size = 11;
  Chart.defaults.animation.duration = 250;

  function baseScale() {
    return {
      grid:   { color: COLOR_GRID, drawBorder: false },
      ticks:  { color: COLOR_TEXT, maxTicksLimit: 5 },
    };
  }

  function createBatteryChart(canvasId) {
    const ctx = document.getElementById(canvasId).getContext("2d");

    const gradient = ctx.createLinearGradient(0, 0, 0, 200);
    gradient.addColorStop(0,   "rgba(46,196,182,0.35)");
    gradient.addColorStop(1,   "rgba(46,196,182,0.00)");

    return new Chart(ctx, {
      type: "line",
      data: {
        labels: [],
        datasets: [{
          label: "Battery (%)",
          data: [],
          borderColor: COLOR_GREEN,
          backgroundColor: gradient,
          borderWidth: 2,
          tension: 0.3,
          fill: true,
          pointRadius: 0,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { ...baseScale(), display: false },
          y: { ...baseScale(), min: 0, max: 100,
               ticks: { ...baseScale().ticks, callback: v => v + "%" } },
        },
      },
    });
  }

  function createVelocityChart(canvasId) {
    const ctx = document.getElementById(canvasId).getContext("2d");
    return new Chart(ctx, {
      type: "line",
      data: {
        labels: [],
        datasets: [
          {
            label: "linear (m/s)",
            data: [],
            borderColor: COLOR_ACCENT,
            backgroundColor: "transparent",
            borderWidth: 2,
            tension: 0.3,
            pointRadius: 0,
            yAxisID: "y",
          },
          {
            label: "angular (rad/s)",
            data: [],
            borderColor: COLOR_PURPLE,
            backgroundColor: "transparent",
            borderWidth: 1.5,
            borderDash: [4, 3],
            tension: 0.3,
            pointRadius: 0,
            yAxisID: "y1",
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: true,
            position: "bottom",
            labels: { boxHeight: 6, boxWidth: 12, padding: 12 },
          },
        },
        scales: {
          x:  { ...baseScale(), display: false },
          y:  { ...baseScale(), position: "left",
                title: { display: true, text: "m/s", color: COLOR_TEXT } },
          y1: { ...baseScale(), position: "right", grid: { drawOnChartArea: false },
                title: { display: true, text: "rad/s", color: COLOR_TEXT } },
        },
      },
    });
  }

  function update(chart, values, labels) {
    chart.data.labels = labels;
    chart.data.datasets[0].data = values;
    chart.update("none");
  }

  function updateVelocity(chart, linear, angular, labels) {
    chart.data.labels = labels;
    chart.data.datasets[0].data = linear;
    chart.data.datasets[1].data = angular;
    chart.update("none");
  }

  return { createBatteryChart, createVelocityChart, update, updateVelocity };
})();

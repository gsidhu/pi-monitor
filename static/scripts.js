window.addEventListener("DOMContentLoaded", () => {
  const maxPoints = 30;

  let minPower = sessionStorage.getItem("minPower") ? parseFloat(sessionStorage.getItem("minPower")) : Infinity;
  let maxPower = sessionStorage.getItem("maxPower") ? parseFloat(sessionStorage.getItem("maxPower")) : 0; 
 
  if (minPower !== Infinity) {
    document.getElementById("minPower").textContent = minPower.toFixed(3);
  }
  if (maxPower !== 0) {
    document.getElementById("maxPower").textContent = maxPower.toFixed(3);
  }

  const chartConfig = (label, color) => ({
    type: "line",
    data: {
      labels: [],
      datasets: [{
        label: String(label),
        data: [],
        fill: false,
        borderColor: String(color),
        borderWidth: 2,
        tension: 0.3,
        pointRadius: 0
      }]
    },
    options: {
      responsive: true,
      animation: false,
      scales: {
        x: { display: false },
        y: { beginAtZero: true }
      },
      plugins: {
        legend: {
          labels: {
            font: {
              size: 12
            }
          }
        }
      }
    }
  });

  const cpuChart = new Chart(document.getElementById("cpuChart"), chartConfig("CPU Usage (%)", "#0d6efd"));
  const memChart = new Chart(document.getElementById("memChart"), chartConfig("Memory Usage (%)", "#6610f2"));
  const tempChart = new Chart(document.getElementById("tempChart"), chartConfig("CPU Temp (°C)", "#dc3545"));
  const fanChart = new Chart(document.getElementById("fanChart"), chartConfig("Fan Speed (RPM)", "#0dcaf0"));
  const freqChart = new Chart(document.getElementById("freqChart"), chartConfig("CPU Frequency (MHz)", "#f39c12"));
  const gpuFreqChart = new Chart(document.getElementById("gpuFreqChart"), chartConfig("GPU Frequency (MHz)", "#fd7e14"));
  const diskChart = new Chart(document.getElementById("diskChart"), chartConfig("Disk Usage (%)", "#6f42c1"));

  const diskIOChart = new Chart(document.getElementById("diskIOChart"), {
    type: "line",
    data: {
      labels: [],
      datasets: [
        {
          label: "Read MB/s",
          data: [],
          borderColor: "#20c997",
          fill: false,
          tension: 0.3,
          pointRadius: 0,
          borderWidth: 2
        },
        {
          label: "Write MB/s",
          data: [],
          borderColor: "#d63384",
          fill: false,
          tension: 0.3,
          pointRadius: 0,
          borderWidth: 2
        }
      ]
    },
    options: {
      responsive: true,
      animation: false,
      scales: {
        x: { display: false },
        y: { beginAtZero: true }
      },
      plugins: {
        legend: {
          labels: {
            font: { size: 12 }
          }
        }
      }
    }
  });

  const netIOChart = new Chart(document.getElementById("netIOChart"), {
    type: "line",
    data: {
      labels: [],
      datasets: [
        {
          label: "Recv MB/s",
          data: [],
          borderColor: "#0dcaf0",
          fill: false,
          tension: 0.3,
          pointRadius: 0,
          borderWidth: 2
        },
        {
          label: "Send MB/s",
          data: [],
          borderColor: "#ffc107",
          fill: false,
          tension: 0.3,
          pointRadius: 0,
          borderWidth: 2
        }
      ]
    },
    options: {
      responsive: true,
      animation: false,
      scales: {
        x: { display: false },
        y: { beginAtZero: true }
      },
      plugins: {
        legend: {
          labels: {
            font: { size: 12 }
          }
        }
      }
    }
  });
  const powerChart = new Chart(document.getElementById("powerChart"), {
    type: "bar",
    data: {
      labels: [],
      datasets: [{
        label: "Power (W)",
        data: [],
        backgroundColor: "rgba(13, 202, 240, 0.6)",
        borderColor: "rgba(13, 202, 240, 1)",
        borderWidth: 1,
        borderRadius: 4
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: {
          beginAtZero: true,
          ticks: { color: "#aaa" },
          grid: { color: "#333" }
        },
        x: {
          ticks: { color: "#aaa" },
          grid: { display: false }
        }
      },
      plugins: {
        legend: {
          labels: {
            font: { size: 12 },
            color: "#ccc"
          }
        },
        tooltip: {
          callbacks: {
            label: ctx => `${ctx.dataset.label}: ${ctx.raw.toFixed(3)} W`
          }
        }
      }
    }
  });

  const updateChart = (chart, value) => {
    if (!chart || !chart.data) return;
    const now = new Date().toLocaleTimeString();
    if (chart.data.labels.length > maxPoints) {
      chart.data.labels.shift();
      chart.data.datasets.forEach(ds => ds.data.shift());
    }
    chart.data.labels.push(now);
    chart.data.datasets[0].data.push(value);
    chart.update();
  };

  const pushToChart = (chart, datasetIndex, value, label = null) => {
    if (!chart || !chart.data) return;
    if (label !== null) {
      chart.data.labels.push(label);
    } else if (chart.data.labels.length < chart.data.datasets[datasetIndex].data.length + 1) {
      chart.data.labels.push(""); // placeholder label
    }
    chart.data.datasets[datasetIndex].data.push(value);
    if (chart.data.labels.length > maxPoints) {
      chart.data.labels.shift();
      chart.data.datasets.forEach(ds => ds.data.shift());
    }
    chart.update();
  };

  async function updateStats() {
    try {
      const res = await fetch("/api/stats");
      const stats = await res.json();
      const now = new Date().toLocaleTimeString();

      // Update single-series charts
      updateChart(cpuChart, stats.cpu * 100);
      updateChart(memChart, stats.memory_percent * 100);
      updateChart(tempChart, stats.temp);
      updateChart(fanChart, stats.fan_rpm);
      updateChart(freqChart, stats.cpu_freq);
      updateChart(gpuFreqChart, stats.gpu_freq);
      updateChart(diskChart, stats.disk_usage_percent * 100);

      // Update multi-series charts
      pushToChart(diskIOChart, 0, stats.disk_read_mb_s, now);
      pushToChart(diskIOChart, 1, stats.disk_write_mb_s);
      pushToChart(netIOChart, 0, stats.net_recv_mb_s, now);
      pushToChart(netIOChart, 1, stats.net_sent_mb_s);

      // Floating stats
      document.getElementById("cpuStat").textContent = `${(stats.cpu * 100).toFixed(1)}%`;
      document.getElementById("memStat").textContent = `${(stats.memory_percent * 100).toFixed(1)}%`;
      document.getElementById("tempStat").textContent = `${stats.temp.toFixed(1)}°C`;
      document.getElementById("fanSpeedLabel").textContent = `${stats.fan_rpm} RPM`;
      document.getElementById("freqStat").textContent = `${stats.cpu_freq.toFixed(0)} MHz`;
      document.getElementById("gpuFreqStat").textContent = `${stats.gpu_freq.toFixed(0)} MHz`;
      document.getElementById("diskStat").textContent = `${(stats.disk_usage_percent * 100).toFixed(1)}%`;
      document.getElementById("diskReadStat").textContent = `${stats.disk_read_mb_s.toFixed(1)} MB/s`;
      document.getElementById("diskWriteStat").textContent = `${stats.disk_write_mb_s.toFixed(1)} MB/s`;
      document.getElementById("netRecvStat").textContent = `${stats.net_recv_mb_s.toFixed(1)} MB/s`;
      document.getElementById("netSentStat").textContent = `${stats.net_sent_mb_s.toFixed(1)} MB/s`;

      // Footer
      document.getElementById("uptime").textContent = stats.uptime_human;
      document.getElementById("loadAvg").textContent = stats.load_avg;

    } catch (err) {
      console.error("Stats fetch failed:", err);
    }
  }

  async function updatePowerChart() {
    try {
      const res = await fetch("/api/power");
      const data = await res.json();

      powerChart.data.labels = data.readings.map(r => r.rail);
      powerChart.data.datasets[0].data = data.readings.map(r => r.power);
      powerChart.update();

      document.getElementById("totalPowerStat").textContent = `${data.total_power.toFixed(3)} W`;

      if (data.total_power < minPower) {
        minPower = data.total_power;
        sessionStorage.setItem("minPower", minPower);
      }
      
      if (data.total_power > maxPower) {
        maxPower = data.total_power;
        sessionStorage.setItem("maxPower", maxPower);
      }

      document.getElementById("minPower").textContent = minPower.toFixed(3);
      document.getElementById("maxPower").textContent = maxPower.toFixed(3);

    } catch (err) {
      console.error("Power chart fetch failed:", err);
    }
  }

  // Initial calls and intervals
  setTimeout(() => {
    updateStats();
    updatePowerChart();
    setInterval(updateStats, 1000);
    setInterval(updatePowerChart, 2000);
  }, 500);

  // Power controls
  const rebootBtn = document.getElementById("rebootBtn");
  const shutdownBtn = document.getElementById("shutdownBtn");

  rebootBtn.addEventListener("click", async () => {
    if (confirm("Are you sure you want to reboot the system?")) {
      try {
        await fetch("/reboot", { method: "POST" });
        alert("Reboot command sent.");
      } catch (err) {
        console.error("Reboot request failed:", err);
        alert("Failed to send reboot command.");
      }
    }
  });

  shutdownBtn.addEventListener("click", async () => {
    if (confirm("Are you sure you want to shut down the system?")) {
      try {
        await fetch("/shutdown", { method: "POST" });
        alert("Shutdown command sent.");
      } catch (err) {
        console.error("Shutdown request failed:", err);
        alert("Failed to send shutdown command.");
      }
    }
  });

  // Speedtest
  const speedtestBtn = document.getElementById("speedtestBtn");
  const speedtestLoader = document.getElementById("speedtestLoader");
  const pingResult = document.getElementById("pingResult");
  const downloadResult = document.getElementById("downloadResult");
  const uploadResult = document.getElementById("uploadResult");

  const runSpeedtest = async () => {
    speedtestBtn.disabled = true;
    speedtestLoader.style.display = "block";
    pingResult.textContent = "--";
    downloadResult.textContent = "--";
    uploadResult.textContent = "--";

    try {
      const res = await fetch("/api/speedtest");
      if (!res.ok) {
        throw new Error(`Speedtest failed with status: ${res.status}`);
      }
      const results = await res.json();
      pingResult.textContent = results.ping.toFixed(2);
      downloadResult.textContent = results.download.toFixed(2);
      uploadResult.textContent = results.upload.toFixed(2);
    } catch (err) {
      console.error("Speedtest failed:", err);
      alert("Speedtest failed. Check the console for details.");
    } finally {
      speedtestBtn.disabled = false;
      speedtestLoader.style.display = "none";
    }
  };

  speedtestBtn.addEventListener("click", runSpeedtest);
});

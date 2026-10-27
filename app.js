const api = window.PATTERN_SIGNAL_API || "";
const state = { signals: [], filter: "all", query: "" };
const $ = (selector) => document.querySelector(selector);

function money(value) { return Number(value).toLocaleString(undefined, {maximumFractionDigits: 2}); }
function metric(data) {
  if (!data || !data.trades) return "<span class='metric'>Insufficient data</span>";
  const positive = data.mean_return_pct >= 0 ? "positive" : "negative";
  return `<span class="metric ${positive}">${(data.mean_return_pct * 100).toFixed(2)}% mean<small>${data.trades} trades · ${(data.win_rate * 100).toFixed(1)}% win</small></span>`;
}
function row(signal) {
  const m = signal.metrics || {};
  return `<tr><td class="symbol">${signal.symbol.replace("US.", "")}</td><td><span class="tag">${signal.timeframe}</span></td><td>${signal.variant_id.replaceAll("_", " ")}</td><td>${money(signal.entry)}</td><td class="stop">${money(signal.initial_stop)}</td><td>${metric(m["10"])}</td><td>${metric(m["5"])}</td><td>${metric(m["1"])}</td><td>${signal.setup_date}</td></tr>`;
}
function render() {
  const matches = state.signals.filter(s => (state.filter === "all" || s.timeframe === state.filter) && s.symbol.toLowerCase().includes(state.query));
  $("#signals").innerHTML = matches.map(row).join("");
  $("#empty-state").hidden = matches.length !== 0;
  $("#signal-count").textContent = state.signals.length;
  $("#daily-count").textContent = state.signals.filter(s => s.timeframe === "day").length;
  $("#weekly-count").textContent = state.signals.filter(s => s.timeframe === "week").length;
}
function demoSignals() {
  return [{symbol:"US.BTC-DEMO",timeframe:"day",variant_id:"demo_preview_only",entry:68420,initial_stop:64950,setup_date:"Preview",metrics:{"10":{trades:115,win_rate:.304,mean_return_pct:.0372},"5":{trades:53,win_rate:.302,mean_return_pct:.0218},"1":{trades:0}}}];
}
async function load() {
  try {
    if (!api) throw new Error("No API configured");
    const [health, signals] = await Promise.all([fetch(`${api}/api/health`).then(r => r.json()), fetch(`${api}/api/signals`).then(r => r.json())]);
    state.signals = signals;
    $("#connection-dot").className = "dot";
    $("#connection-text").textContent = "Scanner connected";
    $("#provider").textContent = "Futu";
    $("#health-value").textContent = health.ok ? "Healthy" : "Check";
    $("#health-detail").textContent = health.service || "scanner API";
    $("#last-scan").textContent = signals[0]?.scanned_at?.replace("T", " ").slice(0, 16) || "No active setup";
  } catch (_) {
    state.signals = location.hostname === "localhost" ? demoSignals() : [];
    $("#connection-text").textContent = api ? "Scanner unavailable" : "API not configured";
    $("#health-value").textContent = "Offline";
    $("#health-detail").textContent = "dashboard preview";
  }
  render();
}
document.querySelectorAll("[data-filter]").forEach(button => button.addEventListener("click", () => { state.filter = button.dataset.filter; document.querySelectorAll("[data-filter]").forEach(x => x.classList.toggle("selected", x === button)); render(); }));
$("#search").addEventListener("input", event => { state.query = event.target.value.toLowerCase(); render(); });
load();

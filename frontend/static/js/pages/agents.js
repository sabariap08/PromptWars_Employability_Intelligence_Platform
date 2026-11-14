/* Agent registry, workflow map and execution log. */
(function () {
  "use strict";

  function renderAgents(data) {
    var agents = data.agents || [];
    var labels = {};
    agents.forEach(function (agent) { labels[agent.key] = agent.label || agent.name; });

    document.getElementById("agent-cards").innerHTML = agents.map(function (agent) {
      return (
        '<div class="attempt-row"><div><strong>' + EIP.escape(agent.label) + "</strong>" +
        '<div class="small muted">' + EIP.escape(agent.name) + " · key " + EIP.escape(agent.key) + "</div></div>" +
        '<span class="badge primary">Agent</span></div>'
      );
    }).join("") || '<p class="small muted">No agents registered.</p>';

    var workflows = data.workflows || {};
    document.getElementById("workflow-list").innerHTML = Object.keys(workflows).map(function (event) {
      var chain = (workflows[event] || []).map(function (key) { return labels[key] || key; });
      return (
        '<div class="next-task"><div class="task-top"><div><h4>' + EIP.escape(event) + "</h4>" +
        '<div class="small muted">' + chain.join(" → ") + "</div></div>" +
        '<span class="badge">' + chain.length + " agents</span></div></div>"
      );
    }).join("") || '<p class="small muted">No workflows registered.</p>';
  }

  function renderExecutions(data) {
    var executions = data.executions || [];
    var stats = data.stats || {};
    var total = stats.total || 0;

    document.getElementById("ag-total").textContent = total;
    document.getElementById("ag-success").textContent = stats.success || 0;
    document.getElementById("ag-rate").textContent = total
      ? Math.round(((stats.success || 0) / total) * 100) + "% success rate"
      : "No runs yet";
    document.getElementById("ag-fallback").textContent = total
      ? Math.round(((stats.fallback || 0) / total) * 100) + "%"
      : "0%";

    var duration = executions.length
      ? Math.round(executions.reduce(function (sum, run) { return sum + (run.duration_ms || 0); }, 0) / executions.length)
      : 0;
    document.getElementById("ag-duration").textContent = duration + "ms";

    var body = document.getElementById("executions-body");
    var empty = document.getElementById("executions-empty");
    if (!executions.length) {
      body.innerHTML = "";
      empty.classList.remove("hidden");
      empty.innerHTML = EIP.empty("No executions yet", "Agent runs appear here after profile, assessment or career events.");
      return;
    }
    empty.classList.add("hidden");
    body.innerHTML = executions.map(function (run) {
      return (
        "<tr><td>" + EIP.fmtDate(run.created_at, true) + "</td><td>" + EIP.escape(run.workflow || "—") +
        "</td><td>" + EIP.escape(run.agent_name) + "</td><td>" + EIP.badge(run.status) +
        "</td><td>" + EIP.escape(run.provider) + "</td><td>" + (run.duration_ms || 0) + "ms</td><td>" +
        '<span class="small">' + EIP.escape(run.output_summary || run.error || "—") + "</span></td></tr>"
      );
    }).join("");
  }

  function load() {
    return Promise.all([EIP.get("/api/admin/agents"), EIP.get("/api/admin/executions?limit=60")]).then(function (results) {
      renderAgents(results[0]);
      renderExecutions(results[1]);
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    document.getElementById("agents-refresh").addEventListener("click", function (event) {
      var button = event.currentTarget;
      EIP.setBusy(button, true, "Refreshing…");
      load().catch(function (err) { EIP.toast(err.message, "error"); }).finally(function () { EIP.setBusy(button, false); });
    });
    load().catch(function (err) { EIP.toast(err.message, "error"); });
  });
})();

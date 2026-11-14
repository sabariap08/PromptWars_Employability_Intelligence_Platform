/* Super-admin platform overview. */
(function () {
  "use strict";

  function contextRow(label, value) {
    return '<div class="ctx-row"><span>' + EIP.escape(label) + "</span><strong>" + EIP.escape(value) + "</strong></div>";
  }

  function providerCard(provider) {
    var badge = provider.configured ? EIP.badge("CONFIGURED") : EIP.badge("NOT_CONFIGURED");
    return (
      '<div class="next-task"><div class="task-top"><div><h4>' + EIP.escape(provider.label || provider.name) + "</h4>" +
      '<div class="small muted">' + EIP.escape(provider.model || "No model") +
      (provider.position ? " · fallback position " + provider.position : " · not routed") + "</div></div>" +
      badge + "</div></div>"
    );
  }

  function render(data) {
    var orgs = data.organizations || {};
    var users = data.users || {};
    var agents = data.agents || {};

    document.getElementById("pf-orgs").textContent = orgs.total || 0;
    document.getElementById("pf-orgbreakdown").textContent =
      (orgs.universities || 0) + " universities · " + (orgs.companies || 0) + " companies";
    document.getElementById("pf-pending").textContent = orgs.pending || 0;
    document.getElementById("pf-users").textContent = users.total || 0;
    document.getElementById("pf-userpending").textContent = (users.pending_members || 0) + " members pending";
    document.getElementById("pf-executions").textContent = agents.total || 0;
    document.getElementById("pf-success").textContent =
      agents.total ? Math.round(((agents.success || 0) / agents.total) * 100) + "% successful" : "No runs yet";

    var roles = users.by_role || {};
    var roleRows = Object.keys(roles).sort().map(function (role) {
      return contextRow(EIP.titleCase(role), roles[role]);
    }).join("");
    document.getElementById("pf-roles").innerHTML =
      roleRows || '<p class="small muted">No users yet.</p>';

    var byStatus = orgs.by_status || {};
    var statusRows = Object.keys(byStatus).sort().map(function (status) {
      return contextRow(EIP.titleCase(status), byStatus[status]);
    }).join("");
    document.getElementById("pf-status").innerHTML =
      statusRows || '<p class="small muted">No organizations yet.</p>';

    var providers = data.providers || [];
    document.getElementById("pf-providers").innerHTML = providers.length
      ? providers.map(providerCard).join("")
      : '<p class="small muted">No provider information available.</p>';

    document.getElementById("pf-agentstats").innerHTML =
      contextRow("Total executions", agents.total || 0) +
      contextRow("Successful", agents.success || 0) +
      contextRow("Failed", agents.failed || 0) +
      contextRow("Deterministic fallback", agents.fallback || 0) +
      contextRow("Database mode", EIP.titleCase(data.database_mode || "memory"));
  }

  document.addEventListener("DOMContentLoaded", function () {
    EIP.get("/api/admin/overview")
      .then(render)
      .catch(function (err) {
        var box = document.getElementById("pf-roles");
        box.innerHTML = '<div class="alert danger">' + EIP.escape(err.message) + "</div>";
      });
  });
})();

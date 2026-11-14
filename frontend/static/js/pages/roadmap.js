/* Learning roadmap with adaptive task updates. */
(function () {
  "use strict";

  var state = { roadmap: null };

  function alertBox(message, type) {
    var box = document.getElementById("roadmap-alert");
    box.className = "alert " + (type || "warning");
    box.textContent = message;
    box.classList.remove("hidden");
  }

  function clearAlert() {
    document.getElementById("roadmap-alert").classList.add("hidden");
  }

  function remainingHours(roadmap) {
    var total = 0;
    (roadmap.phases || []).forEach(function (phase) {
      (phase.tasks || []).forEach(function (task) {
        if (task.status !== "COMPLETED") total += Number(task.est_hours || 0);
      });
    });
    return Math.round(total * 10) / 10;
  }

  function taskCard(task) {
    var actions = "";
    if (task.status === "PENDING") {
      actions = '<button class="btn btn-outline btn-sm" data-task="' + EIP.escape(task.id) + '" data-action="START">Start</button>' +
        '<button class="btn btn-primary btn-sm" data-task="' + EIP.escape(task.id) + '" data-action="COMPLETE">Mark complete</button>';
    } else if (task.status === "IN_PROGRESS") {
      actions = '<button class="btn btn-primary btn-sm" data-task="' + EIP.escape(task.id) + '" data-action="COMPLETE">Mark complete</button>';
    } else {
      actions = '<button class="btn btn-ghost btn-sm" data-task="' + EIP.escape(task.id) + '" data-action="REOPEN">Reopen</button>';
    }
    var resource = task.resource_url
      ? '<a class="small" href="' + EIP.escape(task.resource_url) + '" target="_blank" rel="noopener">Open resource</a>'
      : '<span class="small muted">Guided practice</span>';
    return (
      '<div class="task-card ' + EIP.escape((task.status || "").toLowerCase().replace("_", "-")) + '">' +
      '<div class="task-top"><div><h4>' + EIP.escape(task.resource_title) + "</h4>" +
      '<div class="task-meta">' + EIP.badge(task.status) +
      "<span>" + EIP.escape(task.skill_name) + "</span>" +
      "<span>" + EIP.escape(task.difficulty) + "</span>" +
      "<span>" + (task.est_hours || 0) + "h</span>" +
      (task.remediation ? '<span class="badge warning">Targeted revision</span>' : "") +
      "</div></div>" + resource + "</div>" +
      '<div class="task-exercise">' + EIP.escape(task.exercise) + "</div>" +
      '<div class="task-checkpoint">Checkpoint: ' + EIP.escape(task.checkpoint || "") + "</div>" +
      (task.added_reason ? '<div class="small muted">' + EIP.escape(task.added_reason) + "</div>" : "") +
      '<div class="task-actions">' + actions + "</div></div>"
    );
  }

  function render(data) {
    var roadmap = data.roadmap;
    var summary = data.summary || {};
    state.roadmap = roadmap;
    var empty = document.getElementById("roadmap-empty");
    var content = document.getElementById("roadmap-content");

    if (!roadmap) {
      content.classList.add("hidden");
      empty.classList.remove("hidden");
      empty.innerHTML = EIP.empty(
        "No active plan yet",
        "Set a target career and add a few skills, then generate your first adaptive roadmap.",
        '<button class="btn btn-primary" id="empty-generate" type="button">Generate roadmap</button>'
      );
      var button = document.getElementById("empty-generate");
      if (button) button.addEventListener("click", generate);
      return;
    }

    empty.classList.add("hidden");
    content.classList.remove("hidden");
    document.getElementById("rm-completion").textContent = (summary.completion || 0) + "%";
    document.getElementById("rm-tasks").textContent = (summary.completed_tasks || 0) + " of " + (summary.total_tasks || 0) + " tasks";
    document.getElementById("rm-version").textContent = "v" + (summary.version || 1);
    document.getElementById("rm-trigger").textContent = EIP.titleCase(summary.trigger || "initial");
    document.getElementById("rm-hours").textContent = remainingHours(roadmap) + "h";
    document.getElementById("rm-readiness").textContent = (summary.readiness_snapshot || 0) + "%";
    document.getElementById("rm-career").textContent = summary.career_name || "";
    document.getElementById("rm-rationale").textContent = summary.rationale || "No rationale recorded.";

    document.getElementById("roadmap-body").innerHTML = (roadmap.phases || []).map(function (phase) {
      return (
        '<div class="phase"><div class="phase-head"><h3>Phase ' + (phase.phase_number || "") + " · " +
        EIP.escape(phase.title) + '</h3><p class="small muted">' + EIP.escape(phase.objective || "") + "</p></div>" +
        '<div class="stack">' + (phase.tasks || []).map(taskCard).join("") + "</div></div>"
      );
    }).join("");

    var versions = document.getElementById("roadmap-versions");
    versions.innerHTML = (data.versions || []).length
      ? '<div class="table-wrap"><table><thead><tr><th>Version</th><th>Status</th><th>Trigger</th><th>Career</th><th>Created</th></tr></thead><tbody>' +
        data.versions.map(function (item) {
          return "<tr><td>v" + item.version + "</td><td>" + EIP.badge(item.status) + "</td><td>" +
            EIP.escape(EIP.titleCase(item.trigger || "")) + "</td><td>" + EIP.escape(item.career_name || "") +
            "</td><td>" + EIP.fmtDate(item.created_at) + "</td></tr>";
        }).join("") + "</tbody></table></div>"
      : '<p class="small muted">No earlier versions.</p>';
  }

  function load() {
    return EIP.get("/api/learning/roadmap").then(render);
  }

  async function generate() {
    clearAlert();
    var button = document.getElementById("generate-btn");
    if (button) EIP.setBusy(button, true, "Generating…");
    try {
      var result = await EIP.post("/api/learning/roadmap/generate", {});
      EIP.toast("New plan generated from your latest evidence.", "success");
      await load();
      if (result.summary && result.summary.rationale) {
        alertBox(result.summary.rationale, "success");
      }
    } catch (err) {
      alertBox(err.message, "danger");
    } finally {
      if (button) EIP.setBusy(button, false);
    }
  }

  function wire() {
    document.getElementById("generate-btn").addEventListener("click", generate);

    document.getElementById("roadmap-body").addEventListener("click", async function (event) {
      var button = event.target.closest("[data-task]");
      if (!button) return;
      clearAlert();
      EIP.setBusy(button, true);
      try {
        var result = await EIP.post("/api/learning/tasks/" + encodeURIComponent(button.dataset.task), {
          action: button.dataset.action,
        });
        EIP.toast("Task updated. Plan completion is now " + result.summary.completion + "%.", "success");
        state.roadmap = result.roadmap;
        await load();
      } catch (err) {
        alertBox(err.message, "danger");
      } finally {
        EIP.setBusy(button, false);
      }
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    wire();
    load().catch(function (err) { alertBox(err.message, "danger"); });
  });
})();

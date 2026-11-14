/* Institution overview for university / organization administrators. */
(function () {
  "use strict";

  function learnerRow(learner, tone) {
    return (
      '<div class="attempt-row"><div><strong>' + EIP.escape(learner.full_name) + "</strong>" +
      '<div class="small muted">' + EIP.escape(learner.email) + "</div></div>" +
      '<div class="row"><span class="badge ' + (tone || "") + '">' + learner.readiness + "%</span></div></div>"
    );
  }

  function render(context, data, logs) {
    var org = context.organization;
    var departments = context.departments || [];
    document.getElementById("admin-title").textContent = org.name;
    document.getElementById("admin-sub").textContent =
      EIP.titleCase(org.organization_type) + " · " + (org.city || "No city") +
      " · " + departments.length + " departments";

    document.getElementById("adm-learners").textContent = data.learners_total;
    document.getElementById("adm-pending").textContent = data.pending_requests + " pending approval";
    document.getElementById("adm-readiness").textContent = data.average_readiness + "%";
    document.getElementById("adm-assessments").textContent = data.assessments_completed;
    document.getElementById("adm-avgscore").textContent = "Average score " + data.average_assessment_score + "%";
    document.getElementById("adm-completion").textContent = data.completion_average + "%";

    document.getElementById("adm-departments").innerHTML = data.department_breakdown.length
      ? data.department_breakdown.map(function (row) {
          return "<tr><td>" + EIP.escape(row.department) + "</td><td>" + row.learners +
            "</td><td>" + row.average_readiness + "%</td></tr>";
        }).join("")
      : '<tr><td colspan="3" class="muted">No department data yet.</td></tr>';

    document.getElementById("adm-gaps").innerHTML = data.common_gaps.length
      ? data.common_gaps.map(function (gap) {
          return (
            '<div class="skill-line"><div class="skill-top"><strong>' + EIP.escape(gap.skill_name) +
            "</strong><span>" + gap.learners + " learners · avg " + gap.average_proficiency + "%</span></div>" +
            '<div class="progress amber"><span style="width:' + EIP.percent(gap.average_proficiency) + '%"></span></div></div>'
          );
        }).join("")
      : '<p class="small muted">No skill gaps recorded.</p>';

    document.getElementById("adm-top").innerHTML = data.top_learners.length
      ? data.top_learners.map(function (learner) { return learnerRow(learner, "success"); }).join("")
      : '<p class="small muted">No approved learners yet.</p>';

    document.getElementById("adm-support").innerHTML = data.needs_support.length
      ? data.needs_support.map(function (learner) { return learnerRow(learner, "warning"); }).join("")
      : '<p class="small muted">No learner data yet.</p>';

    document.getElementById("adm-audit").innerHTML = logs.length
      ? logs.map(function (log) {
          return "<tr><td>" + EIP.fmtDate(log.created_at, true) + "</td><td>" + EIP.escape(log.action) +
            (log.detail ? '<div class="small muted">' + EIP.escape(log.detail) + "</div>" : "") +
            "</td><td>" + EIP.escape(EIP.titleCase(log.actor_role || "")) + "</td><td>" +
            EIP.escape(log.target_type || "") + (log.target_id ? " · " + EIP.escape(log.target_id) : "") + "</td></tr>";
        }).join("")
      : '<tr><td colspan="4" class="muted">No activity recorded yet.</td></tr>';
  }

  document.addEventListener("DOMContentLoaded", function () {
    Promise.all([
      EIP.get("/api/organizations/me"),
      EIP.get("/api/organizations/me/overview"),
      EIP.get("/api/organizations/me/audit?limit=15"),
    ])
      .then(function (results) {
        render(results[0], results[1], results[2].logs || []);
      })
      .catch(function (err) {
        var box = document.getElementById("admin-alert");
        box.className = "alert danger";
        box.textContent = err.message;
        box.classList.remove("hidden");
      });
  });
})();

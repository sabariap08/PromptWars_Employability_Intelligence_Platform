/* Learner dashboard. */
(function () {
  "use strict";

  function skillLine(row) {
    var current = EIP.percent(row.current);
    return (
      '<div class="skill-line"><div class="skill-top"><strong>' + EIP.escape(row.skill_name) +
      "</strong><span>" + current + "%" +
      (row.verified ? ' <span class="badge success">Verified</span>' : "") + "</span></div>" +
      '<div class="progress"><span style="width:' + current + '%"></span></div></div>'
    );
  }

  function render(data, me) {
    var dash = data.dashboard;
    var firstName = (me.user.full_name || "").split(" ")[0];
    document.getElementById("dash-greeting").textContent = "Welcome back, " + firstName;
    document.getElementById("dash-sub").textContent = dash.career_name
      ? "Target role: " + dash.career_name + " · profile " + dash.profile_completion + "% complete"
      : "Set a target career to unlock readiness scoring and a personalised roadmap.";

    document.getElementById("stat-readiness").textContent = dash.career_readiness + "%";
    document.getElementById("stat-career").textContent = dash.career_name || "No target career yet";
    document.getElementById("stat-completion").textContent = dash.roadmap_completion + "%";
    document.getElementById("stat-taskcount").textContent =
      dash.roadmap && dash.roadmap.total_tasks
        ? dash.roadmap.completed_tasks + " of " + dash.roadmap.total_tasks + " tasks"
        : "No active plan";
    document.getElementById("stat-verified").textContent = dash.skills_verified;
    document.getElementById("stat-totalskills").textContent = dash.skills_total + " skills on profile";
    document.getElementById("stat-assessments").textContent = dash.assessments_taken;
    document.getElementById("stat-avgscore").textContent = dash.average_score
      ? "Average score " + dash.average_score + "%"
      : "No evaluated attempts";

    var alertBox = document.getElementById("dash-alert");
    var messages = [];
    if (!dash.onboarding_complete) {
      messages.push(
        'Complete your profile and add at least one skill. <a href="/app/profile">Finish profile</a>'
      );
    }
    if (!dash.has_target_career) {
      messages.push('Choose a target career. <a href="/app/profile">Set career goal</a>');
    } else if (!dash.roadmap_id) {
      messages.push('Generate your first learning plan. <a href="/app/roadmap">Open roadmap</a>');
    }
    if (!dash.assessments_taken) {
      messages.push('Take a baseline assessment to verify your current level. <a href="/app/assessments">Start baseline</a>');
    }
    if (messages.length) {
      alertBox.innerHTML = messages.join("<br>");
      alertBox.classList.remove("hidden");
    }

    var tasksBox = document.getElementById("next-tasks");
    if (!dash.next_tasks || !dash.next_tasks.length) {
      tasksBox.innerHTML = EIP.empty("No pending tasks", "Generate a roadmap or complete your profile to get next steps.",
        '<a class="btn btn-primary btn-sm" href="/app/roadmap">Open roadmap</a>');
    } else {
      tasksBox.innerHTML = dash.next_tasks.map(function (task) {
        return (
          '<div class="next-task"><div class="task-top"><h4>' + EIP.escape(task.resource_title) + "</h4>" +
          EIP.badge(task.status) + '</div><div class="meta"><span>' + EIP.escape(task.skill_name) +
          "</span><span>" + (task.phase_title ? EIP.escape(task.phase_title) : "") + "</span><span>" +
          (task.est_hours || 0) + "h</span><span>" + EIP.escape(task.difficulty) + "</span></div>" +
          '<a class="small" href="/app/roadmap">Open task</a></div>'
        );
      }).join("");
    }

    document.getElementById("dash-strengths").innerHTML = dash.strengths.length
      ? dash.strengths.map(skillLine).join("")
      : '<p class="small muted">No verified strengths yet. Complete a skill check to verify your skills.</p>';
    document.getElementById("dash-gaps").innerHTML = dash.gaps.length
      ? dash.gaps.map(skillLine).join("")
      : '<p class="small muted">No gaps recorded against your target career.</p>';

    var attempts = document.getElementById("dash-attempts");
    attempts.innerHTML = dash.recent_attempts.length
      ? dash.recent_attempts.map(function (attempt) {
          var score = attempt.score === null || attempt.score === undefined ? null : attempt.score;
          return (
            '<div class="attempt-row"><div><strong>' + EIP.escape(attempt.title) + "</strong>" +
            '<div class="small muted">' + EIP.escape(EIP.titleCase(attempt.purpose)) + " · " +
            EIP.fmtDate(attempt.evaluated_at || "") + "</div></div><div>" +
            (score !== null
              ? '<span class="badge ' + (score >= 65 ? "success" : score >= 40 ? "warning" : "danger") + '">' + score + "%</span>"
              : EIP.badge(attempt.status)) +
            '</div></div>'
          );
        }).join("")
      : EIP.empty("No attempts yet", "Your baseline assessment is the best first step.");

    var notifications = document.getElementById("dash-notifications");
    notifications.innerHTML = dash.notifications.length
      ? dash.notifications.map(function (item) {
          return (
            '<div class="attempt-row"><div><strong>' + EIP.escape(item.title) + "</strong>" +
            '<div class="small muted">' + EIP.escape(item.message) + "</div></div>" +
            '<span class="small muted nowrap">' + EIP.timeAgo(item.created_at) + "</span></div>"
          );
        }).join("")
      : EIP.empty("All caught up", "New approvals and readiness changes will appear here.");
  }

  function fail(err) {
    var alertBox = document.getElementById("dash-alert");
    alertBox.className = "alert danger";
    alertBox.textContent = err.message;
    alertBox.classList.remove("hidden");
  }

  document.addEventListener("DOMContentLoaded", function () {
    Promise.all([EIP.get("/api/auth/me"), EIP.get("/api/learner/dashboard")])
      .then(function (results) { render(results[1], results[0]); })
      .catch(fail);
  });
})();

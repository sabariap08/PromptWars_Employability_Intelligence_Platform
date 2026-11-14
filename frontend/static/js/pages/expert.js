/* Industry expert review: assigned learners, snapshot and trainer feedback. */
(function () {
  "use strict";

  var selected = null;

  function alertBox(message, type) {
    EIP.toast(message, type || "error");
  }

  function renderLearners(learners) {
    document.getElementById("expert-count").textContent = learners.length + " assigned";
    var box = document.getElementById("expert-learners");
    if (!learners.length) {
      box.innerHTML = EIP.empty("No learners assigned", "An organization administrator assigns learners to expert reviewers.");
      return;
    }
    box.innerHTML = learners.map(function (learner) {
      var active = selected === learner._id ? " in-progress" : "";
      return (
        '<button class="task-card' + active + '" type="button" data-learner="' + EIP.escape(learner._id) +
        '" style="text-align:left; cursor:pointer"><div class="task-top"><div><h4>' +
        EIP.escape(learner.full_name) + "</h4>" +
        '<div class="small muted">' + EIP.escape(learner.email) + " · " +
        EIP.escape(learner.career_name || "No target career") + "</div></div>" +
        '<div class="score-ring ' + EIP.scoreClass(learner.readiness) + '">' + learner.readiness + "%</div></div>" +
        '<div class="task-meta"><span>Assigned ' + EIP.fmtDate(learner.assigned_at) + "</span></div></button>"
      );
    }).join("");
  }

  function renderDetail(snapshot) {
    var user = snapshot.user;
    var career = snapshot.career || {};
    var skills = snapshot.skills || [];
    var assessments = snapshot.assessments || [];
    var feedback = snapshot.feedback || [];

    document.getElementById("expert-selected").textContent = user.full_name;
    document.getElementById("expert-detail").innerHTML =
      '<div class="row between"><div><h3 style="margin:0">' + EIP.escape(user.full_name) + "</h3>" +
      '<div class="small muted">' + EIP.escape(user.email) + (user.designation ? " · " + EIP.escape(user.designation) : "") +
      "</div></div><div class=\"score-ring " + EIP.scoreClass(career.readiness) + '">' + (career.readiness || 0) + "%</div></div>" +
      '<p class="small muted" style="margin-top:0.4rem">' + EIP.escape(career.name || "No target career") +
      " · roadmap " + ((snapshot.roadmap || {}).completion || 0) + "% (" +
      ((snapshot.roadmap || {}).total_tasks || 0) + " tasks)</p>" +
      '<div class="table-wrap"><table><thead><tr><th>Skill</th><th>Level</th><th>Verification</th><th>Evidence</th></tr></thead><tbody>' +
      (skills.length ? skills.map(function (skill) {
        return "<tr><td>" + EIP.escape(skill.skill_name) + "</td><td>" + skill.proficiency + "%</td><td>" +
          EIP.badge(skill.verification_status) + "</td><td>" + (skill.evidence_count || 0) + "</td></tr>";
      }).join("") : '<tr><td colspan="4" class="muted">No skills recorded.</td></tr>') +
      "</tbody></table></div>" +
      "<h4 style=\"margin-top:1rem\">Recent assessments</h4>" +
      (assessments.length ? '<div class="stack">' + assessments.map(function (attempt) {
        return '<div class="attempt-row"><div><strong>' + EIP.escape(attempt.title) + "</strong>" +
          '<div class="small muted">' + EIP.fmtDate(attempt.evaluated_at) + " · risk " +
          EIP.escape(attempt.risk_level || "LOW") + "</div></div>" +
          (attempt.score !== null && attempt.score !== undefined
            ? '<span class="badge ' + (attempt.score >= 65 ? "success" : attempt.score >= 40 ? "warning" : "danger") + '">' + attempt.score + "%</span>"
            : EIP.badge(attempt.status)) + "</div>";
      }).join("") + "</div>" : '<p class="small muted">No attempts yet.</p>') +
      "<h4 style=\"margin-top:1rem\">Trainer feedback</h4>" +
      (feedback.length ? '<div class="stack">' + feedback.map(function (item) {
        return '<div class="review-item"><div class="row between"><strong>' + EIP.escape(item.skill_name) +
          "</strong><span class=\"badge primary\">" + item.rating + "/5</span></div>" +
          '<div class="small muted">' + EIP.fmtDate(item.created_at) + "</div>" +
          '<div class="small">' + EIP.escape(item.feedback || "") + "</div></div>";
      }).join("") + "</div>" : '<p class="small muted">No feedback submitted yet.</p>');

    var form = document.getElementById("feedback-form");
    form.classList.remove("hidden");
    var skillSelect = document.getElementById("feedback-skill");
    skillSelect.innerHTML = skills.length
      ? skills.map(function (skill) {
          return '<option value="' + EIP.escape(skill.skill_name) + '">' + EIP.escape(skill.skill_name) +
            " (" + skill.proficiency + "%)</option>";
        }).join("")
      : '<option value="">No skills available</option>';
  }

  function loadLearners() {
    return EIP.get("/api/learner/expert/learners").then(function (data) {
      return data.learners || [];
    });
  }

  async function selectLearner(learnerId) {
    selected = learnerId;
    try {
      var snapshot = await EIP.get("/api/learner/expert/learners/" + learnerId);
      renderDetail(snapshot);
      var learners = await loadLearners();
      renderLearners(learners);
    } catch (err) {
      alertBox(err.message);
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    loadLearners()
      .then(function (learners) {
        renderLearners(learners);
        if (learners.length) selectLearner(learners[0]._id);
      })
      .catch(function (err) { alertBox(err.message); });

    document.getElementById("expert-learners").addEventListener("click", function (event) {
      var button = event.target.closest("[data-learner]");
      if (button) selectLearner(button.dataset.learner);
    });

    document.getElementById("feedback-form").addEventListener("submit", async function (event) {
      event.preventDefault();
      if (!selected) return;
      var skill = document.getElementById("feedback-skill").value;
      if (!skill) {
        alertBox("This learner has no skills to review yet.", "warning");
        return;
      }
      var submit = document.getElementById("feedback-submit");
      EIP.setBusy(submit, true, "Saving…");
      try {
        await EIP.post("/api/learner/expert/feedback", {
          learner_id: selected,
          skill_name: skill,
          rating: Number(document.getElementById("feedback-rating").value),
          feedback: document.getElementById("feedback-text").value.trim(),
        });
        EIP.toast("Feedback recorded as skill evidence.", "success");
        document.getElementById("feedback-text").value = "";
        await selectLearner(selected);
      } catch (err) {
        EIP.setBusy(submit, false);
        alertBox(err.message);
      } finally {
        EIP.setBusy(submit, false);
      }
    });
  });
})();

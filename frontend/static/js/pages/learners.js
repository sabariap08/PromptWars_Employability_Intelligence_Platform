/* Learner directory, expert capability and reviewer assignments. */
(function () {
  "use strict";

  var state = {
    status: "APPROVED",
    search: "",
    org: null,
    learners: [],
    trainers: [],
  };

  function alertBox(message, type) {
    var box = document.getElementById("learners-alert");
    box.className = "alert " + (type || "warning");
    box.textContent = message;
    box.classList.remove("hidden");
  }

  function clearAlert() {
    document.getElementById("learners-alert").classList.add("hidden");
  }

  function renderLearners(data) {
    var learners = data.learners || [];
    state.learners = learners.filter(function (item) { return item.account_status === "APPROVED"; });
    document.getElementById("learners-count").textContent = learners.length + " shown";
    document.getElementById("learners-title").textContent =
      EIP.titleCase(state.status ? state.status.replace(/_/g, " ") : "all") + " learners";

    var body = document.getElementById("learners-body");
    var empty = document.getElementById("learners-empty");
    if (!learners.length) {
      body.innerHTML = "";
      empty.classList.remove("hidden");
      empty.innerHTML = EIP.empty("No learners", "No members match this filter yet.");
      return;
    }
    empty.classList.add("hidden");
    var isCompany = state.org && state.org.organization_type === "COMPANY";
    body.innerHTML = learners.map(function (learner) {
      var actions = '<button class="btn btn-outline btn-sm" data-snapshot="' + EIP.escape(learner._id) + '">View</button>';
      if (isCompany) {
        actions += learner.is_expert
          ? '<button class="btn btn-ghost btn-sm" data-expert="' + EIP.escape(learner._id) + '" data-enabled="0">Disable expert</button>'
          : '<button class="btn btn-primary btn-sm" data-expert="' + EIP.escape(learner._id) + '" data-enabled="1">Enable expert</button>';
      }
      return (
        "<tr><td>" + EIP.escape(learner.full_name) + (learner.is_expert ? ' <span class="badge primary">Expert</span>' : "") +
        "</td><td>" + EIP.escape(learner.email) + "</td><td>" + EIP.escape(learner.department_name || "—") +
        "</td><td>" + EIP.badge(learner.account_status) + '</td><td><div class="row">' + actions + "</div></td></tr>"
      );
    }).join("");
    populateLearnerSelect();
  }

  function renderTrainers(data) {
    state.trainers = data.trainers || [];
    var box = document.getElementById("trainers-list");
    box.innerHTML = state.trainers.length
      ? state.trainers.map(function (trainer) {
          return (
            '<div class="attempt-row"><div><strong>' + EIP.escape(trainer.full_name) + "</strong>" +
            '<div class="small muted">' + EIP.escape(trainer.email) + (trainer.designation ? " · " + EIP.escape(trainer.designation) : "") +
            "</div></div>" + EIP.badge("EXPERT") + "</div>"
          );
        }).join("")
      : '<p class="small muted">No expert reviewers yet. Enable expert capability on an employee above.</p>';

    var select = document.getElementById("assign-trainer");
    select.innerHTML = '<option value="">Select an expert</option>' + state.trainers.map(function (trainer) {
      return '<option value="' + EIP.escape(trainer._id) + '">' + EIP.escape(trainer.full_name) +
        " (" + EIP.escape(trainer.email) + ")</option>";
    }).join("");
  }

  function populateLearnerSelect() {
    var select = document.getElementById("assign-learner");
    select.innerHTML = '<option value="">Select a learner</option>' + state.learners.map(function (learner) {
      return '<option value="' + EIP.escape(learner._id) + '">' + EIP.escape(learner.full_name) + "</option>";
    }).join("");
  }

  function loadLearners() {
    var query = "?status=" + encodeURIComponent(state.status) + "&q=" + encodeURIComponent(state.search);
    return EIP.get("/api/organizations/me/learners" + query).then(renderLearners);
  }

  function loadTrainers() {
    return EIP.get("/api/organizations/me/trainers").then(renderTrainers);
  }

  function showSnapshot(snapshot) {
    var skills = snapshot.skills || [];
    var attempts = snapshot.assessments || [];
    EIP.detailModal(
      snapshot.user.full_name + " — learner snapshot",
      '<p class="small muted">' + EIP.escape(snapshot.user.email) + " · " +
      EIP.escape((snapshot.career || {}).name || "No target career") + " · readiness " +
      ((snapshot.career || {}).readiness || 0) + "% · roadmap " +
      ((snapshot.roadmap || {}).completion || 0) + "%</p>" +
      '<div class="table-wrap"><table><thead><tr><th>Skill</th><th>Level</th><th>Verification</th></tr></thead><tbody>' +
      (skills.length ? skills.map(function (skill) {
        return "<tr><td>" + EIP.escape(skill.skill_name) + "</td><td>" + skill.proficiency + "%</td><td>" +
          EIP.badge(skill.verification_status) + "</td></tr>";
      }).join("") : '<tr><td colspan="3" class="muted">No skills recorded.</td></tr>') +
      "</tbody></table></div>" +
      "<h4>Recent assessments</h4>" +
      (attempts.length ? attempts.map(function (attempt) {
        return '<div class="attempt-row"><span>' + EIP.escape(attempt.title) + "</span>" +
          (attempt.score !== null && attempt.score !== undefined
            ? '<span class="badge">' + attempt.score + "%</span>"
            : EIP.badge(attempt.status)) + "</div>";
      }).join("") : '<p class="small muted">No attempts yet.</p>')
    );
  }

  function wire() {
    document.querySelectorAll(".tab[data-status]").forEach(function (tab) {
      tab.addEventListener("click", function () {
        document.querySelectorAll(".tab[data-status]").forEach(function (item) { item.classList.remove("active"); });
        tab.classList.add("active");
        state.status = tab.dataset.status;
        clearAlert();
        loadLearners().catch(function (err) { alertBox(err.message, "danger"); });
      });
    });

    document.getElementById("learner-search").addEventListener("input", EIP.debounce(function (event) {
      state.search = event.target.value.trim();
      loadLearners().catch(function (err) { alertBox(err.message, "danger"); });
    }, 350));

    document.getElementById("learner-refresh").addEventListener("click", function () {
      clearAlert();
      Promise.all([loadLearners(), loadTrainers()]).catch(function (err) { alertBox(err.message, "danger"); });
    });

    document.getElementById("learners-body").addEventListener("click", async function (event) {
      var snapshotButton = event.target.closest("[data-snapshot]");
      if (snapshotButton) {
        try {
          var snapshot = await EIP.get("/api/admin/learner/" + snapshotButton.dataset.snapshot);
          showSnapshot(snapshot);
        } catch (err) {
          alertBox(err.message, "danger");
        }
        return;
      }
      var expertButton = event.target.closest("[data-expert]");
      if (expertButton) {
        var enabled = expertButton.dataset.enabled === "1";
        EIP.setBusy(expertButton, true, enabled ? "Enabling…" : "Disabling…");
        try {
          await EIP.post("/api/approvals/experts/" + expertButton.dataset.expert, { enabled: enabled });
          EIP.toast("Expert capability " + (enabled ? "enabled" : "disabled") + ".", "success");
          await Promise.all([loadLearners(), loadTrainers()]);
        } catch (err) {
          EIP.setBusy(expertButton, false);
          alertBox(err.message, "danger");
        }
      }
    });

    document.getElementById("assign-form").addEventListener("submit", async function (event) {
      event.preventDefault();
      var trainerId = document.getElementById("assign-trainer").value;
      var learnerId = document.getElementById("assign-learner").value;
      if (!trainerId || !learnerId) {
        alertBox("Choose both an expert and a learner.", "warning");
        return;
      }
      var submit = document.getElementById("assign-submit");
      EIP.setBusy(submit, true, "Assigning…");
      try {
        await EIP.post("/api/approvals/assignments", { trainer_id: trainerId, learner_id: learnerId });
        EIP.toast("Reviewer assigned.", "success");
        document.getElementById("assign-form").reset();
      } catch (err) {
        alertBox(err.message, "danger");
      } finally {
        EIP.setBusy(submit, false);
      }
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    wire();
    EIP.get("/api/organizations/me")
      .then(function (context) {
        state.org = context.organization;
        return Promise.all([loadLearners(), loadTrainers()]);
      })
      .catch(function (err) { alertBox(err.message, "danger"); });
  });
})();

/* Learner skill profile and evidence. */
(function () {
  "use strict";

  function alertBox(message) {
    var box = document.getElementById("skills-alert");
    box.textContent = message;
    box.classList.remove("hidden");
  }

  function renderSkills(skills) {
    document.getElementById("sk-count").textContent = skills.length + (skills.length === 1 ? " skill" : " skills");
    document.getElementById("sk-total").textContent = skills.length;
    var verified = skills.filter(function (skill) { return skill.verification_status === "VERIFIED"; }).length;
    document.getElementById("sk-verified").textContent = verified + " verified";
    var avg = skills.length
      ? Math.round(skills.reduce(function (sum, skill) { return sum + Number(skill.proficiency || 0); }, 0) / skills.length)
      : 0;
    document.getElementById("sk-avg").textContent = avg + "%";

    var box = document.getElementById("skill-list");
    if (!skills.length) {
      box.innerHTML = EIP.empty(
        "No skills recorded",
        "Add skills from your profile to start measuring readiness.",
        '<a class="btn btn-primary btn-sm" href="/app/profile">Add a skill</a>'
      );
      return;
    }
    box.innerHTML = skills.map(function (skill) {
      var level = EIP.percent(skill.proficiency);
      var target = EIP.percent(skill.target_proficiency || 0);
      return (
        '<div class="skill-line"><div class="skill-top"><strong>' + EIP.escape(skill.skill_name) + "</strong>" +
        "<span>" + level + "%" + (target ? " / " + target + "% target" : "") + " " +
        EIP.badge(skill.verification_status || "SELF_REPORTED") + "</span></div>" +
        '<div class="progress"><span style="width:' + level + '%"></span></div>' +
        '<div class="row between"><span class="small muted">Evidence: ' + (skill.evidence_count || 0) +
        " · Checked " + EIP.fmtDate(skill.last_assessed_at) + "</span>" +
        '<a class="small" href="/app/assessments">Run skill check</a></div></div>'
      );
    }).join("");
  }

  function renderEvidence(evidence) {
    document.getElementById("sk-evidence").textContent = evidence.length;
    var box = document.getElementById("evidence-list");
    if (!evidence.length) {
      box.innerHTML = '<p class="small muted">Evidence appears after assessments, project reviews and trainer feedback.</p>';
      return;
    }
    box.innerHTML = evidence.slice(0, 40).map(function (item) {
      return (
        '<div class="attempt-row"><div><strong>' + EIP.escape(item.title || item.source_type) + "</strong>" +
        '<div class="small muted">' + EIP.escape(item.skill_name) + " · " +
        EIP.escape(EIP.titleCase(item.source_type)) + " · " + EIP.fmtDate(item.created_at) + "</div></div>" +
        '<div><span class="badge ' + (item.verified ? "success" : "warning") + '">' +
        (item.score ? Math.round(item.score) + "%" : (item.verified ? "Verified" : "Unverified")) + "</span></div></div>"
      );
    }).join("");
  }

  function render(bundle) {
    document.getElementById("sk-career").textContent = bundle.target_career ? bundle.target_career.name : "Not set";
    renderSkills(bundle.skills || []);
    renderEvidence(bundle.evidence || []);
  }

  document.addEventListener("DOMContentLoaded", function () {
    EIP.get("/api/learner/profile")
      .then(render)
      .catch(function (err) { alertBox(err.message); });
  });
})();

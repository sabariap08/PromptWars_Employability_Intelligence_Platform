/* Learner profile, skills and evidence. */
(function () {
  "use strict";

  var state = { bundle: null, careers: [] };

  function alertBox(message, type) {
    var box = document.getElementById("profile-alert");
    box.className = "alert " + (type || "danger");
    box.textContent = message;
    box.classList.remove("hidden");
  }

  function clearAlert() {
    document.getElementById("profile-alert").classList.add("hidden");
  }

  function field(label, id, value, type, placeholder) {
    return (
      '<div class="field"><label for="' + id + '">' + EIP.escape(label) + "</label>" +
      '<input id="' + id + '" type="' + (type || "text") + '" value="' +
      EIP.escape(value || "") + '" placeholder="' + EIP.escape(placeholder || "") + '"></div>'
    );
  }

  function renderEduFields(user, profile) {
    var container = document.getElementById("edu-fields");
    var isStudent = user.role === "STUDENT";
    var data = isStudent ? profile.education || {} : profile.employment || {};
    if (isStudent) {
      container.innerHTML =
        '<h3 class="small muted">Education</h3><div class="form-grid two">' +
        field("Degree / programme", "edu-degree", data.degree, "text", "B.E. Computer Science") +
        field("Academic year", "edu-year", data.academic_year, "text", "2023 – 2027") +
        field("Year of study", "edu-study", data.year_of_study, "text", "3rd Year") +
        field("Roll number", "edu-roll", data.roll_number, "text", "21CS1042") +
        "</div>";
    } else {
      container.innerHTML =
        '<h3 class="small muted">Employment</h3><div class="form-grid two">' +
        field("Designation", "emp-designation", data.designation, "text", "Software Engineer") +
        field("Employment type", "emp-type", data.employment_type, "text", "Full-time") +
        field("Years of experience", "emp-years", data.years_experience, "text", "3") +
        "</div>";
    }
  }

  function renderSkills(skills) {
    document.getElementById("skills-count").textContent = skills.length + (skills.length === 1 ? " skill" : " skills");
    var box = document.getElementById("skills-list");
    if (!skills.length) {
      box.innerHTML = EIP.empty("No skills yet", "Add the skills you can demonstrate. Levels guide the first assessment.");
      return;
    }
    box.innerHTML = skills.map(function (skill) {
      var level = EIP.percent(skill.proficiency);
      return (
        '<div class="skill-line"><div class="skill-top"><strong>' + EIP.escape(skill.skill_name) + "</strong>" +
        "<span>" + level + "% " + EIP.badge(skill.verification_status || "SELF_REPORTED") + "</span></div>" +
        '<div class="progress"><span style="width:' + level + '%"></span></div>' +
        '<div class="row between"><span class="small muted">Evidence: ' + (skill.evidence_count || 0) +
        '</span><button class="btn btn-ghost btn-sm" data-remove-skill="' + EIP.escape(skill.skill_name) + '">Remove</button></div></div>'
      );
    }).join("");
  }

  function renderCertifications(certs) {
    var box = document.getElementById("cert-list");
    if (!certs.length) {
      box.innerHTML = '<p class="small muted">No certifications submitted. Verified certifications create a skill check automatically.</p>';
      return;
    }
    box.innerHTML = certs.map(function (cert) {
      return (
        '<div class="task-card"><div class="task-top"><div><h4>' + EIP.escape(cert.name) + "</h4>" +
        '<div class="small muted">' + EIP.escape(cert.issuer) + " · " + EIP.fmtDate(cert.issued_on) + "</div></div>" +
        EIP.badge(cert.status) + "</div>" +
        '<div class="task-meta">' + (cert.skills || []).map(function (skill) {
          return '<span class="badge">' + EIP.escape(skill) + "</span>";
        }).join("") + "</div>" +
        (cert.status === "PENDING_VERIFICATION"
          ? '<div class="task-actions"><button class="btn btn-outline btn-sm" data-verify-cert="' + EIP.escape(cert._id) + '">Start verification check</button></div>'
          : "") +
        "</div>"
      );
    }).join("");
  }

  function renderProjects(projects) {
    var box = document.getElementById("project-list");
    if (!projects.length) {
      box.innerHTML = '<p class="small muted">No projects yet. A portfolio project is strong evidence for practical skills.</p>';
      return;
    }
    box.innerHTML = projects.map(function (project) {
      var followUp = (project.ai_analysis || {}).follow_up_assessment_id;
      return (
        '<div class="task-card"><div class="task-top"><div><h4>' + EIP.escape(project.name) + "</h4>" +
        '<div class="small muted">' + EIP.escape(project.description || "").slice(0, 180) + "</div></div>" +
        EIP.badge(project.status) + "</div>" +
        '<div class="task-meta">' + (project.technologies || []).map(function (tech) {
          return '<span class="badge">' + EIP.escape(tech) + "</span>";
        }).join("") + "</div>" +
        (project.repo_url ? '<a class="small" href="' + EIP.escape(project.repo_url) + '" target="_blank" rel="noopener">Open repository</a>' : "") +
        (followUp ? '<span class="small muted">Follow-up assessment created.</span>'
          : '<div class="task-actions"><button class="btn btn-outline btn-sm" data-followup="' + EIP.escape(project._id) + '">Create follow-up check</button></div>') +
        "</div>"
      );
    }).join("");
  }

  function renderEvidence(bundle) {
    var skills = bundle.skills || [];
    var verified = skills.filter(function (skill) { return skill.verification_status === "VERIFIED"; }).length;
    var evidence = bundle.evidence || [];
    var rows = [
      ["Profile completeness", bundle.completeness + "%"],
      ["Skills recorded", skills.length + " (" + verified + " verified)"],
      ["Certifications", (bundle.certifications || []).length],
      ["Projects", (bundle.projects || []).length],
      ["Evidence records", evidence.length],
      ["Target career", bundle.target_career ? bundle.target_career.name : "Not set"],
    ];
    document.getElementById("evidence-summary").innerHTML = rows.map(function (row) {
      return '<div class="ctx-row"><span>' + EIP.escape(row[0]) + "</span><strong>" + EIP.escape(row[1]) + "</strong></div>";
    }).join("");
    document.getElementById("profile-completeness").textContent = "Completeness " + bundle.completeness + "%";
  }

  function fill(bundle, careers) {
    state.bundle = bundle;
    state.careers = careers;
    var user = bundle.user;
    var profile = bundle.profile;
    document.getElementById("profile-name").value = user.full_name || "";
    document.getElementById("profile-email").value = user.email || "";
    document.getElementById("profile-phone").value = user.phone || "";
    document.getElementById("profile-hours").value = profile.weekly_hours || 6;
    document.getElementById("profile-style").value = profile.learning_style || "";
    document.getElementById("profile-soft").value = (profile.soft_skills || []).join(", ");
    document.getElementById("profile-interests").value = (profile.interests || []).join(", ");

    var careerSelect = document.getElementById("profile-career");
    careerSelect.innerHTML = '<option value="">Select a target career</option>' +
      careers.map(function (career) {
        return '<option value="' + EIP.escape(career._id) + '"' +
          (profile.target_career_id === career._id ? " selected" : "") + ">" +
          EIP.escape(career.name) + "</option>";
      }).join("");

    renderEduFields(user, profile);
    renderSkills(bundle.skills || []);
    renderCertifications(bundle.certifications || []);
    renderProjects(bundle.projects || []);
    renderEvidence(bundle);
  }

  function load() {
    return Promise.all([EIP.get("/api/learner/profile"), EIP.get("/api/public/careers")]).then(function (results) {
      fill(results[0], results[1].careers || []);
    });
  }

  function collectProfilePayload() {
    var payload = {
      phone: document.getElementById("profile-phone").value.trim(),
      target_career_id: document.getElementById("profile-career").value,
      weekly_hours: Number(document.getElementById("profile-hours").value || 6),
      learning_style: document.getElementById("profile-style").value,
      soft_skills: EIP.textToLines(document.getElementById("profile-soft").value),
      interests: EIP.textToLines(document.getElementById("profile-interests").value),
    };
    if (!state.bundle) return payload;
    if (state.bundle.user.role === "STUDENT") {
      payload.education = {
        degree: document.getElementById("edu-degree").value,
        academic_year: document.getElementById("edu-year").value,
        year_of_study: document.getElementById("edu-study").value,
        roll_number: document.getElementById("edu-roll").value,
      };
    } else {
      payload.employment = {
        designation: document.getElementById("emp-designation").value,
        employment_type: document.getElementById("emp-type").value,
        years_experience: document.getElementById("emp-years").value,
      };
    }
    return payload;
  }

  function wire() {
    var form = document.getElementById("profile-form");
    form.addEventListener("submit", async function (event) {
      event.preventDefault();
      clearAlert();
      var submit = document.getElementById("profile-save");
      EIP.setBusy(submit, true, "Saving…");
      try {
        var result = await EIP.post("/api/learner/profile", collectProfilePayload());
        EIP.setBusy(submit, false);
        EIP.toast("Profile saved.", "success");
        if (result.workflow && result.workflow.length) {
          EIP.toast("Agents updated your plan: " + result.workflow.map(function (run) { return run.label; }).join(", "), "info", 6000);
        }
        await load();
      } catch (err) {
        EIP.setBusy(submit, false);
        alertBox(err.message);
      }
    });

    var skillForm = document.getElementById("skill-form");
    skillForm.addEventListener("submit", async function (event) {
      event.preventDefault();
      var name = document.getElementById("skill-name").value.trim();
      if (!name) return;
      var button = document.getElementById("skill-add");
      EIP.setBusy(button, true);
      try {
        await EIP.post("/api/learner/skills", { name: name, level: document.getElementById("skill-level").value });
        skillForm.reset();
        EIP.toast("Skill added.", "success");
        await load();
      } catch (err) {
        alertBox(err.message);
      } finally {
        EIP.setBusy(button, false);
      }
    });

    document.getElementById("skills-list").addEventListener("click", async function (event) {
      var button = event.target.closest("[data-remove-skill]");
      if (!button) return;
      var ok = await EIP.confirmModal({
        title: "Remove skill",
        message: "This removes the skill and its self-reported evidence from your profile.",
        confirmText: "Remove",
        danger: true,
      });
      if (!ok) return;
      try {
        await EIP.del("/api/learner/skills/" + encodeURIComponent(button.dataset.removeSkill));
        EIP.toast("Skill removed.", "success");
        await load();
      } catch (err) {
        alertBox(err.message);
      }
    });

    document.getElementById("cert-form").addEventListener("submit", async function (event) {
      event.preventDefault();
      var button = document.getElementById("cert-submit");
      var data = new FormData();
      data.append("name", document.getElementById("cert-name").value.trim());
      data.append("issuer", document.getElementById("cert-issuer").value.trim());
      data.append("issued_on", document.getElementById("cert-date").value);
      data.append("skills", document.getElementById("cert-skills").value.trim());
      var file = document.getElementById("cert-file").files[0];
      if (file) data.append("file", file);
      EIP.setBusy(button, true, "Submitting…");
      try {
        var result = await EIP.upload("/api/learner/certifications", data);
        EIP.setBusy(button, false);
        document.getElementById("cert-form").reset();
        EIP.toast("Certification submitted for verification.", "success");
        if (result.assessment_id) {
          EIP.toast("A verification check was prepared. Open Assessments to complete it.", "info", 6000);
        }
        await load();
      } catch (err) {
        EIP.setBusy(button, false);
        alertBox(err.message);
      }
    });

    document.getElementById("project-form").addEventListener("submit", async function (event) {
      event.preventDefault();
      var button = document.getElementById("project-submit");
      var payload = {
        name: document.getElementById("project-name").value.trim(),
        description: document.getElementById("project-description").value.trim(),
        technologies: EIP.textToLines(document.getElementById("project-tech").value),
        repo_url: document.getElementById("project-repo").value.trim(),
      };
      EIP.setBusy(button, true, "Submitting…");
      try {
        var result = await EIP.post("/api/learner/projects", payload);
        EIP.setBusy(button, false);
        document.getElementById("project-form").reset();
        EIP.toast("Project submitted.", "success");
        if (result.assessment_id) {
          EIP.toast("A follow-up assessment was created.", "info", 5000);
        }
        await load();
      } catch (err) {
        EIP.setBusy(button, false);
        alertBox(err.message);
      }
    });

    document.getElementById("cert-list").addEventListener("click", async function (event) {
      var button = event.target.closest("[data-verify-cert]");
      if (!button) return;
      try {
        await EIP.post("/api/assessments/certifications/" + button.dataset.verifyCert + "/verify", {});
        EIP.toast("Verification check ready. Opening assessments…", "success");
        window.location.href = "/app/assessments";
      } catch (err) {
        alertBox(err.message);
      }
    });

    document.getElementById("project-list").addEventListener("click", async function (event) {
      var button = event.target.closest("[data-followup]");
      if (!button) return;
      try {
        await EIP.post("/api/assessments/projects/" + button.dataset.followup + "/follow-up", {});
        EIP.toast("Follow-up assessment created. Opening assessments…", "success");
        window.location.href = "/app/assessments";
      } catch (err) {
        alertBox(err.message);
      }
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    wire();
    load().catch(function (err) { alertBox(err.message); });
  });
})();

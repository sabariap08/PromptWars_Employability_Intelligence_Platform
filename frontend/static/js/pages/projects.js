/* Learner portfolio projects and certifications. */
(function () {
  "use strict";

  function alertBox(message) {
    var box = document.getElementById("projects-alert");
    box.textContent = message;
    box.classList.remove("hidden");
  }

  function renderProjects(projects) {
    document.getElementById("pj-total").textContent = projects.length;
    document.getElementById("pj-verified").textContent =
      projects.filter(function (project) { return project.status === "VERIFIED"; }).length;
    var tech = {};
    projects.forEach(function (project) {
      (project.technologies || []).forEach(function (item) { tech[item] = true; });
    });
    document.getElementById("pj-tech").textContent = Object.keys(tech).length;

    var box = document.getElementById("project-list");
    if (!projects.length) {
      box.innerHTML = EIP.empty(
        "No projects yet",
        "A portfolio project is strong evidence for practical skills.",
        '<a class="btn btn-primary btn-sm" href="/app/profile">Submit a project</a>'
      );
      return;
    }
    box.innerHTML = projects.map(function (project) {
      var followUp = (project.ai_analysis || {}).follow_up_assessment_id;
      return (
        '<div class="task-card"><div class="task-top"><div><h4>' + EIP.escape(project.name) + "</h4>" +
        '<div class="small muted">' + EIP.escape((project.description || "").slice(0, 220)) + "</div></div>" +
        EIP.badge(project.status) + "</div>" +
        '<div class="task-meta">' + (project.technologies || []).map(function (item) {
          return '<span class="badge">' + EIP.escape(item) + "</span>";
        }).join("") + "</div>" +
        '<div class="row between"><span class="small muted">Submitted ' + EIP.fmtDate(project.created_at) + "</span>" +
        (project.repo_url
          ? '<a class="small" href="' + EIP.escape(project.repo_url) + '" target="_blank" rel="noopener">Open link</a>'
          : "") + "</div>" +
        (followUp ? '<span class="small muted">Follow-up assessment prepared.</span>' : "") +
        "</div>"
      );
    }).join("");
  }

  function renderCertifications(certs) {
    document.getElementById("pj-certs").textContent = certs.length;
    var box = document.getElementById("cert-list");
    if (!certs.length) {
      box.innerHTML = '<p class="small muted">No certifications submitted yet.</p>';
      return;
    }
    box.innerHTML = certs.map(function (cert) {
      return (
        '<div class="attempt-row"><div><strong>' + EIP.escape(cert.name) + "</strong>" +
        '<div class="small muted">' + EIP.escape(cert.issuer || "") + " · " + EIP.fmtDate(cert.issued_on) + "</div></div>" +
        EIP.badge(cert.status) + "</div>"
      );
    }).join("");
  }

  document.addEventListener("DOMContentLoaded", function () {
    EIP.get("/api/learner/profile")
      .then(function (bundle) {
        renderProjects(bundle.projects || []);
        renderCertifications(bundle.certifications || []);
      })
      .catch(function (err) { alertBox(err.message); });
  });
})();

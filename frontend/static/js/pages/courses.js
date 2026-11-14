/* Course catalog, recommendations, enrolments and module progress. */
(function () {
  "use strict";

  var state = { tab: "catalog", catalog: [], recommended: [], enrolled: [] };

  function alertBox(message) {
    var box = document.getElementById("courses-alert");
    box.textContent = message;
    box.classList.remove("hidden");
  }

  function clearAlert() {
    document.getElementById("courses-alert").classList.add("hidden");
  }

  function courseCard(course, mode) {
    var enrollment = course.enrollment;
    var progress = EIP.percent(enrollment ? enrollment.progress : 0);
    var meta = [
      course.provider || "EIP catalog",
      EIP.titleCase(course.difficulty),
      (course.duration_hours || 0) + "h",
      course.module_count + " modules",
    ].filter(Boolean).join(" · ");
    var action = enrollment
      ? '<button class="btn btn-outline btn-sm" data-open-course="' + EIP.escape(course._id) + '">' +
        (enrollment.status === "COMPLETED" ? "Review" : "Continue") + "</button>"
      : '<button class="btn btn-primary btn-sm" data-enroll-course="' + EIP.escape(course._id) + '">Enrol</button>';
    return (
      '<div class="task-card"><div class="task-top"><div><h4>' + EIP.escape(course.title) + "</h4>" +
      '<div class="small muted">' + EIP.escape(meta) + "</div></div>" +
      (enrollment ? EIP.badge(enrollment.status) : EIP.badge(course.difficulty)) + "</div>" +
      (course.reason ? '<p class="small"><strong>Why this course:</strong> ' + EIP.escape(course.reason) + "</p>"
        : '<p class="small muted">' + EIP.escape((course.description || "").slice(0, 220)) + "</p>") +
      '<div class="task-meta">' + (course.skill_names || []).map(function (skill) {
        return '<span class="badge">' + EIP.escape(skill) + "</span>";
      }).join("") + "</div>" +
      (enrollment
        ? '<div class="progress"><span style="width:' + progress + '%"></span></div>' +
          '<div class="small muted">' + progress + "% complete</div>"
        : "") +
      '<div class="task-actions"><button class="btn btn-ghost btn-sm" data-open-course="' +
      EIP.escape(course._id) + '">Details</button>' + action + "</div></div>"
    );
  }

  function renderStats() {
    document.getElementById("co-total").textContent = state.catalog.length;
    document.getElementById("co-enrolled").textContent = state.enrolled.length;
    document.getElementById("co-completed").textContent = state.enrolled.filter(function (course) {
      return course.enrollment && course.enrollment.status === "COMPLETED";
    }).length;
    document.getElementById("co-recommended").textContent = state.recommended.length;
  }

  function render() {
    var box = document.getElementById("course-list");
    var items;
    if (state.tab === "recommended") {
      items = state.recommended;
    } else if (state.tab === "enrolled") {
      items = state.enrolled;
    } else {
      items = state.catalog;
    }
    document.querySelectorAll("[data-tab]").forEach(function (button) {
      button.classList.toggle("active", button.dataset.tab === state.tab);
    });
    document.getElementById("course-filters").classList.toggle("hidden", state.tab !== "catalog");
    renderStats();
    if (!items.length) {
      var empty = {
        catalog: ["No courses found", "Try a different search or skill filter."],
        recommended: ["No recommendations yet", "Set a target career and add skills to get matched courses."],
        enrolled: ["You are not enrolled yet", "Open the catalog and enrol in your first course."],
      }[state.tab];
      box.innerHTML = EIP.empty(empty[0], empty[1],
        '<a class="btn btn-primary btn-sm" href="/app/courses">Browse catalog</a>');
      return;
    }
    box.innerHTML = items.map(function (course) { return courseCard(course, state.tab); }).join("");
  }

  function catalogQuery() {
    var params = [];
    var search = document.getElementById("course-search").value.trim();
    var skill = document.getElementById("course-skill").value.trim();
    var difficulty = document.getElementById("course-difficulty").value;
    if (search) params.push("q=" + encodeURIComponent(search));
    if (skill) params.push("skill=" + encodeURIComponent(skill));
    if (difficulty) params.push("difficulty=" + encodeURIComponent(difficulty));
    return params.length ? "?" + params.join("&") : "";
  }

  function loadAll() {
    EIP.loading(document.getElementById("course-list"), 3);
    return Promise.all([
      EIP.get("/api/learning/courses" + catalogQuery()),
      EIP.get("/api/learning/recommended-courses"),
      EIP.get("/api/learning/enrollments"),
    ]).then(function (results) {
      state.catalog = results[0].courses || [];
      state.recommended = results[1].courses || [];
      state.enrolled = results[2].courses || [];
      render();
    });
  }

  function moduleRow(module, enrollment) {
    var checked = module.completed ? " checked" : "";
    var disabled = enrollment ? "" : " disabled";
    return (
      '<label class="ctx-row" style="cursor:pointer"><span><input type="checkbox" data-module-id="' +
      EIP.escape(module.id) + '"' + checked + disabled + "> " + EIP.escape(module.title) + "</span>" +
      '<span class="small muted">Module ' + (module.position || "") + "</span></label>"
    );
  }

  function openCourse(courseId) {
    clearAlert();
    EIP.get("/api/learning/courses/" + encodeURIComponent(courseId))
      .then(function (data) {
        var course = data.course;
        var enrollment = course.enrollment;
        var html =
          '<div class="stack"><div class="row between"><span class="small muted">' +
          EIP.escape(course.provider || "") + " · " + EIP.escape(EIP.titleCase(course.difficulty)) + " · " +
          (course.duration_hours || 0) + "h</span>" + (enrollment ? EIP.badge(enrollment.status) : "") + "</div>" +
          '<p class="small muted">' + EIP.escape(course.description || "") + "</p>" +
          '<div class="task-meta">' + (course.skill_names || []).map(function (skill) {
            return '<span class="badge">' + EIP.escape(skill) + "</span>";
          }).join("") + "</div>" +
          (enrollment
            ? '<div class="progress"><span style="width:' + EIP.percent(enrollment.progress) + '%"></span></div>' +
              '<div class="small muted">' + EIP.percent(enrollment.progress) + "% complete</div>"
            : '<div class="alert info small">Enrol to track modules and build evidence.</div>') +
          '<div class="stack">' + (course.modules || []).map(function (module) {
            return moduleRow(module, enrollment);
          }).join("") + "</div>" +
          (course.url ? '<a class="small" href="' + EIP.escape(course.url) + '" target="_blank" rel="noopener">Open course material</a>' : "") +
          "</div>";
        var modal = EIP.detailModal(course.title, html);
        modal.element.querySelector("[data-close]").addEventListener("click", modal.close);
        if (!enrollment) {
          var actions = modal.element.querySelector(".form-actions");
          var enrol = document.createElement("button");
          enrol.className = "btn btn-primary";
          enrol.type = "button";
          enrol.textContent = "Enrol now";
          enrol.addEventListener("click", function () {
            EIP.setBusy(enrol, true, "Enrolling…");
            EIP.post("/api/learning/courses/" + encodeURIComponent(course._id) + "/enroll", {})
              .then(function () {
                modal.close();
                EIP.toast("Enrolled successfully.", "success");
                return loadAll();
              })
              .catch(function (err) {
                EIP.setBusy(enrol, false);
                EIP.toast(err.message, "danger");
              });
          });
          actions.insertBefore(enrol, actions.firstChild);
        }
        modal.element.addEventListener("change", function (event) {
          var input = event.target.closest("[data-module-id]");
          if (!input || !enrollment) return;
          input.disabled = true;
          EIP.post(
            "/api/learning/enrollments/" + encodeURIComponent(enrollment._id) + "/progress",
            { module_id: input.dataset.moduleId, completed: input.checked }
          ).then(function () {
            modal.close();
            EIP.toast("Course progress updated.", "success");
            return loadAll();
          }).catch(function (err) {
            input.checked = !input.checked;
            input.disabled = false;
            EIP.toast(err.message, "danger");
          });
        });
      })
      .catch(function (err) { alertBox(err.message); });
  }

  function wire() {
    document.querySelectorAll("[data-tab]").forEach(function (button) {
      button.addEventListener("click", function () {
        state.tab = button.dataset.tab;
        render();
      });
    });
    document.getElementById("course-filters").addEventListener("submit", function (event) {
      event.preventDefault();
      loadAll().catch(function (err) { alertBox(err.message); });
    });
    document.getElementById("course-list").addEventListener("click", function (event) {
      var open = event.target.closest("[data-open-course]");
      if (open) {
        openCourse(open.dataset.openCourse);
        return;
      }
      var enrol = event.target.closest("[data-enroll-course]");
      if (!enrol) return;
      EIP.setBusy(enrol, true, "Enrolling…");
      EIP.post("/api/learning/courses/" + encodeURIComponent(enrol.dataset.enrollCourse) + "/enroll", {})
        .then(function (result) {
          EIP.setBusy(enrol, false);
          EIP.toast(result.already_enrolled ? "Already enrolled." : "Enrolled successfully.", "success");
          return loadAll();
        })
        .catch(function (err) {
          EIP.setBusy(enrol, false);
          alertBox(err.message);
        });
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    var tab = new URLSearchParams(window.location.search).get("tab");
    if (tab === "recommended" || tab === "enrolled") state.tab = tab;
    wire();
    loadAll().catch(function (err) { alertBox(err.message); });
  });
})();

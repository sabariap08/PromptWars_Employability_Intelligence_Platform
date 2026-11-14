(function () {
  "use strict";

  var adminCourses = [];

  function alertBox(message, type) {
    var box = document.getElementById("content-alert");
    box.className = "alert " + (type || "warning");
    box.textContent = message;
    box.classList.remove("hidden");
  }

  function clearAlert() {
    document.getElementById("content-alert").classList.add("hidden");
  }

  function value(id) {
    var element = document.getElementById(id);
    return element ? element.value.trim() : "";
  }

  function splitList(raw) {
    return String(raw || "").split(/[\n,;]+/).map(function (item) { return item.trim(); }).filter(Boolean);
  }

  function splitLines(raw) {
    return String(raw || "").split(/\r?\n/).map(function (item) { return item.trim(); }).filter(Boolean);
  }

  function renderCourses(courses) {
    adminCourses = courses;
    document.getElementById("content-course-count").textContent =
      courses.length + (courses.length === 1 ? " course" : " courses");
    var box = document.getElementById("content-course-list");
    if (!courses.length) {
      box.innerHTML = '<p class="small muted">No courses in the catalog yet.</p>';
      return;
    }
    box.innerHTML = courses.map(function (course) {
      return (
        '<div class="attempt-row"><div><strong>' + EIP.escape(course.title) + "</strong>" +
        '<div class="small muted">' + EIP.escape(course.provider || "No provider") + " &middot; " +
        EIP.escape(EIP.titleCase(course.difficulty)) + " &middot; " + (course.duration_hours || 0) + "h &middot; " +
        (course.modules || []).length + " modules</div></div>" +
        '<div class="row">' + EIP.badge(course.is_active === false ? "INACTIVE" : "ACTIVE") +
        '<button class="btn btn-ghost btn-sm" data-toggle-course="' + EIP.escape(course._id) +
        '" data-course-active="' + (course.is_active === false ? "false" : "true") + '">' +
        (course.is_active === false ? "Activate" : "Deactivate") + "</button></div></div>"
      );
    }).join("");
  }

  function loadCourses() {
    return EIP.get("/api/admin/courses").then(function (data) {
      renderCourses(data.courses || []);
    });
  }

  function submitForm(formId, handler, successMessage) {
    document.getElementById(formId).addEventListener("submit", async function (event) {
      event.preventDefault();
      var button = event.target.querySelector("button[type='submit']");
      EIP.setBusy(button, true, "Saving...");
      try {
        await handler();
        clearAlert();
        EIP.toast(successMessage, "success");
        event.target.reset();
        await loadCourses();
      } catch (err) {
        alertBox(err.message, "danger");
      } finally {
        EIP.setBusy(button, false);
      }
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    loadCourses().catch(function (err) { alertBox(err.message, "danger"); });

    submitForm("content-course-form", function () {
      return EIP.post("/api/admin/courses", {
        title: value("content-course-title"),
        provider: value("content-course-provider"),
        url: value("content-course-url"),
        difficulty: value("content-course-difficulty"),
        duration_hours: Number(value("content-course-hours") || 6),
        skill_names: splitList(value("content-course-skills")),
        modules: splitLines(value("content-course-modules")),
        description: value("content-course-description"),
      });
    }, "Course created.");

    submitForm("content-question-form", function () {
      return EIP.post("/api/admin/catalog/questions", {
        skill_name: value("content-q-skill"),
        question_type: value("content-q-type"),
        difficulty: value("content-q-difficulty"),
        points: Number(value("content-q-points") || 1),
        prompt: value("content-q-prompt"),
        options: value("content-q-options"),
        correct_option: value("content-q-correct"),
        correct_keywords: splitList(value("content-q-keywords")),
        explanation: value("content-q-explanation"),
      });
    }, "Question created.");

    document.getElementById("content-course-list").addEventListener("click", async function (event) {
      var button = event.target.closest("[data-toggle-course]");
      if (!button) return;
      var course = adminCourses.find(function (item) { return item._id === button.dataset.toggleCourse; });
      if (!course) return;
      EIP.setBusy(button, true, "Saving...");
      try {
        await EIP.put("/api/admin/courses/" + encodeURIComponent(course._id), {
          title: course.title,
          provider: course.provider,
          url: course.url,
          difficulty: course.difficulty,
          duration_hours: course.duration_hours,
          skill_names: course.skill_names,
          modules: course.modules || [],
          description: course.description,
          is_active: button.dataset.courseActive !== "true",
        });
        EIP.toast("Course updated.", "success");
        await loadCourses();
      } catch (err) {
        alertBox(err.message, "danger");
        EIP.setBusy(button, false);
      }
    });
  });
})();

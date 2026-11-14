/* Assessment lifecycle: list, start, take, submit, review. */
(function () {
  "use strict";

  var state = {
    attempt: null,
    timer: null,
    integrity: { tab_switch_count: 0, visibility_events: 0 },
  };

  function alertBox(message, type) {
    var box = document.getElementById("assessment-alert");
    box.className = "alert " + (type || "warning");
    box.textContent = message;
    box.classList.remove("hidden");
  }

  function clearAlert() {
    document.getElementById("assessment-alert").classList.add("hidden");
  }

  function purposeBadge(purpose) {
    return '<span class="badge primary">' + EIP.escape(EIP.titleCase(purpose)) + "</span>";
  }

  function renderAssessments(payload) {
    var list = document.getElementById("assessments-list");
    document.getElementById("assessment-count").textContent = payload.assessments.length + " ready";
    if (!payload.assessments.length) {
      list.innerHTML = EIP.empty("No assessments yet", "Generate a baseline to start measuring your skills.");
      return;
    }
    list.innerHTML = payload.assessments.map(function (item) {
      var attempts = item.attempts || [];
      var active = attempts.find(function (a) { return a.status === "IN_PROGRESS"; });
      return (
        '<div class="task-card"><div class="task-top"><div><h4>' + EIP.escape(item.title) + "</h4>" +
        '<div class="task-meta">' + purposeBadge(item.purpose) +
        "<span>" + Math.round(item.time_limit_seconds / 60) + " min</span>" +
        "<span>" + attempts.length + " attempt(s)</span></div></div>" +
        (active
          ? '<button class="btn btn-amber btn-sm" data-resume="' + EIP.escape(active._id) + '">Resume</button>'
          : '<button class="btn btn-primary btn-sm" data-start="' + EIP.escape(item.assessment_id) + '">Start</button>') +
        "</div><div class=\"task-meta\">" + (item.skill_names || []).slice(0, 8).map(function (skill) {
          return '<span class="badge">' + EIP.escape(skill) + "</span>";
        }).join("") + "</div></div>"
      );
    }).join("");
  }

  function renderHistory(payload) {
    var box = document.getElementById("history-list");
    if (!payload.history.length) {
      box.innerHTML = EIP.empty("No attempts yet", "Start an assessment above to build your evidence trail.");
      return;
    }
    box.innerHTML = payload.history.map(function (attempt) {
      var score = attempt.score === null || attempt.score === undefined ? null : attempt.score;
      var actions = "";
      if (attempt.status === "EVALUATED") {
        actions = '<button class="btn btn-outline btn-sm" data-view-result="' + EIP.escape(attempt._id) + '">View result</button>';
      } else if (attempt.status === "IN_PROGRESS") {
        actions = '<button class="btn btn-amber btn-sm" data-resume="' + EIP.escape(attempt._id) + '">Resume</button>';
      }
      return (
        '<div class="attempt-row"><div><strong>' + EIP.escape(attempt.title) + "</strong>" +
        '<div class="small muted">' + EIP.escape(EIP.titleCase(attempt.purpose)) + " · " +
        EIP.fmtDate(attempt.created_at, true) +
        (attempt.risk_level && attempt.risk_level !== "LOW" ? " · risk " + EIP.escape(attempt.risk_level) : "") +
        "</div></div><div class=\"row\">" +
        (score !== null
          ? '<span class="badge ' + (score >= 65 ? "success" : score >= 40 ? "warning" : "danger") + '">' + score + "%</span>"
          : EIP.badge(attempt.status)) +
        actions + "</div></div>"
      );
    }).join("");
  }

  function renderSkillOptions(payload) {
    var box = document.getElementById("skill-check-options");
    var skills = payload.skills || [];
    if (!skills.length) {
      box.innerHTML = '<p class="small muted">Add skills to your profile first.</p>';
      return;
    }
    box.innerHTML = skills.map(function (skill, index) {
      return (
        '<label class="option"><input type="checkbox" name="skill-check" value="' + EIP.escape(skill.skill_name) + '" id="sc-' + index + '">' +
        '<span><strong>' + EIP.escape(skill.skill_name) + "</strong> <span class=\"small muted\">" +
        (skill.proficiency || 0) + "% · " + EIP.escape(EIP.titleCase(skill.verification_status || "SELF_REPORTED")) +
        "</span></span></label>"
      );
    }).join("");
  }

  function load() {
    return Promise.all([EIP.get("/api/assessments"), EIP.get("/api/learner/profile")]).then(function (results) {
      renderAssessments(results[0]);
      renderHistory(results[0]);
      renderSkillOptions(results[1]);
    });
  }

  function stopTimer() {
    if (state.timer) {
      clearInterval(state.timer);
      state.timer = null;
    }
  }

  function startTimer(expiresAt) {
    stopTimer();
    var label = document.getElementById("exam-timer");
    if (!expiresAt) {
      label.textContent = "Untimed";
      return;
    }
    var end = new Date(expiresAt).getTime();
    var tick = function () {
      var remaining = Math.max(0, Math.round((end - Date.now()) / 1000));
      var minutes = Math.floor(remaining / 60);
      var seconds = remaining % 60;
      label.textContent = String(minutes).padStart(2, "0") + ":" + String(seconds).padStart(2, "0");
      if (remaining === 0) {
        label.textContent = "Time up — submit";
        stopTimer();
      }
    };
    tick();
    state.timer = setInterval(tick, 1000);
  }

  function showExamShell(title, subtitle, statusText) {
    document.getElementById("assessment-view").classList.add("hidden");
    document.getElementById("exam-view").classList.remove("hidden");
    document.getElementById("exam-title").textContent = title;
    document.getElementById("exam-sub").textContent = subtitle;
    var status = document.getElementById("exam-status");
    status.textContent = statusText;
    document.getElementById("exam-result").classList.add("hidden");
    document.getElementById("exam-form").classList.remove("hidden");
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function renderQuestions(attempt) {
    var box = document.getElementById("exam-questions");
    box.innerHTML = attempt.questions.map(function (question, index) {
      var meta = '<div class="q-head"><span>Question ' + (index + 1) + " of " + attempt.questions.length +
        "</span><span>" + EIP.escape(question.skill_name) + " · " + EIP.escape(EIP.titleCase(question.difficulty || "")) +
        " · " + (question.points || 1) + " pt</span></div>";
      if (question.question_type === "PRACTICAL_WRITTEN") {
        return (
          '<div class="question">' + meta + '<div class="q-prompt">' + EIP.escape(question.prompt) + "</div>" +
          '<textarea name="t-' + EIP.escape(question.question_id) + '" rows="5" placeholder="Write a structured answer. Mention the concepts and trade-offs you would apply."></textarea>' +
          '<div class="small muted" style="margin-top:0.3rem">Practical answers are scored against expected concepts.</div></div>'
        );
      }
      var options = question.options || [];
      return (
        '<div class="question">' + meta + '<div class="q-prompt">' + EIP.escape(question.prompt) + "</div>" +
        options.map(function (option, optionIndex) {
          var key = option && option.key ? option.key : String.fromCharCode(65 + optionIndex);
          var text = option && option.text !== undefined ? option.text : option;
          return (
            '<label class="option"><input type="radio" name="q-' + EIP.escape(question.question_id) + '" value="' + key + '">' +
            '<span><span class="key">' + key + ".</span> " + EIP.escape(text) + "</span></label>"
          );
        }).join("") + "</div>"
      );
    }).join("");
  }

  function showAttempt(attempt) {
    state.attempt = attempt;
    showExamShell(attempt.title, "Attempt " + (attempt.attempt_number || 1) + " · " + EIP.titleCase(attempt.purpose), "In progress");
    renderQuestions(attempt);
    startTimer(attempt.expires_at);
    document.getElementById("exam-integrity").textContent =
      "Tab switches: " + state.integrity.tab_switch_count + " · Visibility changes: " + state.integrity.visibility_events;
  }

  function scoreClass(score) {
    return score >= 65 ? "success" : score >= 40 ? "warning" : "danger";
  }

  function showResult(result, workflow) {
    stopTimer();
    state.attempt = null;
    showExamShell(result.title, "Result · " + EIP.titleCase(result.purpose), "Evaluated");
    document.getElementById("exam-form").classList.add("hidden");
    document.getElementById("exam-status").className = "badge success";
    document.getElementById("exam-timer").textContent = "—";

    var topicRows = Object.keys(result.topic_scores || {}).map(function (skill) {
      var score = result.topic_scores[skill];
      return (
        '<div class="topic-score"><div class="top"><strong>' + EIP.escape(skill) + "</strong><span>" + score + "%</span></div>" +
        '<div class="progress"><span style="width:' + EIP.percent(score) + '%"></span></div></div>'
      );
    }).join("");

    var review = (result.questions || []).map(function (item) {
      var status = item.correct === true ? "correct" : item.correct === false ? "wrong" : "pending";
      return (
        '<div class="review-item ' + status + '"><div class="row between"><strong>' + EIP.escape(item.prompt) + "</strong>" +
        '<span class="badge">' + item.points_awarded + "/" + item.points_possible + "</span></div>" +
        '<div class="small muted">' + EIP.escape(item.skill_name) +
        (item.selected_option ? " · your answer " + EIP.escape(item.selected_option) : "") +
        (item.correct_option ? " · correct " + EIP.escape(item.correct_option) : "") + "</div>" +
        (item.text_answer ? '<div class="small" style="margin-top:0.25rem">' + EIP.escape(item.text_answer).slice(0, 400) + "</div>" : "") +
        "</div>"
      );
    }).join("");

    var workflowRows = (workflow || []).map(function (run) {
      return (
        '<li><span class="item-top"><span><strong>' + EIP.escape(run.label) + "</strong> · " +
        EIP.escape(run.provider) + "</span>" + EIP.badge(run.status) + "</span>" +
        '<span class="small muted">' + run.duration_ms + "ms" + (run.handoff_to ? " → next agent" : "") + "</span></li>"
      );
    }).join("");

    var risk = (result.integrity || {}).risk_level || "LOW";
    document.getElementById("exam-result").innerHTML =
      '<div class="card"><div class="row between"><div class="row"><div class="score-ring ' + EIP.scoreClass(result.score) + '">' +
      (result.score === null || result.score === undefined ? "—" : result.score + "%") + "</div>" +
      "<div><h2 style=\"margin:0\">" + EIP.escape(result.title) + "</h2><p class=\"small muted\" style=\"margin:0\">" +
      EIP.escape(result.summary || "Assessment evaluated.") + "</p></div></div>" +
      '<span class="badge ' + (risk === "LOW" ? "success" : "warning") + '">Integrity ' + EIP.escape(risk) + "</span></div></div>" +
      '<div class="grid two"><div class="card"><h3>Topic scores</h3><div class="result-grid">' +
      (topicRows || '<p class="small muted">No topic scores recorded.</p>') + "</div></div>" +
      '<div class="card"><h3>Agent workflow</h3>' +
      (workflowRows ? '<ul class="list-plain">' + workflowRows + "</ul>" : '<p class="small muted">No agents ran for this attempt.</p>') +
      "</div></div>" +
      '<div class="card"><h3>Question review</h3><div class="stack">' + review + "</div></div>" +
      '<div class="form-actions"><button class="btn btn-primary" id="result-back" type="button">Back to assessments</button>' +
      '<a class="btn btn-outline" href="/app/roadmap">Open updated roadmap</a></div>';
    document.getElementById("exam-result").classList.remove("hidden");
    document.getElementById("result-back").addEventListener("click", backToList);
  }

  function backToList() {
    stopTimer();
    state.attempt = null;
    document.getElementById("exam-view").classList.add("hidden");
    document.getElementById("assessment-view").classList.remove("hidden");
    document.getElementById("exam-status").className = "badge warning";
    load().catch(function (err) { alertBox(err.message, "danger"); });
  }

  async function startAssessment(assessmentId) {
    clearAlert();
    try {
      var attempt = await EIP.post("/api/assessments/" + assessmentId + "/start", {});
      state.integrity = { tab_switch_count: 0, visibility_events: 0 };
      showAttempt(attempt);
    } catch (err) {
      alertBox(err.message, "danger");
    }
  }

  async function resumeAttempt(attemptId) {
    clearAlert();
    try {
      var data = await EIP.get("/api/assessments/attempts/" + attemptId);
      if (data.status === "IN_PROGRESS" && data.questions && data.questions.length) {
        state.integrity = { tab_switch_count: 0, visibility_events: 0 };
        showAttempt(data);
      } else {
        showResult(data, []);
      }
    } catch (err) {
      alertBox(err.message, "danger");
    }
  }

  async function viewResult(attemptId) {
    clearAlert();
    try {
      var result = await EIP.get("/api/assessments/attempts/" + attemptId + "/result");
      showResult(result, []);
    } catch (err) {
      alertBox(err.message, "danger");
    }
  }

  function wire() {
    document.getElementById("baseline-btn").addEventListener("click", async function (event) {
      var button = event.currentTarget;
      EIP.setBusy(button, true, "Preparing…");
      try {
        var assessment = await EIP.post("/api/assessments/baseline", {});
        EIP.toast("Baseline prepared: " + assessment.title, "success");
        await load();
        alertBox("Baseline ready. Choose Start next to your baseline assessment.", "success");
      } catch (err) {
        alertBox(err.message, "danger");
      } finally {
        EIP.setBusy(button, false);
      }
    });

    document.getElementById("skill-check-form").addEventListener("submit", async function (event) {
      event.preventDefault();
      var checked = Array.prototype.slice.call(document.querySelectorAll("input[name='skill-check']:checked"))
        .map(function (input) { return input.value; });
      if (!checked.length) {
        alertBox("Choose at least one skill.", "warning");
        return;
      }
      if (checked.length > 4) {
        alertBox("Choose up to four skills.", "warning");
        return;
      }
      try {
        await EIP.post("/api/assessments/skill-check", {
          skills: checked,
          title: document.getElementById("skill-check-title").value.trim(),
        });
        EIP.toast("Skill check created.", "success");
        document.getElementById("skill-check-form").reset();
        await load();
      } catch (err) {
        alertBox(err.message, "danger");
      }
    });

    document.getElementById("assessments-list").addEventListener("click", function (event) {
      var start = event.target.closest("[data-start]");
      if (start) { startAssessment(start.dataset.start); return; }
      var resume = event.target.closest("[data-resume]");
      if (resume) resumeAttempt(resume.dataset.resume);
    });

    document.getElementById("history-list").addEventListener("click", function (event) {
      var view = event.target.closest("[data-view-result]");
      if (view) { viewResult(view.dataset.viewResult); return; }
      var resume = event.target.closest("[data-resume]");
      if (resume) resumeAttempt(resume.dataset.resume);
    });

    document.getElementById("exam-exit").addEventListener("click", async function () {
      if (state.attempt) {
        var ok = await EIP.confirmModal({
          title: "Leave assessment",
          message: "Your attempt stays open but nothing is submitted. You can resume it from history.",
          confirmText: "Leave",
        });
        if (!ok) return;
      }
      backToList();
    });

    document.getElementById("exam-form").addEventListener("submit", async function (event) {
      event.preventDefault();
      if (!state.attempt) return;
      var answers = {};
      state.attempt.questions.forEach(function (question) {
        if (question.question_type === "PRACTICAL_WRITTEN") {
          var textarea = document.querySelector("[name='t-" + question.question_id + "']");
          if (textarea && textarea.value.trim()) {
            answers[question.question_id] = { text_answer: textarea.value.trim() };
          }
        } else {
          var checked = document.querySelector("input[name='q-" + question.question_id + "']:checked");
          if (checked) answers[question.question_id] = { selected_option: checked.value };
        }
      });
      if (!Object.keys(answers).length) {
        alertBox("Answer at least one question before submitting.", "warning");
        return;
      }
      var submit = document.getElementById("exam-submit");
      EIP.setBusy(submit, true, "Submitting…");
      try {
        var data = await EIP.post("/api/assessments/attempts/" + state.attempt._id + "/submit", {
          answers: answers,
          integrity: {
            tab_switch_count: state.integrity.tab_switch_count,
            visibility_events: state.integrity.visibility_events,
            events: [],
          },
        });
        EIP.setBusy(submit, false);
        EIP.toast("Assessment evaluated. Readiness updated.", "success");
        showResult(data.attempt, data.workflow);
      } catch (err) {
        EIP.setBusy(submit, false);
        alertBox(err.message, "danger");
      }
    });

    document.getElementById("refresh-btn").addEventListener("click", function () {
      clearAlert();
      load().catch(function (err) { alertBox(err.message, "danger"); });
    });

    document.addEventListener("visibilitychange", function () {
      if (!state.attempt) return;
      if (document.hidden) {
        state.integrity.visibility_events += 1;
        state.integrity.tab_switch_count += 1;
        var label = document.getElementById("exam-integrity");
        if (label) {
          label.textContent = "Tab switches: " + state.integrity.tab_switch_count +
            " · Visibility changes: " + state.integrity.visibility_events;
        }
      }
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    wire();
    load().catch(function (err) { alertBox(err.message, "danger"); });
  });
})();

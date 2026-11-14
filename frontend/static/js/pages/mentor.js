/* Context-grounded AI mentor chat. */
(function () {
  "use strict";

  var busy = false;

  function messageNode(message) {
    var role = message.role === "user" ? "user" : "assistant";
    var meta = role === "assistant"
      ? '<span class="msg-meta">' + EIP.escape(message.provider || "deterministic-fallback") + "</span>"
      : "";
    return '<div class="msg ' + role + '">' + EIP.escape(message.content) + meta + "</div>";
  }

  function scrollLog() {
    var log = document.getElementById("chat-log");
    log.scrollTop = log.scrollHeight;
  }

  function appendMessage(message) {
    var log = document.getElementById("chat-log");
    var wrapper = document.createElement("div");
    wrapper.innerHTML = messageNode(message);
    log.appendChild(wrapper.firstChild);
    scrollLog();
  }

  function renderContext(context) {
    var panel = document.getElementById("mentor-panel");
    var rows = [
      ["Target career", context.career_name || "Not set"],
      ["Readiness", (context.readiness || 0) + "%"],
      ["Verified skills", (context.verified_skills || 0) + " of " + (context.total_skills || 0)],
      ["Latest score", context.latest_score === null || context.latest_score === undefined ? "No attempt" : context.latest_score + "%"],
      ["Weekly hours", context.weekly_hours || 6],
    ];
    panel.innerHTML = rows.map(function (row) {
      return '<div class="ctx-row"><span>' + EIP.escape(row[0]) + "</span><strong>" + EIP.escape(row[1]) + "</strong></div>";
    }).join("") +
      "<div class=\"ctx-row\"><span>Top gaps</span><strong>" +
      ((context.top_gaps || []).map(function (gap) { return gap.skill; }).join(", ") || "None") + "</strong></div>" +
      "<div class=\"ctx-row\"><span>Next task</span><strong>" +
      ((context.next_tasks || [])[0] ? context.next_tasks[0].title : "None") + "</strong></div>";

    document.getElementById("mentor-context-line").textContent =
      (context.career_name || "No target career") + " · readiness " + (context.readiness || 0) + "%";
  }

  function renderSuggestions(suggestions) {
    var box = document.getElementById("mentor-suggestions");
    box.innerHTML = (suggestions || []).map(function (text) {
      return '<button class="suggestion" type="button" data-suggestion="' + EIP.escape(text) + '">' +
        EIP.escape(text) + "</button>";
    }).join(" ");
  }

  function setProvider(provider) {
    document.getElementById("mentor-provider").textContent = "Provider: " + (provider || "deterministic-fallback");
  }

  async function send(message) {
    if (busy || !message.trim()) return;
    busy = true;
    var input = document.getElementById("chat-input");
    var button = document.getElementById("chat-send");
    appendMessage({ role: "user", content: message.trim() });
    input.value = "";
    EIP.setBusy(button, true, "Thinking…");
    try {
      var result = await EIP.post("/api/mentor/chat", { message: message.trim() });
      appendMessage({ role: "assistant", content: result.reply, provider: result.provider });
      setProvider(result.provider);
      renderSuggestions(result.suggestions);
      if (result.context) renderContext(result.context);
    } catch (err) {
      appendMessage({ role: "assistant", content: "I could not answer just now: " + err.message, provider: "error" });
      EIP.toast(err.message, "error");
    } finally {
      EIP.setBusy(button, false);
      busy = false;
      input.focus();
    }
  }

  function load() {
    return EIP.get("/api/mentor/history").then(function (data) {
      var log = document.getElementById("chat-log");
      log.innerHTML = (data.messages || []).map(messageNode).join("");
      renderSuggestions(data.suggestions);
      renderContext(data.context || {});
      var lastAssistant = (data.messages || []).filter(function (m) { return m.role === "assistant"; }).pop();
      setProvider(lastAssistant ? lastAssistant.provider : "deterministic-fallback");
      scrollLog();
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    var form = document.getElementById("chat-form");
    var input = document.getElementById("chat-input");
    form.addEventListener("submit", function (event) {
      event.preventDefault();
      send(input.value);
    });
    input.addEventListener("keydown", function (event) {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        send(input.value);
      }
    });
    document.getElementById("mentor-suggestions").addEventListener("click", function (event) {
      var button = event.target.closest("[data-suggestion]");
      if (button) send(button.dataset.suggestion);
    });
    load().catch(function (err) {
      EIP.toast(err.message, "error");
    });
  });
})();

/* Shared UI helpers: toasts, formatting, modals, badges. */
window.EIP = window.EIP || {};

(function () {
  "use strict";

  EIP.escape = function (value) {
    return String(value === null || value === undefined ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  };

  EIP.fmtDate = function (value, withTime) {
    if (!value) return "—";
    var date = new Date(value);
    if (isNaN(date.getTime())) return "—";
    var opts = withTime
      ? { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" }
      : { day: "numeric", month: "short", year: "numeric" };
    return aDate(date, opts);
  };

  function aDate(date, opts) {
    try {
      return new Intl.DateTimeFormat(undefined, opts).format(date);
    } catch (e) {
      return date.toLocaleString();
    }
  }

  EIP.timeAgo = function (value) {
    if (!value) return "";
    var date = new Date(value);
    if (isNaN(date.getTime())) return "";
    var diff = Math.round((Date.now() - date.getTime()) / 1000);
    if (diff < 60) return "just now";
    if (diff < 3600) return Math.round(diff / 60) + "m ago";
    if (diff < 86400) return Math.round(diff / 3600) + "h ago";
    if (diff < 604800) return Math.round(diff / 86400) + "d ago";
    return EIP.fmtDate(value);
  };

  EIP.initials = function (name) {
    var parts = String(name || "?").trim().split(/\s+/);
    var letters = parts.slice(0, 2).map(function (p) { return p.charAt(0); }).join("");
    return (letters || "?").toUpperCase();
  };

  EIP.titleCase = function (value) {
    return String(value || "")
      .replace(/_/g, " ")
      .toLowerCase()
      .replace(/\b\w/g, function (c) { return c.toUpperCase(); });
  };

  EIP.toast = function (message, type, timeout) {
    var host = document.getElementById("toast-host");
    if (!host) {
      host = document.createElement("div");
      host.id = "toast-host";
      host.className = "toast-host";
      document.body.appendChild(host);
    }
    var node = document.createElement("div");
    node.className = "toast " + (type || "");
    node.setAttribute("role", "status");
    node.textContent = message;
    host.appendChild(node);
    setTimeout(function () {
      node.style.opacity = "0";
      node.style.transition = "opacity 0.25s ease";
      setTimeout(function () { node.remove(); }, 260);
    }, timeout || 4200);
  };

  EIP.setBusy = function (button, busy, busyText) {
    if (!button) return;
    if (busy) {
      if (!button.dataset.originalText) button.dataset.originalText = button.textContent;
      button.disabled = true;
      if (busyText) button.textContent = busyText;
    } else {
      button.disabled = false;
      if (button.dataset.originalText) button.textContent = button.dataset.originalText;
    }
  };

  EIP.loading = function (target, rows) {
    if (!target) return;
    var count = rows || 3;
    var html = "";
    for (var i = 0; i < count; i++) {
      html += '<div class="card tight muted">Loading…</div>';
    }
    target.innerHTML = html;
  };

  EIP.empty = function (title, text, actionHtml) {
    return (
      '<div class="empty"><h3>' + EIP.escape(title) + "</h3>" +
      (text ? "<p>" + EIP.escape(text) + "</p>" : "") +
      (actionHtml || "") +
      "</div>"
    );
  };

  EIP.badge = function (status, label) {
    var s = String(status || "").toUpperCase();
    var cls = "badge";
    if (/APPROVED|ACTIVE|COMPLETED|PASSED|VERIFIED|SUCCESS|READY/.test(s)) cls += " success";
    else if (/PENDING|REVIEW|SUBMITTED|DRAFT|STARTED|IN_PROGRESS|PAUSED|REQUESTED/.test(s)) cls += " warning";
    else if (/REJECT|SUSPEND|FAILED|ERROR|BLOCK|INACTIVE|EXPIRED/.test(s)) cls += " danger";
    else if (/ADMIN|SUPER/.test(s)) cls += " primary";
    else if (/RUNNING|QUEUED/.test(s)) cls += " info";
    return '<span class="' + cls + '">' + EIP.escape(label || EIP.titleCase(s)) + "</span>";
  };

  EIP.scoreClass = function (score) {
    var value = Number(score || 0);
    if (value >= 65) return "";
    if (value >= 40) return "mid";
    return "low";
  };

  EIP.percent = function (value) {
    var n = Number(value || 0);
    if (n < 0) n = 0;
    if (n > 100) n = 100;
    return Math.round(n);
  };

  EIP.debounce = function (fn, wait) {
    var timer = null;
    return function () {
      var args = arguments;
      var ctx = this;
      clearTimeout(timer);
      timer = setTimeout(function () { fn.apply(ctx, args); }, wait || 250);
    };
  };

  EIP.textToLines = function (value) {
    return String(value || "")
      .split(/[\n,;]+/)
      .map(function (s) { return s.trim(); })
      .filter(Boolean);
  };

  function makeModal(html) {
    var backdrop = document.createElement("div");
    backdrop.className = "modal-backdrop";
    backdrop.innerHTML = '<div class="modal" role="dialog" aria-modal="true">' + html + "</div>";
    document.body.appendChild(backdrop);
    var close = function () { backdrop.remove(); };
    backdrop.addEventListener("click", function (event) {
      if (event.target === backdrop) close();
    });
    document.addEventListener("keydown", function esc(event) {
      if (event.key === "Escape") { close(); document.removeEventListener("keydown", esc); }
    });
    return { element: backdrop, close: close };
  }

  EIP.confirmModal = function (options) {
    options = options || {};
    return new Promise(function (resolve) {
      var modal = makeModal(
        "<h3>" + EIP.escape(options.title || "Confirm") + "</h3>" +
        "<p>" + EIP.escape(options.message || "") + "</p>" +
        '<div class="form-actions"><button class="btn ' + (options.danger ? "btn-danger" : "btn-primary") + '" data-yes>' +
        EIP.escape(options.confirmText || "Confirm") + '</button><button class="btn btn-ghost" data-no>Cancel</button></div>'
      );
      modal.element.querySelector("[data-yes]").addEventListener("click", function () { modal.close(); resolve(true); });
      modal.element.querySelector("[data-no]").addEventListener("click", function () { modal.close(); resolve(false); });
    });
  };

  EIP.promptModal = function (options) {
    options = options || {};
    return new Promise(function (resolve) {
      var modal = makeModal(
        "<h3>" + EIP.escape(options.title || "Provide details") + "</h3>" +
        (options.message ? "<p>" + EIP.escape(options.message) + "</p>" : "") +
        '<div class="field"><label for="modal-input">' + EIP.escape(options.label || "Details") + "</label>" +
        '<textarea id="modal-input" rows="3" placeholder="' + EIP.escape(options.placeholder || "") + '"></textarea></div>' +
        '<div class="form-actions"><button class="btn btn-primary" data-yes>' +
        EIP.escape(options.confirmText || "Submit") + '</button><button class="btn btn-ghost" data-no>Cancel</button></div>'
      );
      var input = modal.element.querySelector("#modal-input");
      input.focus();
      modal.element.querySelector("[data-yes]").addEventListener("click", function () {
        var value = input.value.trim();
        if (!value) { EIP.toast("Please add a short explanation.", "warning"); return; }
        modal.close();
        resolve(value);
      });
      modal.element.querySelector("[data-no]").addEventListener("click", function () { modal.close(); resolve(null); });
    });
  };

  EIP.detailModal = function (title, html) {
    return makeModal("<h3>" + EIP.escape(title) + "</h3>" + html +
      '<div class="form-actions"><button class="btn btn-outline" data-close>Close</button></div>');
  };
})();

/* Notification inbox for all roles. */
(function () {
  "use strict";

  function render(data) {
    var unread = document.getElementById("unread-badge");
    unread.textContent = data.unread + " unread";
    unread.className = "badge " + (data.unread ? "warning" : "success");

    var list = document.getElementById("notification-list");
    if (!data.notifications.length) {
      list.innerHTML = EIP.empty("No notifications", "Approvals and readiness changes will appear here.");
      return;
    }
    list.innerHTML = data.notifications.map(function (item) {
      return (
        '<div class="next-task" style="' + (item.read ? "" : "border-left:4px solid var(--amber-strong)") + '">' +
        '<div class="task-top"><div><h4>' + EIP.escape(item.title) + "</h4>" +
        '<div class="small muted">' + EIP.escape(item.message) + "</div></div>" +
        '<span class="small muted nowrap">' + EIP.timeAgo(item.created_at) + "</span></div>" +
        '<div class="row between"><div class="row"><span class="badge">' + EIP.escape(item.type) + "</span>" +
        (item.read ? EIP.badge("READ") : '<span class="badge warning">Unread</span>') + "</div>" +
        '<div class="row">' +
        (item.link ? '<a class="small" href="' + EIP.escape(item.link) + '">Open</a>' : "") +
        (item.read ? "" : '<button class="btn btn-ghost btn-sm" data-read="' + EIP.escape(item._id) + '">Mark read</button>') +
        "</div></div></div>"
      );
    }).join("");
  }

  function load() {
    return EIP.get("/api/notifications").then(render);
  }

  document.addEventListener("DOMContentLoaded", function () {
    load().catch(function (err) { EIP.toast(err.message, "error"); });

    document.getElementById("notification-list").addEventListener("click", async function (event) {
      var button = event.target.closest("[data-read]");
      if (!button) return;
      try {
        await EIP.post("/api/notifications/read", { id: button.dataset.read });
        await load();
      } catch (err) {
        EIP.toast(err.message, "error");
      }
    });

    document.getElementById("mark-all").addEventListener("click", async function (event) {
      var button = event.currentTarget;
      EIP.setBusy(button, true, "Updating…");
      try {
        await EIP.post("/api/notifications/read", {});
        EIP.toast("All notifications marked as read.", "success");
        await load();
      } catch (err) {
        EIP.toast(err.message, "error");
      } finally {
        EIP.setBusy(button, false);
      }
    });
  });
})();

/* Authenticated shell: session banner, sidebar, logout, CSRF bootstrap. */
(function () {
  "use strict";

  document.addEventListener("DOMContentLoaded", function () {
    var sidebar = document.getElementById("sidebar");
    var toggle = document.getElementById("sidebar-toggle");
    if (toggle && sidebar) {
      toggle.addEventListener("click", function (event) {
        event.stopPropagation();
        sidebar.classList.toggle("open");
      });
      document.addEventListener("click", function (event) {
        if (!sidebar.classList.contains("open")) return;
        if (sidebar.contains(event.target)) return;
        if (event.target.closest && event.target.closest("#sidebar-toggle")) return;
        sidebar.classList.remove("open");
      });
    }

    var logout = document.getElementById("logout-btn");
    if (logout) {
      logout.addEventListener("click", async function () {
        EIP.setBusy(logout, true, "Signing out…");
        try {
          await EIP.post("/api/auth/logout", {});
        } catch (err) {
          /* session is cleared server-side even if the response is odd */
        }
        window.location.href = "/login";
      });
    }

    EIP.get("/api/auth/me")
      .then(function (data) {
        EIP.user = data.user;
        EIP.organization = data.organization;
        if (data.csrf_token) EIP.csrfToken = data.csrf_token;
        var avatar = document.getElementById("user-avatar");
        if (avatar) {
          avatar.textContent = EIP.initials(data.user.full_name);
          avatar.title = data.user.full_name;
        }
        var nameSlot = document.getElementById("user-name");
        if (nameSlot) nameSlot.textContent = data.user.full_name;
        var orgSlot = document.getElementById("user-org");
        if (orgSlot) {
          orgSlot.textContent = data.organization
            ? data.organization.name
            : EIP.titleCase(data.user.role);
        }
        return EIP.get("/api/notifications");
      })
      .then(function (data) {
        var badge = document.getElementById("notif-count");
        if (badge) {
          if (data.unread > 0) {
            badge.textContent = data.unread > 9 ? "9+" : String(data.unread);
            badge.classList.remove("hidden");
          } else {
            badge.classList.add("hidden");
          }
        }
      })
      .catch(function () {
        /* unauthenticated users are redirected by page guards */
      });
  });
})();

/* Membership approval queue for organization administrators. */
(function () {
  "use strict";

  var state = { status: "PENDING_APPROVAL", search: "" };

  function alertBox(message, type) {
    var box = document.getElementById("requests-alert");
    box.className = "alert " + (type || "warning");
    box.textContent = message;
    box.classList.remove("hidden");
  }

  function clearAlert() {
    document.getElementById("requests-alert").classList.add("hidden");
  }

  function render(data) {
    var members = data.members || [];
    document.getElementById("requests-count").textContent = members.length + " shown";
    document.getElementById("requests-title").textContent =
      EIP.titleCase(state.status.replace(/_/g, " ")) + " requests";
    var body = document.getElementById("requests-body");
    var empty = document.getElementById("requests-empty");

    if (!members.length) {
      body.innerHTML = "";
      empty.classList.remove("hidden");
      empty.innerHTML = EIP.empty("Nothing here", "No " + state.status.toLowerCase().replace(/_/g, " ") + " members found.");
      return;
    }
    empty.classList.add("hidden");
    body.innerHTML = members.map(function (member) {
      var actions = "";
      if (member.account_status === "PENDING_APPROVAL") {
        actions = '<button class="btn btn-primary btn-sm" data-approve="' + EIP.escape(member._id) + '">Approve</button>' +
          '<button class="btn btn-ghost btn-sm" data-reject="' + EIP.escape(member._id) + '" data-name="' +
          EIP.escape(member.full_name) + '">Reject</button>';
      }
      return (
        "<tr><td>" + EIP.escape(member.full_name) + "</td><td>" + EIP.escape(member.email) + "</td><td>" +
        EIP.escape(member.department_name || member.department_id || "—") + "</td><td>" +
        EIP.badge(member.account_status) + "</td><td>" + EIP.fmtDate(member.created_at) + "</td><td>" +
        '<div class="row">' + actions + "</div></td></tr>"
      );
    }).join("");
  }

  function load() {
    var query = "?status=" + encodeURIComponent(state.status) + "&q=" + encodeURIComponent(state.search);
    return EIP.get("/api/approvals/members" + query).then(render);
  }

  function wire() {
    document.querySelectorAll(".tab[data-status]").forEach(function (tab) {
      tab.addEventListener("click", function () {
        document.querySelectorAll(".tab[data-status]").forEach(function (item) { item.classList.remove("active"); });
        tab.classList.add("active");
        state.status = tab.dataset.status;
        clearAlert();
        load().catch(function (err) { alertBox(err.message, "danger"); });
      });
    });

    document.getElementById("request-search").addEventListener("input", EIP.debounce(function (event) {
      state.search = event.target.value.trim();
      load().catch(function (err) { alertBox(err.message, "danger"); });
    }, 350));

    document.getElementById("request-refresh").addEventListener("click", function () {
      clearAlert();
      load().catch(function (err) { alertBox(err.message, "danger"); });
    });

    document.getElementById("requests-body").addEventListener("click", async function (event) {
      var approve = event.target.closest("[data-approve]");
      if (approve) {
        EIP.setBusy(approve, true, "Approving…");
        try {
          await EIP.post("/api/approvals/members/" + approve.dataset.approve + "/approve", {});
          EIP.toast("Member approved.", "success");
          await load();
        } catch (err) {
          EIP.setBusy(approve, false);
          alertBox(err.message, "danger");
        }
        return;
      }
      var reject = event.target.closest("[data-reject]");
      if (reject) {
        var reason = await EIP.promptModal({
          title: "Reject request",
          label: "Reason for rejecting " + (reject.dataset.name || "this member"),
          placeholder: "Explain why this request is not approved",
          confirmText: "Reject",
        });
        if (!reason) return;
        EIP.setBusy(reject, true, "Rejecting…");
        try {
          await EIP.post("/api/approvals/members/" + reject.dataset.reject + "/reject", { reason: reason });
          EIP.toast("Request rejected.", "success");
          await load();
        } catch (err) {
          EIP.setBusy(reject, false);
          alertBox(err.message, "danger");
        }
      }
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    wire();
    load().catch(function (err) { alertBox(err.message, "danger"); });
  });
})();

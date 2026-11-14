/* Organization approval and status management. */
(function () {
  "use strict";

  var state = { status: "", search: "" };

  function alertBox(message, type) {
    var box = document.getElementById("orgs-alert");
    box.className = "alert " + (type || "warning");
    box.textContent = message;
    box.classList.remove("hidden");
  }

  function clearAlert() {
    document.getElementById("orgs-alert").classList.add("hidden");
  }

  function render(data) {
    var orgs = data.organizations || [];
    document.getElementById("orgs-count").textContent = orgs.length + " shown";
    document.getElementById("orgs-title").textContent =
      (state.status ? EIP.titleCase(state.status.replace(/_/g, " ")) + " " : "") + "organizations";
    var body = document.getElementById("orgs-body");
    var empty = document.getElementById("orgs-empty");

    if (!orgs.length) {
      body.innerHTML = "";
      empty.classList.remove("hidden");
      empty.innerHTML = EIP.empty("No organizations", "No organizations match this filter.");
      return;
    }
    empty.classList.add("hidden");
    body.innerHTML = orgs.map(function (org) {
      var actions = "";
      if (org.approval_status === "PENDING_APPROVAL") {
        actions = '<button class="btn btn-primary btn-sm" data-approve="' + EIP.escape(org._id) + '">Approve</button>' +
          '<button class="btn btn-ghost btn-sm" data-reject="' + EIP.escape(org._id) + '" data-name="' +
          EIP.escape(org.name) + '">Reject</button>';
      } else if (org.approval_status === "APPROVED") {
        actions = '<button class="btn btn-ghost btn-sm" data-status="' + EIP.escape(org._id) +
          '" data-next="SUSPENDED" data-name="' + EIP.escape(org.name) + '">Suspend</button>';
      } else if (org.approval_status === "SUSPENDED") {
        actions = '<button class="btn btn-outline btn-sm" data-status="' + EIP.escape(org._id) +
          '" data-next="APPROVED" data-name="' + EIP.escape(org.name) + '">Reactivate</button>';
      }
      var applicant = org.applicant
        ? '<div class="small muted">' + EIP.escape(org.applicant.full_name || org.applicant.email || "") + "</div>"
        : "";
      return (
        "<tr><td>" + EIP.escape(org.name) + applicant + "</td><td>" + EIP.badge(org.organization_type) +
        "</td><td>" + EIP.escape([org.city, org.state].filter(Boolean).join(", ") || "—") +
        "</td><td>" + EIP.badge(org.approval_status) + "</td><td>" + EIP.fmtDate(org.created_at) +
        '</td><td><div class="row">' + actions + "</div></td></tr>"
      );
    }).join("");
  }

  function load() {
    var query = "?status=" + encodeURIComponent(state.status) + "&q=" + encodeURIComponent(state.search);
    return EIP.get("/api/admin/organizations" + query).then(render);
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

    document.getElementById("org-search").addEventListener("input", EIP.debounce(function (event) {
      state.search = event.target.value.trim();
      load().catch(function (err) { alertBox(err.message, "danger"); });
    }, 350));

    document.getElementById("org-refresh").addEventListener("click", function () {
      clearAlert();
      load().catch(function (err) { alertBox(err.message, "danger"); });
    });

    document.getElementById("orgs-body").addEventListener("click", async function (event) {
      var approve = event.target.closest("[data-approve]");
      if (approve) {
        EIP.setBusy(approve, true, "Approving…");
        try {
          await EIP.post("/api/approvals/organizations/" + approve.dataset.approve + "/approve", {});
          EIP.toast("Organization approved.", "success");
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
          title: "Reject organization",
          label: "Reason for rejecting " + (reject.dataset.name || "this organization"),
          confirmText: "Reject",
        });
        if (!reason) return;
        EIP.setBusy(reject, true, "Rejecting…");
        try {
          await EIP.post("/api/approvals/organizations/" + reject.dataset.reject + "/reject", { reason: reason });
          EIP.toast("Organization rejected.", "success");
          await load();
        } catch (err) {
          EIP.setBusy(reject, false);
          alertBox(err.message, "danger");
        }
        return;
      }

      var statusButton = event.target.closest("[data-status]");
      if (statusButton) {
        var next = statusButton.dataset.next;
        var reasonText = "";
        if (next === "SUSPENDED") {
          reasonText = await EIP.promptModal({
            title: "Suspend organization",
            label: "Reason for suspending " + (statusButton.dataset.name || "this organization"),
            confirmText: "Suspend",
          });
          if (!reasonText) return;
        }
        EIP.setBusy(statusButton, true, "Updating…");
        try {
          await EIP.post("/api/approvals/organizations/" + statusButton.dataset.status + "/status", {
            status: next,
            reason: reasonText,
          });
          EIP.toast("Organization status updated.", "success");
          await load();
        } catch (err) {
          EIP.setBusy(statusButton, false);
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

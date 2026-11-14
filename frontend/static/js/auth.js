/* Public auth flows: login, multi-mode registration, email verification. */
(function () {
  "use strict";

  function page() {
    return document.body.dataset.page || "";
  }

  function alertBox(target, message, type) {
    if (!target) return;
    target.className = "alert " + (type || "danger");
    target.textContent = message;
    target.classList.remove("hidden");
  }

  function clearAlert(target) {
    if (target) target.classList.add("hidden");
  }

  function endpointFor(mode) {
    return {
      student: "/api/auth/register/student",
      employee: "/api/auth/register/employee",
      university: "/api/auth/register/university",
      organization: "/api/auth/register/organization",
    }[mode];
  }

  /* ---------- Login ---------- */
  function initLogin() {
    var form = document.getElementById("login-form");
    if (!form) return;
    var errorBox = document.getElementById("login-error");
    var submit = document.getElementById("login-submit");
    var nextInput = document.getElementById("next-url");
    var nextUrl = nextInput ? nextInput.value : "";
    if (nextUrl && nextUrl.charAt(0) !== "/") nextUrl = "";

    document.querySelectorAll("[data-demo-email]").forEach(function (button) {
      button.addEventListener("click", function () {
        form.email.value = button.dataset.demoEmail;
        form.password.value = "Demo@12345";
        clearAlert(errorBox);
        form.password.focus();
      });
    });

    form.addEventListener("submit", async function (event) {
      event.preventDefault();
      clearAlert(errorBox);
      EIP.setBusy(submit, true, "Signing in…");
      try {
        await EIP.post("/api/auth/login", {
          email: form.email.value.trim(),
          password: form.password.value,
        });
        EIP.toast("Signed in. Loading your workspace…", "success", 1600);
        window.location.href = nextUrl || "/app";
      } catch (err) {
        EIP.setBusy(submit, false);
        if (err.code === "EMAIL_NOT_VERIFIED") {
          alertBox(errorBox, err.message + " Open the verification link from your registration.", "warning");
        } else if (err.code === "ACCOUNT_NOT_ACTIVE") {
          alertBox(errorBox, err.message, "warning");
        } else {
          alertBox(errorBox, err.message, "danger");
        }
      }
    });
  }

  /* ---------- Registration ---------- */
  function initRegister() {
    var form = document.getElementById("register-form");
    if (!form) return;
    var mode = document.body.dataset.mode;
    var errorBox = document.getElementById("register-error");
    var submit = document.getElementById("register-submit");
    var resultCard = document.getElementById("register-result");
    var organizationInput = form.querySelector("[name='organization_id']");
    var searchInput = document.getElementById("org-search");
    var resultsBox = document.getElementById("org-results");
    var selectedLabel = document.getElementById("org-selected");
    var departmentSelect = form.querySelector("[name='department_id']");

    if (searchInput && resultsBox) {
      var orgType = mode === "employee" ? "COMPANY" : "UNIVERSITY";

      var renderResults = function (orgs) {
        if (!orgs.length) {
          resultsBox.innerHTML = '<div class="combo-meta" style="padding:0.6rem 0.7rem">No approved organizations match that search.</div>';
          resultsBox.classList.remove("hidden");
          return;
        }
        resultsBox.innerHTML = orgs
          .map(function (org) {
            var meta = [org.subtype, org.city, org.state].filter(Boolean).join(" · ");
            return (
              '<button type="button" data-org="' + EIP.escape(org._id) + '">' +
              "<strong>" + EIP.escape(org.name) + "</strong>" +
              (meta ? '<span class="combo-meta">' + EIP.escape(meta) + "</span>" : "") +
              "</button>"
            );
          })
          .join("");
        resultsBox.classList.remove("hidden");
        resultsBox.querySelectorAll("[data-org]").forEach(function (button) {
          button.addEventListener("click", function () {
            var chosen = orgs.find(function (o) { return o._id === button.dataset.org; });
            if (!chosen) return;
            organizationInput.value = chosen._id;
            searchInput.value = chosen.name;
            if (selectedLabel) {
              selectedLabel.textContent =
                "Selected: " + chosen.name + (chosen.city ? " · " + chosen.city : "");
              selectedLabel.classList.remove("hidden");
            }
            if (departmentSelect) {
              departmentSelect.innerHTML = '<option value="">Select a department</option>' +
                (chosen.departments || [])
                  .map(function (d) {
                    return '<option value="' + EIP.escape(d._id) + '">' + EIP.escape(d.name) + "</option>";
                  })
                  .join("");
              if (!chosen.departments || !chosen.departments.length) {
                departmentSelect.innerHTML = '<option value="">No departments listed</option>';
              }
            }
            resultsBox.classList.add("hidden");
          });
        });
      };

      var search = async function () {
        var query = searchInput.value.trim();
        try {
          var data = await EIP.get(
            "/api/public/organizations?type=" + orgType + "&q=" + encodeURIComponent(query) + "&limit=12"
          );
          renderResults(data.organizations || []);
        } catch (err) {
          resultsBox.innerHTML = '<div class="combo-meta" style="padding:0.6rem 0.7rem">' +
            EIP.escape(err.message) + "</div>";
          resultsBox.classList.remove("hidden");
        }
      };

      searchInput.addEventListener("focus", search);
      searchInput.addEventListener("input", EIP.debounce(function () {
        organizationInput.value = "";
        if (selectedLabel) selectedLabel.classList.add("hidden");
        if (departmentSelect) departmentSelect.innerHTML = '<option value="">Select an organization first</option>';
        search();
      }, 260));
      document.addEventListener("click", function (event) {
        if (!event.target.closest(".combo")) resultsBox.classList.add("hidden");
      });
    }

    form.addEventListener("submit", async function (event) {
      event.preventDefault();
      clearAlert(errorBox);

      if (organizationInput && !organizationInput.value) {
        alertBox(errorBox, "Search for and select your " +
          (mode === "employee" ? "organization" : "university") + ".", "warning");
        return;
      }
      if (form.password.value !== form.confirm_password.value) {
        alertBox(errorBox, "Passwords do not match.", "warning");
        return;
      }

      var payload = {};
      Array.prototype.forEach.call(form.elements, function (field) {
        if (!field.name) return;
        if (field.type === "checkbox") {
          if (field.checked) {
            payload[field.name] = (payload[field.name] || []).concat(field.value);
          }
        } else if (field.type !== "file") {
          payload[field.name] = field.value.trim ? field.value.trim() : field.value;
        }
      });
      if (Array.isArray(payload.interests)) {
        /* checkbox groups collect values; text input handled below */
      } else if (typeof payload.interests === "string") {
        payload.interests = EIP.textToLines(payload.interests);
      }

      EIP.setBusy(submit, true, "Creating account…");
      try {
        var data = await EIP.post(endpointFor(mode), payload);
        form.classList.add("hidden");
        var delivery = (data.verification && data.verification.delivery) || "";
        var devLink = data.verification && data.verification.dev_link;
        var html =
          '<div class="auth-head"><h1>Check your email</h1><p>' + EIP.escape(data.message || "Registration submitted.") + "</p></div>" +
          '<div class="alert info">' +
          "Account status: " + EIP.escape(EIP.titleCase(data.user.account_status)) + " · " +
          "Verification: " + EIP.escape(delivery || "email") +
          "</div>";
        if (devLink) {
          html += '<div class="alert warning" style="margin-top:0.7rem">' +
            "Demo environment: no email provider is configured, so use this verification link.<br>" +
            '<a href="' + EIP.escape(devLink) + '">Verify my email address</a></div>';
        }
        html += '<div class="form-actions" style="margin-top:1rem">' +
          '<a class="btn btn-primary" href="' + (devLink ? EIP.escape(devLink) : "/login") + '">' +
          (devLink ? "Verify email" : "Go to sign in") + "</a>" +
          '<a class="btn btn-outline" href="/login">Sign in</a></div>';
        resultCard.innerHTML = html;
        resultCard.classList.remove("hidden");
        window.scrollTo({ top: 0, behavior: "smooth" });
      } catch (err) {
        EIP.setBusy(submit, false);
        alertBox(errorBox, err.message, "danger");
      }
    });
  }

  /* ---------- Verify email ---------- */
  function initVerify() {
    var status = document.getElementById("verify-status");
    if (!status) return;
    var token = document.body.dataset.token || "";
    if (!token) {
      status.className = "alert warning";
      status.innerHTML = "This verification link is missing its token. " +
        '<a href="/login">Sign in</a> or register again to receive a fresh link.';
      return;
    }

    (async function () {
      try {
        await EIP.post("/api/auth/verify-email", { token: token });
        status.className = "alert success";
        status.innerHTML = "Email verified. Your registration is now waiting for administrator approval. " +
          '<a href="/login">Sign in to check status</a>.';
        EIP.toast("Email verified.", "success");
      } catch (err) {
        status.className = "alert danger";
        status.innerHTML = EIP.escape(err.message) + ' <a href="/login">Back to sign in</a>';
      }
    })();
  }

  document.addEventListener("DOMContentLoaded", function () {
    var name = page();
    if (name === "login") initLogin();
    if (name === "register") initRegister();
    if (name === "verify") initVerify();
  });
})();

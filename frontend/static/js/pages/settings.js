/* Platform settings: provider routing and catalog administration. */
(function () {
  "use strict";

  var providersLoaded = false;

  function alertBox(message, type) {
    var box = document.getElementById("settings-alert");
    box.className = "alert " + (type || "warning");
    box.textContent = message;
    box.classList.remove("hidden");
  }

  function clearAlert() {
    document.getElementById("settings-alert").classList.add("hidden");
  }

  function providerBadge(provider) {
    if (provider.configured) return EIP.badge("CONFIGURED");
    return EIP.badge("NOT_CONFIGURED");
  }

  function renderProviderStatus(providers) {
    document.getElementById("provider-status").innerHTML = providers.length
      ? providers.map(function (provider) {
          return (
            '<div class="attempt-row"><div><strong>' + EIP.escape(provider.label || provider.name) + "</strong>" +
            '<div class="small muted">' + EIP.escape(provider.model || "No model") +
            (provider.position ? " · position " + provider.position : " · not routed") +
            (provider.last_error ? " · " + EIP.escape(provider.last_error) : "") + "</div></div>" +
            providerBadge(provider) + "</div>"
          );
        }).join("")
      : '<p class="small muted">No providers available.</p>';
  }

  function fillProviderSelect(providers, settings) {
    var select = document.getElementById("primary-provider");
    select.innerHTML = '<option value="">Automatic</option>' + providers.map(function (provider) {
      return '<option value="' + EIP.escape(provider.name) + '">' + EIP.escape(provider.label || provider.name) + "</option>";
    }).join("");
    select.value = (settings && settings.primary_provider) || "";
  }

  function loadProviders() {
    return EIP.get("/api/admin/providers").then(function (data) {
      renderProviderStatus(data.providers || []);
      if (!providersLoaded) {
        fillProviderSelect(data.providers || [], data.settings || {});
        document.getElementById("fallback-order").value = (data.settings && data.settings.fallback_order) || "";
        providersLoaded = true;
      }
      return data;
    });
  }

  function loadCatalog() {
    return EIP.get("/api/admin/catalog").then(function (data) {
      var counts = data.counts || {};
      document.getElementById("count-skills").textContent = counts.skills || 0;
      document.getElementById("count-careers").textContent = counts.careers || 0;
      document.getElementById("count-resources").textContent = counts.resources || 0;
      document.getElementById("count-questions").textContent = counts.questions || 0;
    });
  }

  function load() {
    return Promise.all([
      loadProviders(),
      loadCatalog(),
      EIP.get("/api/admin/overview").then(function (data) {
        document.getElementById("settings-dbmode").textContent =
          "Database — " + EIP.titleCase(data.database_mode || "memory");
      }),
    ]);
  }

  function value(id) {
    var element = document.getElementById(id);
    return element ? element.value.trim() : "";
  }

  function splitList(raw) {
    return String(raw || "").split(/[\n,;]+/).map(function (item) { return item.trim(); }).filter(Boolean);
  }

  function submitCatalogForm(formId, handler) {
    document.getElementById(formId).addEventListener("submit", async function (event) {
      event.preventDefault();
      var button = event.target.querySelector("button[type='submit']");
      EIP.setBusy(button, true, "Saving…");
      try {
        await handler();
        clearAlert();
        EIP.toast("Catalog updated.", "success");
        event.target.reset();
        await loadCatalog();
      } catch (err) {
        alertBox(err.message, "danger");
      } finally {
        EIP.setBusy(button, false);
      }
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    load().catch(function (err) { alertBox(err.message, "danger"); });

    document.getElementById("provider-form").addEventListener("submit", async function (event) {
      event.preventDefault();
      var button = document.getElementById("provider-save");
      EIP.setBusy(button, true, "Saving…");
      try {
        var result = await EIP.put("/api/admin/providers", {
          primary_provider: value("primary-provider"),
          fallback_order: value("fallback-order"),
        });
        providersLoaded = false;
        renderProviderStatus(result.providers || []);
        await loadProviders();
        clearAlert();
        EIP.toast("Provider routing updated.", "success");
      } catch (err) {
        alertBox(err.message, "danger");
      } finally {
        EIP.setBusy(button, false);
      }
    });

    submitCatalogForm("skill-catalog-form", function () {
      return EIP.post("/api/admin/catalog/skills", {
        name: value("cat-skill-name"),
        category: value("cat-skill-category"),
        description: value("cat-skill-desc"),
      });
    });

    submitCatalogForm("resource-form", function () {
      return EIP.post("/api/admin/catalog/resources", {
        title: value("res-title"),
        url: value("res-url"),
        provider: value("res-provider"),
        resource_type: value("res-type"),
        skill_names: splitList(value("res-skills")),
        difficulty: value("res-difficulty"),
        duration_hours: Number(value("res-hours") || 4),
        description: value("res-desc"),
      });
    });

    submitCatalogForm("career-form", function () {
      return EIP.post("/api/admin/catalog/careers", {
        name: value("car-name"),
        experience_level: value("car-level"),
        required_skills: splitList(value("car-required")),
        preferred_skills: splitList(value("car-preferred")),
        description: value("car-desc"),
        project_expectations: value("car-expectations"),
      });
    });

    submitCatalogForm("question-form", function () {
      var correctKeywords = splitList(value("q-keywords"));
      return EIP.post("/api/admin/catalog/questions", {
        skill_name: value("q-skill"),
        question_type: value("q-type"),
        difficulty: value("q-difficulty"),
        points: Number(value("q-points") || 1),
        prompt: value("q-prompt"),
        options: value("q-options"),
        correct_option: value("q-correct"),
        correct_keywords: correctKeywords,
        explanation: value("q-explanation"),
      });
    });
  });
})();

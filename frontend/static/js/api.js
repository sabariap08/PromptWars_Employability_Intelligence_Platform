/* EIP API client: JSON envelope handling, CSRF header, auth redirects. */
window.EIP = window.EIP || {};

(function () {
  "use strict";

  var meta = document.querySelector('meta[name="csrf-token"]');
  EIP.csrfToken = meta ? meta.getAttribute("content") : "";

  EIP.refreshCsrf = async function () {
    try {
      var res = await fetch("/api/auth/csrf", {
        credentials: "same-origin",
        headers: { Accept: "application/json" },
      });
      var payload = await res.json();
      if (payload && payload.data && payload.data.csrf_token) {
        EIP.csrfToken = payload.data.csrf_token;
      }
    } catch (err) {
      /* keep the meta token */
    }
    return EIP.csrfToken;
  };

  EIP.request = async function (path, opts) {
    opts = opts || {};
    var method = (opts.method || "GET").toUpperCase();
    var headers = Object.assign({ Accept: "application/json" }, opts.headers || {});
    var body = opts.body;

    if (opts.json !== undefined) {
      body = JSON.stringify(opts.json);
      headers["Content-Type"] = "application/json";
    }
    if (method !== "GET" && method !== "HEAD") {
      if (!EIP.csrfToken) await EIP.refreshCsrf();
      headers["X-CSRF-Token"] = EIP.csrfToken;
    }

    var res;
    try {
      res = await fetch(path, {
        method: method,
        headers: headers,
        body: body,
        credentials: "same-origin",
      });
    } catch (networkError) {
      var offline = new Error("Cannot reach the server. Check your connection and try again.");
      offline.status = 0;
      throw offline;
    }

    var payload = null;
    try {
      payload = await res.json();
    } catch (err) {
      payload = null;
    }

    if (res.status === 401) {
      if (window.location.pathname.indexOf("/app") === 0) {
        var next = encodeURIComponent(window.location.pathname + window.location.search);
        window.location.href = "/login?next=" + next;
      }
    }

    if (!res.ok || !payload || payload.success === false) {
      var error = new Error((payload && payload.message) || "Request failed (" + res.status + ").");
      error.status = res.status;
      error.code = payload && payload.error_code;
      error.details = payload && payload.details;
      throw error;
    }
    return payload.data;
  };

  EIP.get = function (path) {
    return EIP.request(path);
  };
  EIP.post = function (path, json) {
    return EIP.request(path, { method: "POST", json: json });
  };
  EIP.put = function (path, json) {
    return EIP.request(path, { method: "PUT", json: json });
  };
  EIP.del = function (path) {
    return EIP.request(path, { method: "DELETE" });
  };
  EIP.upload = function (path, formData) {
    return EIP.request(path, { method: "POST", body: formData });
  };
})();

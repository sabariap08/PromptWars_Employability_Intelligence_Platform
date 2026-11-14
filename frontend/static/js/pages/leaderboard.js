/* Organization leaderboard. */
(function () {
  "use strict";

  function alertBox(message) {
    var box = document.getElementById("leaderboard-alert");
    box.textContent = message;
    box.classList.remove("hidden");
  }

  function render(data) {
    var rows = data.leaderboard || [];
    var me = data.me;
    document.getElementById("lb-scope").textContent =
      data.scope === "platform" ? "Platform" : "Organization";
    document.getElementById("lb-total").textContent = (data.total || 0) + " learners ranked";
    document.getElementById("lb-count").textContent = rows.length + " shown";
    if (me) {
      document.getElementById("lb-rank").textContent = "#" + me.rank;
      document.getElementById("lb-points").textContent = me.points;
      document.getElementById("lb-readiness").textContent = me.readiness + "%";
      document.getElementById("lb-courses").textContent = me.courses_completed + " courses completed";
    } else {
      document.getElementById("lb-rank").textContent = "—";
      document.getElementById("lb-points").textContent = "—";
      document.getElementById("lb-readiness").textContent = "—";
      document.getElementById("lb-courses").textContent = "Complete evidence to enter the ranking";
    }

    var body = document.getElementById("leaderboard-body");
    var empty = document.getElementById("leaderboard-empty");
    if (!rows.length) {
      body.innerHTML = "";
      empty.classList.remove("hidden");
      empty.innerHTML = EIP.empty(
        "No ranked learners yet",
        "Learners appear after their profile is approved and they add skills or take assessments."
      );
      return;
    }
    empty.classList.add("hidden");
    body.innerHTML = rows.map(function (row) {
      var highlight = me && row.user_id === me.user_id;
      return (
        "<tr" + (highlight ? ' style="background:#f0fdfa;font-weight:600"' : "") + ">" +
        "<td>" + row.rank + "</td>" +
        "<td>" + EIP.escape(row.full_name) + (highlight ? " (you)" : "") + "</td>" +
        "<td>" + EIP.escape(row.department || "—") + "</td>" +
        "<td>" + row.readiness + "%</td>" +
        "<td>" + row.skills_verified + "</td>" +
        "<td>" + row.courses_completed + "</td>" +
        "<td><strong>" + row.points + "</strong></td>" +
        "</tr>"
      );
    }).join("");
  }

  document.addEventListener("DOMContentLoaded", function () {
    EIP.get("/api/learning/leaderboard?limit=25")
      .then(render)
      .catch(function (err) { alertBox(err.message); });
  });
})();

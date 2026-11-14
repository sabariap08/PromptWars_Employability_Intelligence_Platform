/* Explainable readiness breakdown. */
(function () {
  "use strict";

  function render(data) {
    var empty = document.getElementById("readiness-empty");
    var content = document.getElementById("readiness-content");
    if (!data.has_target) {
      content.classList.add("hidden");
      empty.classList.remove("hidden");
      empty.innerHTML = EIP.empty(
        "No target career yet",
        "Choose a career goal to compare your evidence against real role requirements.",
        '<a class="btn btn-primary" href="/app/profile">Set target career</a>'
      );
      return;
    }
    empty.classList.add("hidden");
    content.classList.remove("hidden");

    document.getElementById("readiness-career").textContent = data.career_name;
    document.getElementById("readiness-badge").textContent = data.required_count + " required skills";
    document.getElementById("readiness-score").textContent = data.readiness + "%";
    document.getElementById("readiness-strong").textContent =
      data.strong_count + " of " + data.required_count + " requirements met";
    document.getElementById("readiness-bar").style.width = EIP.percent(data.readiness) + "%";
    document.getElementById("gaps-count").textContent = data.gaps.length + " gaps";

    document.getElementById("readiness-strengths").innerHTML = data.strengths.length
      ? data.strengths.map(function (row) {
          return (
            '<div class="skill-line"><div class="skill-top"><strong>' + EIP.escape(row.skill_name) + "</strong>" +
            "<span>" + row.current + "% / " + row.required + "% " +
            (row.verified ? '<span class="badge success">Verified</span>' : "") + "</span></div>" +
            '<div class="progress"><span style="width:' + EIP.percent(row.current) + '%"></span></div></div>'
          );
        }).join("")
      : '<p class="small muted">No strengths yet. Your strongest current skills will show here.</p>';

    document.getElementById("readiness-gaps").innerHTML = data.gaps.length
      ? data.gaps.map(function (row) {
          return (
            '<div class="skill-line"><div class="skill-top"><strong>' + EIP.escape(row.skill_name) + "</strong>" +
            "<span>" + row.current + "% / " + row.required + "%</span></div>" +
            '<div class="progress amber"><span style="width:' + EIP.percent(row.attainment) + '%"></span></div>' +
            '<div class="small muted">' + EIP.escape(EIP.titleCase(row.status)) +
            " · weight " + row.weight + "</div></div>"
          );
        }).join("")
      : '<p class="small muted">No gaps against this role. Verify more skills to keep the score current.</p>';

    document.getElementById("readiness-skills").innerHTML = data.skills.map(function (row) {
      return (
        "<tr><td>" + EIP.escape(row.skill_name) + (row.verified ? ' <span class="badge success">Verified</span>' : "") +
        "</td><td>" + row.current + "%</td><td>" + row.required + "%</td><td>" + row.attainment + "%</td>" +
        "<td>" + EIP.badge(row.status, EIP.titleCase(row.status)) + "</td></tr>"
      );
    }).join("");

    var preferred = data.preferred_skills || [];
    document.getElementById("preferred-skills").innerHTML = preferred.length
      ? "Preferred skills: " + preferred.map(function (item) {
          return '<span class="badge">' + EIP.escape(item.skill_name || item) + "</span>";
        }).join(" ")
      : "";
  }

  document.addEventListener("DOMContentLoaded", function () {
    EIP.get("/api/learner/readiness")
      .then(render)
      .catch(function (err) {
        var empty = document.getElementById("readiness-empty");
        empty.classList.remove("hidden");
        empty.innerHTML = '<div class="alert danger">' + EIP.escape(err.message) + "</div>";
      });
  });
})();

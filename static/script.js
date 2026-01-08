const form = document.getElementById("form");
const output = document.getElementById("output");
const loader = document.getElementById("loader");
const rankTable = document.getElementById("rankTable");

form.addEventListener("submit", async (e) => {
  e.preventDefault();

  const fileInput = document.querySelector('input[type="file"]');
  const files = fileInput.files;

  loader.classList.remove("hidden");
  output.classList.add("hidden");
  if (rankTable) rankTable.innerHTML = "";

  try {
    // ---------- MULTIPLE RESUMES ----------
    if (files.length > 1) {
      const fd = new FormData();

      for (let f of files) fd.append("resumes", f);

      fd.append("skills", form.skills.value);
      fd.append("experience", form.experience.value);

      const res = await fetch("/rank", {
        method: "POST",
        body: fd
      });

      const data = await res.json();
      loader.classList.add("hidden");

      let html = `
        <tr>
          <th>Rank</th>
          <th>Resume</th>
          <th>Domain</th>
          <th>Score</th>
          <th>Decision</th>
        </tr>
      `;

      data.forEach(r => {
        html += `
          <tr>
            <td>${r.rank}</td>
            <td>${r.resume}</td>
            <td>${r.domain.toUpperCase()}</td>
            <td>${r.score}%</td>
            <td>${r.decision}</td>
          </tr>
        `;
      });

      rankTable.innerHTML = html;
      return;
    }

    // ---------- SINGLE RESUME ----------
    const fd = new FormData(form);

    const res = await fetch("/analyze", {
      method: "POST",
      body: fd
    });

    const data = await res.json();
    loader.classList.add("hidden");

    document.getElementById("decision").innerText =
      "Decision: " + data.decision;

    document.getElementById("score").innerText =
      data.score + "%";

    document.getElementById("matched").innerText =
      data.matchedSkills.length ? data.matchedSkills.join(", ") : "None";

    document.getElementById("l3").innerText =
      data.detectedSkills.length ? data.detectedSkills.join(", ") : "None";

    const badge = document.getElementById("domainBadge");
    if (badge) {
      badge.innerText = data.domain.replace("_", " ").toUpperCase();
      badge.className = "domain-badge " + data.domain;
      badge.classList.remove("hidden");
    }

    output.classList.remove("hidden");

  } catch (err) {
    loader.classList.add("hidden");
    alert("Error analyzing resume. Check server logs.");
    console.error(err);
  }
});

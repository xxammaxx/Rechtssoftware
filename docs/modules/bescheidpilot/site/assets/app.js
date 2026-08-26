(() => {
  "use strict";

  const statusLabels = {
    planned: "Geplant",
    "in-progress": "In Arbeit",
    documented: "Dokumentiert",
    partial: "Teilweise belegt",
    complete: "Belegt",
    missing: "Fehlt",
    "not-yet-proven": "Noch nicht bewiesen",
    "demo-ready": "Demo-bereit",
    validated: "Validiert",
    "pilot-ready": "Pilot-bereit",
    deferred: "Zurückgestellt"
  };

  const currentPage = document.body.dataset.page;
  document.querySelectorAll("[data-nav]").forEach((link) => {
    if (link.dataset.nav === currentPage) {
      link.setAttribute("aria-current", "page");
    }
  });

  document.querySelectorAll("[data-year]").forEach((node) => {
    node.textContent = new Date().getFullYear().toString();
  });

  const loadJson = async (path) => {
    const response = await fetch(path, { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`Could not load ${path}: ${response.status}`);
    }
    return response.json();
  };

  const text = (tag, value, className) => {
    const node = document.createElement(tag);
    node.textContent = value;
    if (className) {
      node.className = className;
    }
    return node;
  };

  const renderRoadmap = async () => {
    const root = document.querySelector("[data-roadmap]");
    if (!root) return;

    try {
      const roadmap = await loadJson("data/roadmap.json");
      root.replaceChildren();
      roadmap.forEach((item) => {
        const card = document.createElement("article");
        card.className = "data-card";
        card.dataset.status = item.status;
        card.append(
          text("p", statusLabels[item.status] || item.status, "meta"),
          text("h3", item.milestone),
          text("p", item.summary)
        );
        const evidence = text("p", `Evidence: ${item.evidence}`, "fine-print");
        card.append(evidence);
        root.append(card);
      });
    } catch (error) {
      root.dataset.loadError = "true";
      console.warn(error.message);
    }
  };

  const renderEvidence = async () => {
    const root = document.querySelector("[data-evidence]");
    if (!root) return;

    try {
      const evidence = await loadJson("data/evidence.json");
      root.replaceChildren();
      evidence.forEach((item) => {
        const row = document.createElement("tr");
        const claim = text("td", item.claim);
        claim.dataset.label = "Aussage";
        const state = text("td", statusLabels[item.status] || item.status);
        state.dataset.label = "Status";
        const source = text("td", item.evidence);
        source.dataset.label = "Evidence";
        const limitation = text("td", item.limitation);
        limitation.dataset.label = "Offene Grenze";
        row.append(claim, state, source, limitation);
        root.append(row);
      });
    } catch (error) {
      root.dataset.loadError = "true";
      console.warn(error.message);
    }
  };

  const renderFeatures = async () => {
    const root = document.querySelector("[data-features]");
    if (!root) return;

    try {
      const features = await loadJson("data/features.json");
      root.replaceChildren();
      features.forEach((item) => {
        const card = document.createElement("article");
        card.className = "data-card";
        card.dataset.status = item.status;
        card.append(
          text("p", statusLabels[item.status] || item.status, "meta"),
          text("h3", item.feature),
          text("p", item.description),
          text("p", `Evidence: ${item.evidence}`, "fine-print")
        );
        root.append(card);
      });
    } catch (error) {
      root.dataset.loadError = "true";
      console.warn(error.message);
    }
  };

  const renderStatus = async () => {
    const root = document.querySelector("[data-status]");
    if (!root) return;

    try {
      const data = await loadJson("data/project-status.json");
      root.replaceChildren();
      const fields = [
        ["Projekt", data.project],
        ["Gesamtstatus", data.status],
        ["MVP-Phase", data.mvpPhase],
        ["Local-only", data.localOnlyStatus],
        ["Upload-Risiko", data.uploadRisk],
        ["Remote-LLM-Risiko", data.remoteLlmRisk],
        ["Demo", data.demoStatus],
        ["Evidence", data.evidenceStatus],
        ["Build / Deploy", data.deployStatus],
        ["Nächster Milestone", data.nextMilestone],
        ["Letzte Aktualisierung", data.lastUpdated]
      ];

      const list = document.createElement("dl");
      fields.forEach(([label, value]) => {
        const row = document.createElement("div");
        row.className = "status-row";
        row.append(text("dt", label), text("dd", value));
        list.append(row);
      });
      root.append(list);

      const blockerHeading = text("h3", "Offene Blocker");
      blockerHeading.style.marginTop = "2rem";
      const blockers = document.createElement("ul");
      blockers.className = "plain-list";
      data.openBlockers.forEach((blocker) => blockers.append(text("li", blocker)));
      root.append(blockerHeading, blockers);
    } catch (error) {
      root.dataset.loadError = "true";
      console.warn(error.message);
    }
  };

  renderRoadmap();
  renderEvidence();
  renderFeatures();
  renderStatus();
})();

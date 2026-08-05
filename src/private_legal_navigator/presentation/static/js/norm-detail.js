"use strict";

const linkForm = document.getElementById("link-form");
const caseSelect = document.getElementById("case-select");

if (linkForm instanceof HTMLFormElement && caseSelect instanceof HTMLSelectElement) {
    caseSelect.addEventListener("change", () => {
        const caseId = caseSelect.value;
        linkForm.action = caseId
            ? `/ui/cases/${encodeURIComponent(caseId)}/legal-situation/link`
            : "";
    });
}

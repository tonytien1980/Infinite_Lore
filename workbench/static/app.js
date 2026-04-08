const state = {
  page: "home",
  dashboard: null,
  bundles: [],
  knowledge: { synthesis: [], small_notes: [] },
  health: null,
  settings: null,
};

const pages = [...document.querySelectorAll(".page")];
const navLinks = [...document.querySelectorAll(".nav-link")];
const pageTitle = document.getElementById("pageTitle");
const healthPill = document.getElementById("healthPill");
const vaultPath = document.getElementById("vaultPath");
const systemVaultPath = document.getElementById("systemVaultPath");

function setPage(page) {
  state.page = page;
  pages.forEach((element) => element.classList.toggle("active", element.dataset.page === page));
  navLinks.forEach((element) => element.classList.toggle("active", element.dataset.page === page));
  pageTitle.textContent = page.charAt(0).toUpperCase() + page.slice(1);
}

function createListItem(title, meta, detail) {
  const item = document.createElement("article");
  item.className = "list-item";
  item.innerHTML = `
    <p class="eyebrow">${meta}</p>
    <strong>${title}</strong>
    <p>${detail}</p>
  `;
  return item;
}

function renderDashboard() {
  const imports = document.getElementById("recentImports");
  const knowledge = document.getElementById("recentKnowledge");
  const cards = document.getElementById("snapshotCards");

  imports.innerHTML = "";
  (state.dashboard?.recent_imports || []).forEach((item) => {
    imports.appendChild(
      createListItem(
        item.title,
        item.primary_domain || "unclassified",
        `${item.bundle_path} • ${item.conversion_status || "unknown"}`
      )
    );
  });
  if (!imports.children.length) imports.textContent = "No imports yet.";

  knowledge.innerHTML = "";
  (state.dashboard?.recent_synthesis || []).forEach((item) => {
    knowledge.appendChild(createListItem(item.title, item.primary_domain || "wiki", item.path));
  });
  if (!knowledge.children.length) knowledge.textContent = "No compiled knowledge yet.";

  cards.innerHTML = "";
  const snapshotEntries = [
    ["Bundles", state.dashboard?.bundle_count ?? 0, "Raw intake units"],
    ["Knowledge", state.dashboard?.knowledge_count ?? 0, "Compiled notes"],
    ["Warnings", state.dashboard?.warning_count ?? 0, "Needs attention"],
  ];
  snapshotEntries.forEach(([label, value, detail]) => {
    const card = document.createElement("article");
    card.className = "snapshot-card";
    card.innerHTML = `<p class="eyebrow">${label}</p><strong>${value}</strong><p>${detail}</p>`;
    cards.appendChild(card);
  });
}

function renderBundles() {
  const container = document.getElementById("bundleList");
  container.innerHTML = "";
  state.bundles.forEach((bundle) => {
    const review = bundle.review_required === "true" ? "Needs review" : "Ready";
    container.appendChild(
      createListItem(bundle.title, bundle.primary_domain || "unclassified", `${bundle.bundle_path} • ${review}`)
    );
  });
  if (!container.children.length) container.textContent = "No raw bundles found.";
}

function renderKnowledge() {
  const synthesis = document.getElementById("synthesisList");
  const small = document.getElementById("smallNotesList");
  synthesis.innerHTML = "";
  small.innerHTML = "";

  state.knowledge.synthesis.forEach((note) => {
    synthesis.appendChild(createListItem(note.title, note.primary_domain || "wiki", note.path));
  });
  if (!synthesis.children.length) synthesis.textContent = "No synthesis notes yet.";

  state.knowledge.small_notes.forEach((note) => {
    small.appendChild(createListItem(note.title, `${note.note_type} • ${note.primary_domain || "wiki"}`, note.path));
  });
  if (!small.children.length) small.textContent = "No smaller notes yet.";
}

function renderHealth() {
  const target = document.getElementById("healthDetails");
  target.innerHTML = "";
  const health = state.health;
  if (!health) {
    target.textContent = "Loading health status…";
    return;
  }
  healthPill.textContent = health.status === "ok" ? "Healthy" : "Needs review";
  target.textContent = health.status === "ok" ? "Vault health check passed." : health.errors.join("\n");
}

function populateSettings() {
  const settings = state.settings || {};
  const provider = settings.providers?.[0] || { provider: "openai", id: "openai-main", api_key: "", models: [] };
  document.getElementById("providerName").value = provider.provider || "openai";
  document.getElementById("providerId").value = provider.id || "openai-main";
  document.getElementById("providerApiKey").value = provider.api_key || "";
  document.getElementById("balancedModel").value =
    provider.models?.find((model) => model.role === "balanced")?.id || "";
  document.getElementById("bestModel").value =
    provider.models?.find((model) => model.role === "best_deep")?.id || "";

  const routes = settings.routes || {};
  document.getElementById("routeScan").value = routes.scan || "no_model";
  document.getElementById("routeImport").value = routes.import || "no_model";
  document.getElementById("routeCompile").value = routes.compile || "balanced";
  document.getElementById("routeAsk").value = routes.ask || "best_deep";
  document.getElementById("routeReflection").value = routes.reflection || "balanced";
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
  return response.json();
}

async function loadAll() {
  state.dashboard = await fetchJson("/api/dashboard");
  state.bundles = await fetchJson("/api/bundles");
  state.knowledge = await fetchJson("/api/knowledge");
  state.health = await fetchJson("/api/system/health");
  const systemInfo = await fetchJson("/api/system/info");
  state.settings = await fetchJson("/api/settings");
  vaultPath.textContent = systemInfo.vault_root;
  systemVaultPath.textContent = systemInfo.vault_root;
  renderDashboard();
  renderBundles();
  renderKnowledge();
  renderHealth();
  populateSettings();
}

navLinks.forEach((button) => {
  button.addEventListener("click", () => setPage(button.dataset.page));
});

document.getElementById("homeAskForm").addEventListener("submit", (event) => {
  event.preventDefault();
  document.getElementById("askInput").value = document.getElementById("homeAskInput").value;
  setPage("ask");
});

document.getElementById("askForm").addEventListener("submit", (event) => {
  event.preventDefault();
  document.getElementById("askAnswer").textContent =
    "Grounded Ask backend is the next phase. This shell is ready to show structured answers, grounding, and source trace.";
});

document.getElementById("fileImportForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  await fetchJson("/api/inbox/import-file", { method: "POST", body: form });
  await loadAll();
  setPage("knowledge");
});

document.getElementById("urlImportForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  await fetchJson("/api/inbox/import-url", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      url: form.get("url"),
      primary_domain: form.get("primary_domain"),
    }),
  });
  await loadAll();
  setPage("inbox");
});

document.getElementById("refreshBundlesButton").addEventListener("click", loadAll);
document.getElementById("scanNowButton").addEventListener("click", loadAll);

document.getElementById("settingsForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const payload = {
    providers: [
      {
        id: document.getElementById("providerId").value,
        provider: document.getElementById("providerName").value,
        api_key: document.getElementById("providerApiKey").value,
        models: [
          { id: document.getElementById("balancedModel").value, role: "balanced" },
          { id: document.getElementById("bestModel").value, role: "best_deep" },
        ].filter((model) => model.id),
      },
    ],
    routes: {
      scan: document.getElementById("routeScan").value,
      import: document.getElementById("routeImport").value,
      compile: document.getElementById("routeCompile").value,
      ask: document.getElementById("routeAsk").value,
      reflection: document.getElementById("routeReflection").value,
    },
  };
  state.settings = await fetchJson("/api/settings", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  document.getElementById("settingsStatus").textContent = "Local settings saved.";
});

loadAll().catch((error) => {
  healthPill.textContent = "Load failed";
  document.getElementById("healthDetails").textContent = error.message;
});

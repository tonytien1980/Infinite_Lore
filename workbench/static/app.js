const state = {
  page: "home",
  dashboard: null,
  bundles: [],
  knowledge: { synthesis: [], small_notes: [] },
  health: null,
  settings: null,
  ask: {
    question: "",
    mode: "auto",
    answer: "",
    grounding: [],
    trace: [],
    limits: [],
    reflections: [],
    reflectionsExpanded: false,
    draft: null,
    requestSeq: 0,
    feedbackSeq: 0,
    askBusy: false,
    feedbackBusy: false,
  },
};

const pages = [...document.querySelectorAll(".page")];
const navLinks = [...document.querySelectorAll(".nav-link")];
const pageTitle = document.getElementById("pageTitle");
const healthPill = document.getElementById("healthPill");
const vaultPath = document.getElementById("vaultPath");
const systemVaultPath = document.getElementById("systemVaultPath");
const askAnswer = document.getElementById("askAnswer");
const askGrounding = document.getElementById("askGrounding");
const askTrace = document.getElementById("askTrace");
const askLimits = document.getElementById("askLimits");
const reflectionList = document.getElementById("reflectionList");
const reflectionViewAllButton = document.getElementById("reflectionViewAllButton");
const feedbackInput = document.getElementById("feedbackInput");
const feedbackHint = document.getElementById("feedbackHint");
const feedbackEditorTitle = document.getElementById("feedbackEditorTitle");
const feedbackEditorStatus = document.getElementById("feedbackEditorStatus");
const feedbackEditorEmpty = document.getElementById("feedbackEditorEmpty");
const feedbackEditorBody = document.getElementById("feedbackEditorBody");
const feedbackEditorMeta = document.getElementById("feedbackEditorMeta");
const feedbackEditorTextarea = document.getElementById("feedbackEditorTextarea");
const feedbackConfirmButton = document.getElementById("feedbackConfirmButton");
const feedbackDiscardButton = document.getElementById("feedbackDiscardButton");
const draftCorrectionButton = document.getElementById("draftCorrectionButton");
const draftReflectionButton = document.getElementById("draftReflectionButton");
const askSubmitButton = document.getElementById("askSubmitButton");

function setPage(page) {
  state.page = page;
  pages.forEach((element) => element.classList.toggle("active", element.dataset.page === page));
  navLinks.forEach((element) => element.classList.toggle("active", element.dataset.page === page));
  pageTitle.textContent = page.charAt(0).toUpperCase() + page.slice(1);
}

function createListItem(title, meta, detail) {
  const item = document.createElement("article");
  item.className = "list-item";
  const metaLine = document.createElement("p");
  metaLine.className = "eyebrow";
  metaLine.textContent = meta || "";
  const heading = document.createElement("strong");
  heading.textContent = title || "";
  const body = document.createElement("p");
  body.textContent = detail || "";
  item.append(metaLine, heading, body);
  return item;
}

function renderListStack(container, items, emptyMessage, mapItem) {
  container.innerHTML = "";
  items.forEach((item) => {
    container.appendChild(mapItem(item));
  });
  if (!container.children.length) {
    container.textContent = emptyMessage;
  }
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
  document.getElementById("routeQuery").value = routes.query || "no_model";
  document.getElementById("routeAsk").value = routes.ask || "best_deep";
  document.getElementById("routeReflection").value = routes.reflection || "balanced";
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try {
      const payload = await response.json();
      if (payload && typeof payload.detail === "string" && payload.detail.trim()) {
        detail = payload.detail;
      }
    } catch (error) {
      // Keep the default HTTP status text when there is no JSON body.
    }
    throw new Error(detail);
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
  document.getElementById("askMode").value = "auto";
  setPage("ask");
  runAsk(document.getElementById("askInput").value, "auto");
});

function clearDraftEditor(message = "No draft loaded yet.") {
  state.ask.draft = null;
  feedbackEditorTitle.textContent = "Draft review";
  feedbackEditorStatus.textContent = message;
  feedbackEditorEmpty.hidden = false;
  feedbackEditorBody.hidden = true;
  feedbackEditorMeta.innerHTML = "";
  feedbackEditorTextarea.value = "";
  feedbackEditorTextarea.dataset.draftId = "";
  feedbackConfirmButton.textContent = "Confirm";
  feedbackConfirmButton.disabled = true;
  feedbackDiscardButton.disabled = true;
}

function renderAskAnswer() {
  askAnswer.textContent = state.ask.answer || "Ask the library and the grounded answer will appear here.";

  renderListStack(
    askGrounding,
    state.ask.grounding,
    "Grounding will appear here.",
    (item) => createListItem(item.title || item.path || "Grounding note", item.note_type || item.primary_domain || "wiki", item.path || item.ref || "")
  );

  renderListStack(
    askTrace,
    state.ask.trace,
    "Source trace will appear here.",
    (item) => createListItem(item.source_ref || item.path || "Source", "source", item.from_note || item.title || "")
  );

  renderListStack(
    askLimits,
    state.ask.limits,
    "Limits and uncertainty will appear here when needed.",
    (item) => createListItem(item, "limit", "Evidence boundary")
  );
}

function renderReflections() {
  const reflections = state.ask.reflections || [];
  const visibleReflections = state.ask.reflectionsExpanded ? reflections : reflections.slice(0, 3);

  renderListStack(
    reflectionList,
    visibleReflections,
    "Ask the library first, then the most recent linked reflections will appear here.",
    (item) =>
      createListItem(
        item.title || "Reflection",
        item.linked_note_title || item.primary_domain || "linked note",
        item.created_at || item.updated_at || item.path || ""
      )
  );

  reflectionViewAllButton.disabled = reflections.length <= 3;
  reflectionViewAllButton.textContent = state.ask.reflectionsExpanded ? "Show recent 3" : "View all";
}

function setAskBusy(isBusy) {
  state.ask.askBusy = isBusy;
  askSubmitButton.disabled = isBusy;
  document.getElementById("askMode").disabled = isBusy;
}

function setFeedbackBusy(isBusy) {
  state.ask.feedbackBusy = isBusy;
  draftCorrectionButton.disabled = isBusy;
  draftReflectionButton.disabled = isBusy;
  feedbackConfirmButton.disabled = isBusy || !state.ask.draft;
  feedbackDiscardButton.disabled = isBusy || !state.ask.draft;
  feedbackInput.disabled = isBusy;
  feedbackEditorTextarea.disabled = isBusy;
}

function normalizeDraft(kind, payload, userInput) {
  const draftPayload = payload.draft || payload.proposal || payload;
  const content =
    draftPayload.proposed_content ||
    draftPayload.body ||
    draftPayload.content ||
    payload.proposed_content ||
    payload.body ||
    payload.content ||
    "";

  return {
    id: draftPayload.id || payload.id || `${kind}-${Date.now()}`,
    kind,
    title:
      draftPayload.title ||
      payload.title ||
      (kind === "correction" ? "Correction Proposal" : "Reflection Draft"),
    targetRef: draftPayload.target_note_ref || draftPayload.linked_note_ref || payload.target_note_ref || payload.linked_note_ref || "",
    targetTitle:
      draftPayload.target_note_title || draftPayload.linked_note_title || payload.target_note_title || payload.linked_note_title || "",
    question: draftPayload.ask_question || payload.ask_question || state.ask.question,
    mode: draftPayload.ask_mode || payload.ask_mode || state.ask.mode,
    body: content,
    rawInput: draftPayload.raw_input || payload.raw_input || userInput,
    primaryDomain: draftPayload.primary_domain || payload.primary_domain || "",
    proposalPath: draftPayload.proposal_path || payload.proposal_path || "",
    groundingNoteRefs: draftPayload.grounding_note_refs || payload.grounding_note_refs || [],
    sourceRefs: draftPayload.source_refs || payload.source_refs || [],
    confirmEndpoint: kind === "correction" ? "/api/ask/correction/apply" : "/api/ask/reflection/confirm",
    confirmLabel: kind === "correction" ? "Apply correction" : "Confirm reflection",
    helperText:
      kind === "correction"
        ? "Review the full proposed corrected note, edit it inline if needed, then apply it."
        : "Review the reflection draft, edit it inline if needed, then confirm it.",
  };
}

function renderDraftEditor() {
  const draft = state.ask.draft;
  if (!draft) {
    clearDraftEditor(state.ask.grounding.length ? "No draft loaded yet." : "Ask the library first, then draft a correction or reflection here.");
    return;
  }

  feedbackEditorTitle.textContent = draft.kind === "correction" ? "Correction review" : "Reflection review";
  feedbackEditorStatus.textContent = draft.helperText;
  feedbackEditorEmpty.hidden = true;
  feedbackEditorBody.hidden = false;
  feedbackEditorMeta.innerHTML = "";
  feedbackEditorMeta.appendChild(
    createListItem(
      draft.targetTitle || draft.title,
      draft.kind === "correction" ? "Target note" : "Linked note",
      draft.targetRef || draft.rawInput || ""
    )
  );
  feedbackEditorMeta.appendChild(
    createListItem(
      draft.question || state.ask.question || "Ask context",
      draft.mode || state.ask.mode || "auto",
      draft.rawInput || ""
    )
  );
  if (feedbackEditorTextarea.dataset.draftId !== draft.id) {
    feedbackEditorTextarea.value = draft.body || "";
    feedbackEditorTextarea.dataset.draftId = draft.id;
  }
  feedbackConfirmButton.textContent = draft.confirmLabel;
  feedbackConfirmButton.disabled = state.ask.feedbackBusy ? true : false;
  feedbackDiscardButton.disabled = state.ask.feedbackBusy ? true : false;
}

async function runAsk(question, mode) {
  const requestId = ++state.ask.requestSeq;
  state.ask.feedbackSeq += 1;
  setAskBusy(true);
  state.ask.question = question;
  state.ask.mode = mode;
  state.ask.answer = "Thinking through the library…";
  state.ask.grounding = [];
  state.ask.trace = [];
  state.ask.limits = [];
  state.ask.reflections = [];
  state.ask.reflectionsExpanded = false;
  clearDraftEditor("Drafting and waiting for the library answer…");
  renderAskAnswer();
  renderReflections();

  try {
    const payload = await fetchJson("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, mode }),
    });

    if (requestId !== state.ask.requestSeq) {
      return;
    }

    state.ask.answer = payload.answer || "No answer returned.";
    state.ask.grounding = Array.isArray(payload.grounding) ? payload.grounding : [];
    state.ask.trace = Array.isArray(payload.trace) ? payload.trace : [];
    state.ask.limits = Array.isArray(payload.limits) ? payload.limits : [];
    state.ask.reflections = Array.isArray(payload.reflections)
      ? payload.reflections
      : Array.isArray(payload.recent_reflections)
        ? payload.recent_reflections
        : [];
    state.ask.reflectionsExpanded = false;
    renderAskAnswer();
    renderReflections();
  } catch (error) {
    if (requestId !== state.ask.requestSeq) {
      return;
    }
    state.ask.answer = `Ask failed: ${error.message}`;
    state.ask.grounding = [];
    state.ask.trace = [];
    state.ask.limits = [error.message];
    state.ask.reflections = [];
    state.ask.reflectionsExpanded = false;
    renderAskAnswer();
    renderReflections();
    feedbackEditorStatus.textContent = `Ask failed: ${error.message}`;
  } finally {
    if (requestId === state.ask.requestSeq) {
      setAskBusy(false);
    }
  }
}

async function submitFeedbackDraft(kind) {
  if (state.ask.feedbackBusy) {
    return;
  }
  const feedbackRequestId = ++state.ask.feedbackSeq;
  const askContext = { question: state.ask.question, mode: state.ask.mode };
  const input = feedbackInput.value.trim();
  if (!state.ask.question || !state.ask.grounding.length) {
    feedbackEditorStatus.textContent = "Ask the library first so the feedback can link to a note.";
    return;
  }
  if (!input) {
    feedbackEditorStatus.textContent = "Write the correction request or interpretation in the shared input first.";
    return;
  }

  const primaryGrounding = state.ask.grounding[0] || {};
  feedbackEditorStatus.textContent = kind === "correction" ? "Drafting correction…" : "Drafting reflection…";
  setFeedbackBusy(true);

  try {
    const payload = {
      question: state.ask.question,
      ask_question: state.ask.question,
      mode: state.ask.mode,
      ask_mode: state.ask.mode,
      input,
      raw_input: input,
      feedback_input: input,
      answer: state.ask.answer,
      grounding: state.ask.grounding,
      trace: state.ask.trace,
      limits: state.ask.limits,
      primary_grounding_ref: primaryGrounding.path || primaryGrounding.ref || "",
      primary_grounding_title: primaryGrounding.title || "",
      primary_domain: primaryGrounding.primary_domain || "",
    };
    const response = await fetchJson(kind === "correction" ? "/api/ask/correction/draft" : "/api/ask/reflection/draft", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (
      feedbackRequestId !== state.ask.feedbackSeq ||
      state.ask.question !== askContext.question ||
      state.ask.mode !== askContext.mode
    ) {
      return;
    }
    state.ask.draft = normalizeDraft(kind, response, input);
    renderDraftEditor();
  } catch (error) {
    if (feedbackRequestId !== state.ask.feedbackSeq) {
      return;
    }
    feedbackEditorStatus.textContent = `${kind === "correction" ? "Correction" : "Reflection"} draft failed: ${error.message}`;
    clearDraftEditor(feedbackEditorStatus.textContent);
  } finally {
    if (feedbackRequestId === state.ask.feedbackSeq) {
      setFeedbackBusy(false);
      if (state.ask.draft) {
        renderDraftEditor();
      }
    }
  }
}

async function confirmFeedbackDraft() {
  const draft = state.ask.draft;
  if (!draft) {
    return;
  }
  const feedbackRequestId = ++state.ask.feedbackSeq;
  const draftContext = { question: draft.question, mode: draft.mode, id: draft.id };

  const content = feedbackEditorTextarea.value.trim();
  if (!content) {
    feedbackEditorStatus.textContent = "The draft body cannot be empty.";
    return;
  }

  feedbackEditorStatus.textContent = draft.kind === "correction" ? "Applying correction…" : "Confirming reflection…";
  setFeedbackBusy(true);

  try {
    await fetchJson(draft.confirmEndpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        id: draft.id,
        kind: draft.kind,
        title: draft.title,
        target_ref: draft.targetRef,
        target_note_ref: draft.targetRef,
        target_note_title: draft.targetTitle,
        linked_note_ref: draft.targetRef,
        linked_note_title: draft.targetTitle,
        proposal_path: draft.proposalPath,
        ask_question: draft.question,
        ask_mode: draft.mode,
        raw_input: draft.rawInput,
        proposed_content: content,
        body: content,
        content,
        question: draft.question,
        mode: draft.mode,
        input: draft.rawInput,
        feedback_input: draft.rawInput,
        grounding_note_refs: draft.groundingNoteRefs,
        source_refs: draft.sourceRefs,
        primary_domain: draft.primaryDomain,
      }),
    });
    if (feedbackRequestId !== state.ask.feedbackSeq) {
      return;
    }
    feedbackInput.value = "";
    clearDraftEditor(draft.kind === "correction" ? "Correction applied. Refreshing the Ask answer…" : "Reflection saved. Refreshing linked reflections…");
    if (state.ask.question === draftContext.question && state.ask.mode === draftContext.mode) {
      await runAsk(draftContext.question, draftContext.mode);
    }
  } catch (error) {
    if (feedbackRequestId !== state.ask.feedbackSeq) {
      return;
    }
    feedbackEditorStatus.textContent = `${draft.kind === "correction" ? "Correction" : "Reflection"} confirmation failed: ${error.message}`;
  } finally {
    if (feedbackRequestId === state.ask.feedbackSeq) {
      setFeedbackBusy(false);
      if (state.ask.draft && state.ask.draft.id === draftContext.id) {
        renderDraftEditor();
      }
    }
  }
}

document.getElementById("askForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  await runAsk(document.getElementById("askInput").value, document.getElementById("askMode").value);
});

reflectionViewAllButton.addEventListener("click", () => {
  state.ask.reflectionsExpanded = !state.ask.reflectionsExpanded;
  renderReflections();
});

draftCorrectionButton.addEventListener("click", () => submitFeedbackDraft("correction"));
draftReflectionButton.addEventListener("click", () => submitFeedbackDraft("reflection"));
feedbackConfirmButton.addEventListener("click", confirmFeedbackDraft);
feedbackDiscardButton.addEventListener("click", () => {
  clearDraftEditor("Draft dismissed. You can refine the shared input and try again.");
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
      query: document.getElementById("routeQuery").value,
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

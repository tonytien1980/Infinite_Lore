const state = {
  page: "home",
  dashboard: null,
  bundles: [],
  knowledge: { synthesis: [], small_notes: [] },
  health: null,
  settings: null,
  inbox: {
    summary: null,
    sources: [],
    scanBusy: false,
    sourcesBusy: false,
    status: "就緒。",
  },
  ask: {
    question: "",
    mode: "auto",
    answer: "",
    grounding: [],
    trace: [],
    relationTrace: [],
    limits: [],
    reflections: [],
    reflectionsExpanded: false,
    draft: null,
    requestSeq: 0,
    feedbackSeq: 0,
    contextSeq: 0,
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
const askRelationTrace = document.getElementById("askRelationTrace");
const askLimits = document.getElementById("askLimits");
const reflectionList = document.getElementById("reflectionList");
const reflectionViewAllButton = document.getElementById("reflectionViewAllButton");
const feedbackInput = document.getElementById("feedbackInput");
const askForm = document.getElementById("askForm");
const askInput = document.getElementById("askInput");
const askMode = document.getElementById("askMode");
const askSubmitButton = document.getElementById("askSubmitButton");
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
const inboxSourceStatus = document.getElementById("inboxSourceStatus");
const inboxScanStatus = document.getElementById("inboxScanStatus");
const sourceList = document.getElementById("sourceList");
const addSourceButton = document.getElementById("addSourceButton");
const saveSourcesButton = document.getElementById("saveSourcesButton");
const scanSummary = document.getElementById("scanSummary");
const scanNowButton = document.getElementById("scanNowButton");
const refreshBundlesButton = document.getElementById("refreshBundlesButton");
const providerList = document.getElementById("providerList");
const addProviderButton = document.getElementById("addProviderButton");
const settingsForm = document.getElementById("settingsForm");
const routeScan = document.getElementById("routeScan");
const routeImport = document.getElementById("routeImport");
const routeEnrichRaw = document.getElementById("routeEnrichRaw");
const routeCompile = document.getElementById("routeCompile");
const routeQuery = document.getElementById("routeQuery");
const routeAsk = document.getElementById("routeAsk");
const routeReflection = document.getElementById("routeReflection");
const settingsStatus = document.getElementById("settingsStatus");
const PAGE_TITLES = {
  home: "首頁",
  summary: "摘要",
  inbox: "收件匣",
  knowledge: "知識庫",
  system: "系統",
  settings: "設定",
};
const ASK_EMPTY_MESSAGE = "提出問題後，系統會在這裡顯示可閱讀的主答案。";
const ASK_LOADING_MESSAGE = "系統正在整理答案，請稍候…";
const FOLLOWUP_DISABLED_HINT = "需先取得有證據的回答，才能起草修正或反思。";
const FOLLOWUP_ENABLED_HINT = "可在這裡補充修正方向、語氣調整或新的觀察。";

function setPage(page) {
  state.page = page;
  pages.forEach((element) => element.classList.toggle("active", element.dataset.page === page));
  navLinks.forEach((element) => element.classList.toggle("active", element.dataset.page === page));
  pageTitle.textContent = PAGE_TITLES[page] || page.charAt(0).toUpperCase() + page.slice(1);
}

function formatVaultName(path) {
  if (typeof path !== "string" || !path.trim()) {
    return "尚未指定";
  }
  const segments = path.split("/").filter(Boolean);
  return segments[segments.length - 1] || path;
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

function normalizeInboxSource(source, index) {
  const fallbackId = `source-${index + 1}`;
  return {
    id: typeof source?.id === "string" && source.id.trim() ? source.id.trim() : fallbackId,
    name: typeof source?.name === "string" ? source.name : "",
    source_type: source?.source_type === "article-list-page" ? "article-list-page" : "rss-feed",
    url: typeof source?.url === "string" ? source.url : "",
    enabled: source?.enabled !== false,
  };
}

function cloneInboxSources(sources) {
  return (Array.isArray(sources) ? sources : []).map((source, index) => normalizeInboxSource(source, index));
}

function normalizeProvider(provider, index) {
  const models = Array.isArray(provider?.models) ? provider.models : [];
  const fallbackProvider = typeof provider?.provider === "string" && provider.provider.trim() ? provider.provider.trim() : "openai";
  const fallbackId = fallbackProvider === "openai" ? `openai-${index + 1}` : `${fallbackProvider}-${index + 1}`;
  return {
    id: typeof provider?.id === "string" && provider.id.trim() ? provider.id.trim() : fallbackId,
    provider: fallbackProvider,
    enabled: provider?.enabled !== false,
    api_key: typeof provider?.api_key === "string" ? provider.api_key : "",
    base_url: typeof provider?.base_url === "string" ? provider.base_url : "",
    cheap_fast:
      models.find((model) => model?.role === "cheap_fast" && typeof model.id === "string" && model.id.trim())?.id || "",
    balanced:
      models.find((model) => model?.role === "balanced" && typeof model.id === "string" && model.id.trim())?.id || "",
    best_deep:
      models.find((model) => model?.role === "best_deep" && typeof model.id === "string" && model.id.trim())?.id || "",
  };
}

function cloneProviders(providers) {
  const normalized = (Array.isArray(providers) ? providers : []).map((provider, index) => normalizeProvider(provider, index));
  return normalized.length ? normalized : [normalizeProvider({}, 0)];
}

function providerLabel(provider, index) {
  const providerName = provider.provider || "provider";
  return provider.id || `${providerName}-${index + 1}`;
}

function createProviderPayload(provider, index) {
  const normalized = normalizeProvider(provider, index);
  const models = [];
  if (normalized.cheap_fast) {
    models.push({ id: normalized.cheap_fast, role: "cheap_fast" });
  }
  if (normalized.balanced) {
    models.push({ id: normalized.balanced, role: "balanced" });
  }
  if (normalized.best_deep) {
    models.push({ id: normalized.best_deep, role: "best_deep" });
  }
  return {
    id: normalized.id,
    provider: normalized.provider,
    enabled: normalized.enabled,
    api_key: normalized.api_key,
    base_url: normalized.base_url,
    models,
  };
}

function buildRouteProviderPreferences(providers, existingPreferences) {
  const normalizedProviders = providers.map((provider, index) => normalizeProvider(provider, index)).filter((provider) => provider.id);
  const availableIds = normalizedProviders.map((provider) => provider.id);
  const openaiFirst = normalizedProviders
    .slice()
    .sort((left, right) => {
      const leftScore = left.provider === "openai" ? 0 : 1;
      const rightScore = right.provider === "openai" ? 0 : 1;
      return leftScore - rightScore;
    })
    .map((provider) => provider.id);
  const localFirst = normalizedProviders
    .slice()
    .sort((left, right) => {
      const leftScore = left.provider === "openai" ? 1 : 0;
      const rightScore = right.provider === "openai" ? 1 : 0;
      return leftScore - rightScore;
    })
    .map((provider) => provider.id);

  function mergePreference(routeName, fallbackList) {
    const existingList = existingPreferences?.[routeName];
    if (!Array.isArray(existingList) || !existingList.length) {
      return fallbackList;
    }
    const surviving = existingList.filter((providerId) => availableIds.includes(providerId));
    const missing = fallbackList.filter((providerId) => !surviving.includes(providerId));
    return [...surviving, ...missing];
  }

  return {
    ask: mergePreference("ask", openaiFirst),
    enrich_raw: mergePreference("enrich_raw", openaiFirst),
    reflection: mergePreference("reflection", openaiFirst),
    compile: mergePreference("compile", localFirst.length ? localFirst : availableIds),
  };
}

function addProvider() {
  const nextIndex = Array.isArray(state.settings?.providers) ? state.settings.providers.length : 0;
  const defaultProvider =
    nextIndex === 0
      ? normalizeProvider({}, nextIndex)
      : normalizeProvider({ provider: "ollama", base_url: "http://127.0.0.1:11434" }, nextIndex);
  state.settings = {
    ...(state.settings || {}),
    providers: [...(state.settings?.providers || []), defaultProvider],
  };
  renderProviders();
}

function renderProviders() {
  const providers = cloneProviders(state.settings?.providers || []);
  state.settings = { ...(state.settings || {}), providers };
  providerList.innerHTML = "";
  providerList.className = "list-stack";

  providers.forEach((provider, index) => {
    const card = document.createElement("article");
    card.className = "list-item";

    const header = document.createElement("div");
    header.className = "panel-head split";
    const titleWrap = document.createElement("div");
    const meta = document.createElement("p");
    meta.className = "eyebrow";
    meta.textContent = provider.enabled ? "啟用中" : "已停用";
    const title = document.createElement("h3");
    title.textContent = providerLabel(provider, index);
    titleWrap.append(meta, title);

    const actions = document.createElement("div");
    actions.className = "button-row";
    const removeButton = document.createElement("button");
    removeButton.type = "button";
    removeButton.className = "ghost-button";
    removeButton.textContent = "移除";
    removeButton.disabled = providers.length === 1;
    removeButton.addEventListener("click", () => {
      state.settings.providers.splice(index, 1);
      renderProviders();
    });
    actions.appendChild(removeButton);
    header.append(titleWrap, actions);

    const fields = document.createElement("div");
    fields.className = "route-grid";

    const providerTypeLabel = document.createElement("label");
    providerTypeLabel.innerHTML = "<span>供應商類型</span>";
    const providerTypeSelect = document.createElement("select");
    [
      ["openai", "OpenAI"],
      ["ollama", "Ollama"],
    ].forEach(([value, text]) => {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = text;
      providerTypeSelect.appendChild(option);
    });
    providerTypeSelect.value = provider.provider;
    providerTypeSelect.addEventListener("change", () => {
      state.settings.providers[index].provider = providerTypeSelect.value;
      if (providerTypeSelect.value === "ollama" && !state.settings.providers[index].base_url) {
        state.settings.providers[index].base_url = "http://127.0.0.1:11434";
      }
      renderProviders();
    });
    providerTypeLabel.appendChild(providerTypeSelect);

    const providerIdLabel = document.createElement("label");
    providerIdLabel.innerHTML = "<span>供應商 ID</span>";
    const providerIdInput = document.createElement("input");
    providerIdInput.type = "text";
    providerIdInput.value = provider.id;
    providerIdInput.autocomplete = "username";
    providerIdInput.addEventListener("input", () => {
      state.settings.providers[index].id = providerIdInput.value;
      title.textContent = providerLabel(state.settings.providers[index], index);
    });
    providerIdLabel.appendChild(providerIdInput);

    const enabledLabel = document.createElement("label");
    enabledLabel.className = "inline-checkbox";
    const enabledInput = document.createElement("input");
    enabledInput.type = "checkbox";
    enabledInput.checked = provider.enabled !== false;
    enabledInput.addEventListener("change", () => {
      state.settings.providers[index].enabled = enabledInput.checked;
      meta.textContent = enabledInput.checked ? "啟用中" : "已停用";
    });
    const enabledText = document.createElement("span");
    enabledText.textContent = "啟用";
    enabledLabel.append(enabledInput, enabledText);

    const apiKeyLabel = document.createElement("label");
    apiKeyLabel.innerHTML = "<span>API 金鑰</span>";
    const apiKeyInput = document.createElement("input");
    apiKeyInput.type = "password";
    apiKeyInput.value = provider.api_key;
    apiKeyInput.placeholder = "存放於本機設定，不進入知識庫";
    apiKeyInput.autocomplete = "new-password";
    apiKeyInput.addEventListener("input", () => {
      state.settings.providers[index].api_key = apiKeyInput.value;
    });
    apiKeyLabel.appendChild(apiKeyInput);

    const baseUrlLabel = document.createElement("label");
    baseUrlLabel.innerHTML = "<span>Base URL</span>";
    const baseUrlInput = document.createElement("input");
    baseUrlInput.type = "url";
    baseUrlInput.value = provider.base_url;
    baseUrlInput.placeholder = "例如：http://127.0.0.1:11434";
    baseUrlInput.addEventListener("input", () => {
      state.settings.providers[index].base_url = baseUrlInput.value;
    });
    baseUrlLabel.appendChild(baseUrlInput);

    const balancedLabel = document.createElement("label");
    balancedLabel.innerHTML = "<span>平衡模型</span>";
    const balancedInput = document.createElement("input");
    balancedInput.type = "text";
    balancedInput.value = provider.balanced;
    balancedInput.placeholder = "模型識別碼";
    balancedInput.addEventListener("input", () => {
      state.settings.providers[index].balanced = balancedInput.value;
    });
    balancedLabel.appendChild(balancedInput);

    const cheapFastLabel = document.createElement("label");
    cheapFastLabel.innerHTML = "<span>小而快模型</span>";
    const cheapFastInput = document.createElement("input");
    cheapFastInput.type = "text";
    cheapFastInput.value = provider.cheap_fast;
    cheapFastInput.placeholder = "模型識別碼";
    cheapFastInput.addEventListener("input", () => {
      state.settings.providers[index].cheap_fast = cheapFastInput.value;
    });
    cheapFastLabel.appendChild(cheapFastInput);

    const bestLabel = document.createElement("label");
    bestLabel.innerHTML = "<span>高品質 / 深度模型</span>";
    const bestInput = document.createElement("input");
    bestInput.type = "text";
    bestInput.value = provider.best_deep;
    bestInput.placeholder = "模型識別碼";
    bestInput.addEventListener("input", () => {
      state.settings.providers[index].best_deep = bestInput.value;
    });
    bestLabel.appendChild(bestInput);

    fields.append(
      providerTypeLabel,
      providerIdLabel,
      enabledLabel,
      apiKeyLabel,
      baseUrlLabel,
      cheapFastLabel,
      balancedLabel,
      bestLabel
    );
    card.append(header, fields);
    providerList.appendChild(card);
  });

  if (!providerList.children.length) {
    providerList.className = "list-stack empty-state";
    providerList.textContent = "尚未設定供應商。";
  }
}

function createMetricCard(label, value, detail) {
  const card = document.createElement("article");
  card.className = "scan-metric";
  const eyebrow = document.createElement("p");
  eyebrow.className = "eyebrow";
  eyebrow.textContent = label;
  const strong = document.createElement("strong");
  strong.textContent = String(value);
  const body = document.createElement("p");
  body.textContent = detail || "";
  card.append(eyebrow, strong, body);
  return card;
}

function canDraftFollowup() {
  return !state.ask.askBusy && Array.isArray(state.ask.grounding) && state.ask.grounding.length > 0;
}

function syncFollowupControls() {
  const canDraft = canDraftFollowup();
  feedbackInput.disabled = state.ask.feedbackBusy || !canDraft;
  draftCorrectionButton.disabled = state.ask.feedbackBusy || !canDraft;
  draftReflectionButton.disabled = state.ask.feedbackBusy || !canDraft;
  feedbackConfirmButton.disabled = state.ask.feedbackBusy || !state.ask.draft;
  feedbackDiscardButton.disabled = state.ask.feedbackBusy || !state.ask.draft;
  feedbackEditorTextarea.disabled = state.ask.feedbackBusy || !state.ask.draft;
  if (!state.ask.draft) {
    feedbackHint.textContent = canDraft ? FOLLOWUP_ENABLED_HINT : FOLLOWUP_DISABLED_HINT;
  }
}

function renderInboxSources() {
  const sources = state.inbox.sources;
  inboxSourceStatus.textContent = `${sources.length} 個已設定來源`;
  sourceList.innerHTML = "";

  if (!sources.length) {
    sourceList.className = "source-list empty-state";
    sourceList.textContent = "尚未設定來源，請先新增 RSS 或清單頁來源。";
    return;
  }

  sourceList.className = "source-list";
  sources.forEach((source, index) => {
    const row = document.createElement("article");
    row.className = "source-card";

    const header = document.createElement("div");
    header.className = "source-card-head";
    const title = document.createElement("strong");
    title.textContent = source.name || source.id || `來源 ${index + 1}`;
    const meta = document.createElement("p");
    meta.className = "eyebrow";
    meta.textContent = source.enabled ? "啟用" : "停用";
    const removeButton = document.createElement("button");
    removeButton.type = "button";
    removeButton.className = "ghost-button";
    removeButton.textContent = "移除";
    removeButton.addEventListener("click", () => {
      state.inbox.sources.splice(index, 1);
      renderInboxSources();
    });
    header.append(title, meta, removeButton);

    const fields = document.createElement("div");
    fields.className = "source-fields";

    const idLabel = document.createElement("label");
    idLabel.innerHTML = "<span>來源代碼</span>";
    const idInput = document.createElement("input");
    idInput.type = "text";
    idInput.value = source.id || "";
    idInput.addEventListener("input", () => {
      state.inbox.sources[index].id = idInput.value;
    });
    idLabel.appendChild(idInput);

    const nameLabel = document.createElement("label");
    nameLabel.innerHTML = "<span>名稱</span>";
    const nameInput = document.createElement("input");
    nameInput.type = "text";
    nameInput.value = source.name || "";
    nameInput.addEventListener("input", () => {
      state.inbox.sources[index].name = nameInput.value;
    });
    nameLabel.appendChild(nameInput);

    const typeLabel = document.createElement("label");
    typeLabel.innerHTML = "<span>來源類型</span>";
    const typeSelect = document.createElement("select");
    [
      ["rss-feed", "RSS / 來源"],
      ["article-list-page", "網頁清單頁"],
    ].forEach(([value, text]) => {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = text;
      typeSelect.appendChild(option);
    });
    typeSelect.value = source.source_type || "rss-feed";
    typeSelect.addEventListener("change", () => {
      state.inbox.sources[index].source_type = typeSelect.value;
    });
    typeLabel.appendChild(typeSelect);

    const urlLabel = document.createElement("label");
    urlLabel.innerHTML = "<span>來源網址</span>";
    const urlInput = document.createElement("input");
    urlInput.type = "url";
    urlInput.value = source.url || "";
    urlInput.addEventListener("input", () => {
      state.inbox.sources[index].url = urlInput.value;
    });
    urlLabel.appendChild(urlInput);

    const enabledLabel = document.createElement("label");
    enabledLabel.className = "inline-checkbox";
    const enabledInput = document.createElement("input");
    enabledInput.type = "checkbox";
    enabledInput.checked = source.enabled !== false;
    enabledInput.addEventListener("change", () => {
      state.inbox.sources[index].enabled = enabledInput.checked;
      meta.textContent = enabledInput.checked ? "啟用" : "停用";
    });
    const enabledText = document.createElement("span");
    enabledText.textContent = "啟用";
    enabledLabel.append(enabledInput, enabledText);

    fields.append(idLabel, nameLabel, typeLabel, urlLabel, enabledLabel);
    row.append(header, fields);
    sourceList.appendChild(row);
  });
}

function renderInboxScanSummary() {
  const summary = state.inbox.summary;
  scanSummary.innerHTML = "";

  if (!summary || !summary.last_scan) {
    scanSummary.className = "scan-summary empty-state";
    scanSummary.textContent = summary?.state_warning
      ? "尚未執行掃描，且已從壞掉的儲存回復。"
      : "尚未執行掃描。";
    return;
  }

  scanSummary.className = "scan-summary";
  const note = document.createElement("p");
  note.className = "scan-summary-note";
  note.textContent = summary.recovered_from_corruption
    ? "本次掃描前已從損壞檔案回復來源狀態。"
    : "本次掃描摘要如下。";
  scanSummary.appendChild(note);

  const grid = document.createElement("div");
  grid.className = "scan-summary-grid";
  const lastScan = summary.last_scan || {};
  [
    ["執行時間", lastScan.ran_at || "尚未記錄", "時間戳記（UTC）"],
    ["發現數", lastScan.discovered_count ?? 0, "候選來源數"],
    ["去重數", lastScan.deduplicated_count ?? 0, "排重後保留數"],
    ["已匯入", lastScan.imported_count ?? 0, "已建立原始筆記"],
    ["已編譯", lastScan.compiled_count ?? 0, "已編譯完成筆記"],
    ["失敗", lastScan.failed_count ?? 0, "待重試項目"],
    ["耗盡重試", lastScan.exhausted_failed_count ?? 0, "已用盡重試次數"],
    ["重試上限", lastScan.retry_limit ?? 0, "最大重試次數"],
  ].forEach(([label, value, detail]) => {
    grid.appendChild(createMetricCard(label, value, detail));
  });
  scanSummary.appendChild(grid);

  const foot = document.createElement("p");
  foot.className = "scan-summary-foot";
  const parts = [
    `${summary.sources?.length ?? 0} 個來源`,
    `${summary.failed_count ?? 0} 項失敗`,
    `${summary.processed_count ?? 0} 項已處理`,
  ];
  if (summary.state_warning) {
    parts.push(`狀態：${summary.state_warning}`);
  }
  foot.textContent = parts.join(" • ");
  scanSummary.appendChild(foot);
}

function renderInbox() {
  renderInboxSources();
  renderInboxScanSummary();
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
        item.primary_domain || "未分類",
        `${item.bundle_path} • ${item.conversion_status || "未定義"}`
      )
    );
  });
  if (!imports.children.length) imports.textContent = "目前還沒有匯入紀錄。先到收件匣加入第一份原始資料。";

  knowledge.innerHTML = "";
  (state.dashboard?.recent_synthesis || []).forEach((item) => {
    knowledge.appendChild(createListItem(item.title, item.primary_domain || "知識庫", item.path));
  });
  if (!knowledge.children.length) knowledge.textContent = "目前還沒有已編譯知識。完成匯入與編譯後，摘要會先在這裡更新。";

  cards.innerHTML = "";
  const snapshotEntries = [
    ["待處理包", state.dashboard?.bundle_count ?? 0, "原始匯入單元"],
    ["知識筆記", state.dashboard?.knowledge_count ?? 0, "已完成編譯"],
    ["警示", state.dashboard?.warning_count ?? 0, "待注意項目"],
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
    const review = bundle.review_required === "true" ? "待審核" : "可用";
    container.appendChild(
      createListItem(bundle.title, bundle.primary_domain || "未分類", `${bundle.bundle_path} • ${review}`)
    );
  });
  if (!container.children.length) container.textContent = "目前沒有待處理的項目。可在上方立即掃描，或先新增新的來源入口。";
}

function renderKnowledge() {
  const synthesis = document.getElementById("synthesisList");
  const small = document.getElementById("smallNotesList");
  synthesis.innerHTML = "";
  small.innerHTML = "";

  state.knowledge.synthesis.forEach((note) => {
    synthesis.appendChild(createListItem(note.title, note.primary_domain || "知識庫", note.path));
  });
  if (!synthesis.children.length) synthesis.textContent = "目前還沒有合成條目。先從收件匣匯入資料，或執行立即掃描。";

  state.knowledge.small_notes.forEach((note) => {
    small.appendChild(createListItem(note.title, `${note.note_type} • ${note.primary_domain || "知識庫"}`, note.path));
  });
  if (!small.children.length) small.textContent = "目前還沒有小節筆記。完成編譯後，概念、框架與問題會逐步累積在這裡。";
}

function renderHealth() {
  const target = document.getElementById("healthDetails");
  target.innerHTML = "";
  const health = state.health;
  if (!health) {
    target.textContent = "載入健康狀態…";
    return;
  }
  healthPill.textContent = health.status === "ok" ? "運作正常" : "需要回顧";
  target.textContent = health.status === "ok" ? "知識庫健康檢查通過。" : health.errors.join("\n");
}

function populateSettings() {
  const settings = state.settings || {};
  state.settings = {
    ...settings,
    providers: cloneProviders(settings.providers),
  };
  renderProviders();

  const routes = settings.routes || {};
  routeScan.value = routes.scan || "no_model";
  routeImport.value = routes.import || "no_model";
  routeEnrichRaw.value = routes.enrich_raw || "balanced";
  routeCompile.value = routes.compile || "balanced";
  routeQuery.value = routes.query || "no_model";
  routeAsk.value = routes.ask || "best_deep";
  routeReflection.value = routes.reflection || "balanced";
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
  state.inbox.summary = await fetchJson("/api/inbox/summary");
  state.inbox.sources = cloneInboxSources(state.inbox.summary.sources || []);
  state.settings = await fetchJson("/api/settings");
  vaultPath.textContent = formatVaultName(systemInfo.vault_root);
  vaultPath.title = systemInfo.vault_root;
  systemVaultPath.textContent = systemInfo.vault_root;
  renderDashboard();
  renderBundles();
  renderKnowledge();
  renderHealth();
  renderInbox();
  populateSettings();
  syncFollowupControls();
}

function setInboxBusy(isBusy, message) {
  state.inbox.scanBusy = isBusy;
  state.inbox.status = message || (isBusy ? "執行中…" : "就緒。");
  scanNowButton.disabled = isBusy;
  refreshBundlesButton.disabled = isBusy;
  addSourceButton.disabled = isBusy;
  saveSourcesButton.disabled = isBusy;
  inboxScanStatus.textContent = state.inbox.status;
}

function addInboxSource() {
  state.inbox.sources.push(
    normalizeInboxSource(
      {
        id: `source-${state.inbox.sources.length + 1}`,
        name: "",
        source_type: "rss-feed",
        url: "",
        enabled: true,
      },
      state.inbox.sources.length
    )
  );
  renderInboxSources();
}

async function persistInboxSources() {
  return fetchJson("/api/inbox/sources", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sources: state.inbox.sources }),
  });
}

async function saveInboxSources() {
  if (state.inbox.sourcesBusy) {
    return;
  }
  state.inbox.sourcesBusy = true;
  setInboxBusy(true, "正在儲存來源設定…");
  try {
    await persistInboxSources();
    await loadAll();
    state.inbox.status = "來源設定已儲存。";
    inboxScanStatus.textContent = state.inbox.status;
  } catch (error) {
    state.inbox.status = `來源儲存失敗：${error.message}`;
    inboxScanStatus.textContent = state.inbox.status;
  } finally {
    state.inbox.sourcesBusy = false;
    setInboxBusy(false, state.inbox.status);
  }
}

async function runInboxScan() {
  if (state.inbox.scanBusy) {
    return;
  }
  setInboxBusy(true, "先儲存來源設定並開始掃描…");
  try {
    try {
      await persistInboxSources();
    } catch (error) {
      state.inbox.status = `掃描前來源儲存失敗：${error.message}`;
      inboxScanStatus.textContent = state.inbox.status;
      return;
    }

    const summary = await fetchJson("/api/inbox/scan", { method: "POST" });
    state.inbox.summary = {
      ...(state.inbox.summary || {}),
      last_scan: summary,
    };
    renderInbox();
    try {
      await loadAll();
    } catch (refreshError) {
      state.inbox.status = `掃描完成，但資料重整失敗：${refreshError.message}`;
      inboxScanStatus.textContent = state.inbox.status;
      return;
    }
    state.inbox.status = "掃描完成。";
    inboxScanStatus.textContent = state.inbox.status;
  } catch (error) {
    state.inbox.status = `掃描失敗：${error.message}`;
    inboxScanStatus.textContent = state.inbox.status;
  } finally {
    setInboxBusy(false, state.inbox.status);
  }
}

navLinks.forEach((button) => {
  button.addEventListener("click", () => setPage(button.dataset.page));
});

function clearDraftEditor(message = "目前沒有草稿。") {
  state.ask.draft = null;
  feedbackEditorTitle.textContent = "草稿審閱";
  feedbackEditorStatus.textContent = message;
  feedbackEditorEmpty.hidden = false;
  feedbackEditorBody.hidden = true;
  feedbackEditorMeta.innerHTML = "";
  feedbackEditorTextarea.value = "";
  feedbackEditorTextarea.dataset.draftId = "";
  feedbackConfirmButton.textContent = "確認";
  syncFollowupControls();
}

function renderAskAnswer() {
  const answerText = state.ask.answer || ASK_EMPTY_MESSAGE;
  askAnswer.textContent = answerText;
  askAnswer.classList.toggle("empty-state", answerText === ASK_EMPTY_MESSAGE || answerText === ASK_LOADING_MESSAGE);
  askAnswer.classList.toggle("answer-body", !(answerText === ASK_EMPTY_MESSAGE || answerText === ASK_LOADING_MESSAGE));

  renderListStack(
    askGrounding,
    state.ask.grounding,
    "基礎證據將顯示在這裡。",
    (item) => createListItem(item.title || item.path || "基礎證據", item.note_type || item.primary_domain || "知識庫", item.path || item.ref || "")
  );

  renderListStack(
    askTrace,
    state.ask.trace,
    "來源回溯將顯示在這裡。",
    (item) => createListItem(item.source_ref || item.path || "來源代碼", "來源", item.from_note || item.title || "")
  );

  renderListStack(
    askRelationTrace,
    state.ask.relationTrace,
    "關聯追蹤會在知識沿連結展開時顯示於此。",
    (item) =>
      createListItem(
        item.source_note || "來源筆記",
        `${item.relation || "關聯"} • ${item.confidence || "信心"}`,
        item.target_note || "目標筆記"
      )
  );

  renderListStack(
    askLimits,
    state.ask.limits,
    "需要提示時，這裡會顯示答案邊界與不確定性。",
    (item) => createListItem(item, "限制", "證據邊界")
  );
  syncFollowupControls();
}

function renderReflections() {
  const reflections = state.ask.reflections || [];
  const visibleReflections = state.ask.reflectionsExpanded ? reflections : reflections.slice(0, 3);

  renderListStack(
    reflectionList,
    visibleReflections,
    "先完成提問，才會在這裡顯示最近連結的反思紀錄。",
    (item) =>
      createListItem(
        item.title || "反思紀錄",
        item.linked_note_title || item.primary_domain || "關聯筆記",
        item.created_at || item.updated_at || item.path || ""
      )
  );

  reflectionViewAllButton.disabled = reflections.length <= 3;
  reflectionViewAllButton.textContent = state.ask.reflectionsExpanded ? "只看最近 3 筆" : "查看全部";
}

function setAskBusy(isBusy) {
  state.ask.askBusy = isBusy;
  askInput.disabled = isBusy;
  askMode.disabled = isBusy;
  askSubmitButton.disabled = isBusy;
  syncFollowupControls();
}

function setFeedbackBusy(isBusy) {
  state.ask.feedbackBusy = isBusy;
  syncFollowupControls();
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
      (kind === "correction" ? "修正草稿" : "反思草稿"),
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
    confirmLabel: kind === "correction" ? "套用修正" : "確認反思",
    helperText:
      kind === "correction"
        ? "先審閱完整修正草稿，必要時可直接編修，再決定是否套用。"
        : "先審閱反思草稿，必要時可直接編修，再決定是否確認。",
  };
}

function renderDraftEditor() {
  const draft = state.ask.draft;
  if (!draft) {
    clearDraftEditor(state.ask.grounding.length ? "目前沒有草稿。" : "先取得有證據的回答，才會開啟草稿審閱。");
    return;
  }

  feedbackEditorTitle.textContent = draft.kind === "correction" ? "修正審閱" : "反思審閱";
  feedbackEditorStatus.textContent = draft.helperText;
  feedbackEditorEmpty.hidden = true;
  feedbackEditorBody.hidden = false;
  feedbackEditorMeta.innerHTML = "";
  feedbackEditorMeta.appendChild(
    createListItem(
      draft.targetTitle || draft.title,
      draft.kind === "correction" ? "對應筆記" : "關聯筆記",
      draft.targetRef || draft.rawInput || ""
    )
  );
  feedbackEditorMeta.appendChild(
    createListItem(
      draft.question || state.ask.question || "提問內容",
      draft.mode || state.ask.mode || "auto",
      draft.rawInput || ""
    )
  );
  if (feedbackEditorTextarea.dataset.draftId !== draft.id) {
    feedbackEditorTextarea.value = draft.body || "";
    feedbackEditorTextarea.dataset.draftId = draft.id;
  }
  feedbackConfirmButton.textContent = draft.confirmLabel;
  syncFollowupControls();
}

async function runAsk(question, mode) {
  const requestId = ++state.ask.requestSeq;
  state.ask.contextSeq += 1;
  setAskBusy(true);
  state.ask.question = question;
  state.ask.mode = mode;
  state.ask.answer = ASK_LOADING_MESSAGE;
  state.ask.grounding = [];
  state.ask.trace = [];
  state.ask.relationTrace = [];
  state.ask.limits = [];
  state.ask.reflections = [];
  state.ask.reflectionsExpanded = false;
  clearDraftEditor("正在等待回答，暫時不建立草稿。");
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

    state.ask.answer = payload.answer || "尚未取得答案。";
    state.ask.grounding = Array.isArray(payload.grounding) ? payload.grounding : [];
    state.ask.trace = Array.isArray(payload.trace) ? payload.trace : [];
    state.ask.relationTrace = Array.isArray(payload.relation_trace) ? payload.relation_trace : [];
    state.ask.limits = Array.isArray(payload.limits) ? payload.limits : [];
    state.ask.reflections = Array.isArray(payload.reflections)
      ? payload.reflections
      : Array.isArray(payload.recent_reflections)
        ? payload.recent_reflections
        : [];
    state.ask.reflectionsExpanded = false;
    clearDraftEditor(state.ask.grounding.length ? "目前沒有草稿。" : "先取得有證據的回答，才會開啟草稿審閱。");
    renderAskAnswer();
    renderReflections();
  } catch (error) {
    if (requestId !== state.ask.requestSeq) {
      return;
    }
    state.ask.answer = `提問失敗：${error.message}`;
    state.ask.grounding = [];
    state.ask.trace = [];
    state.ask.relationTrace = [];
    state.ask.limits = [error.message];
    state.ask.reflections = [];
    state.ask.reflectionsExpanded = false;
    clearDraftEditor("提問失敗，暫時無法建立草稿。");
    renderAskAnswer();
    renderReflections();
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
  const askContext = { question: state.ask.question, mode: state.ask.mode, contextSeq: state.ask.contextSeq };
  const input = feedbackInput.value.trim();
  if (!state.ask.question || !state.ask.grounding.length) {
    feedbackEditorStatus.textContent = "請先完成提問，回饋才能對應到知識來源。";
    return;
  }
  if (!input) {
    feedbackEditorStatus.textContent = "請先在共用輸入框寫下修正要求或反思內容。";
    return;
  }

  const primaryGrounding = state.ask.grounding[0] || {};
  feedbackEditorStatus.textContent = kind === "correction" ? "正在草擬修正建議…" : "正在草擬反思草稿…";
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
      state.ask.contextSeq !== askContext.contextSeq ||
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
    feedbackEditorStatus.textContent = `${kind === "correction" ? "修正" : "反思"}草稿產生失敗：${error.message}`;
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
  const draftContext = { question: draft.question, mode: draft.mode, id: draft.id, contextSeq: state.ask.contextSeq };

  const content = feedbackEditorTextarea.value.trim();
  if (!content) {
    feedbackEditorStatus.textContent = "草稿內容不可為空。";
    return;
  }

  feedbackEditorStatus.textContent = draft.kind === "correction" ? "正在套用修正…" : "正在確認反思…";
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
    clearDraftEditor(
      draft.kind === "correction" ? "修正已套用，將重新整理回答…" : "反思已儲存，將刷新最近反思…"
    );
    if (
      state.ask.contextSeq === draftContext.contextSeq &&
      state.ask.question === draftContext.question &&
      state.ask.mode === draftContext.mode
    ) {
      await runAsk(draftContext.question, draftContext.mode);
    }
  } catch (error) {
    if (feedbackRequestId !== state.ask.feedbackSeq) {
      return;
    }
    feedbackEditorStatus.textContent = `${draft.kind === "correction" ? "修正" : "反思"}確認失敗：${error.message}`;
  } finally {
    if (feedbackRequestId === state.ask.feedbackSeq) {
      setFeedbackBusy(false);
      if (state.ask.draft && state.ask.draft.id === draftContext.id) {
        renderDraftEditor();
      }
    }
  }
}

askForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  await runAsk(askInput.value, askMode.value);
});

reflectionViewAllButton.addEventListener("click", () => {
  state.ask.reflectionsExpanded = !state.ask.reflectionsExpanded;
  renderReflections();
});

draftCorrectionButton.addEventListener("click", () => submitFeedbackDraft("correction"));
draftReflectionButton.addEventListener("click", () => submitFeedbackDraft("reflection"));
feedbackConfirmButton.addEventListener("click", confirmFeedbackDraft);
feedbackDiscardButton.addEventListener("click", () => {
  clearDraftEditor("已放棄草稿。可再次調整共用輸入框後重試。");
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

refreshBundlesButton.addEventListener("click", loadAll);
scanNowButton.addEventListener("click", async () => {
  await runInboxScan();
});
addSourceButton.addEventListener("click", addInboxSource);
saveSourcesButton.addEventListener("click", async () => {
  await saveInboxSources();
});

addProviderButton.addEventListener("click", addProvider);

settingsForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const providerPayload = cloneProviders(state.settings?.providers || []).map((provider, index) => createProviderPayload(provider, index));
  const payload = {
    providers: providerPayload,
    routes: {
      scan: routeScan.value,
      import: routeImport.value,
      enrich_raw: routeEnrichRaw.value,
      compile: routeCompile.value,
      query: routeQuery.value,
      ask: routeAsk.value,
      reflection: routeReflection.value,
    },
    route_provider_preferences: buildRouteProviderPreferences(providerPayload, state.settings?.route_provider_preferences),
  };
  state.settings = await fetchJson("/api/settings", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  populateSettings();
  settingsStatus.textContent = "本機設定已儲存。";
});

loadAll().catch((error) => {
  healthPill.textContent = "載入失敗";
  document.getElementById("healthDetails").textContent = error.message;
});

setPage(state.page);

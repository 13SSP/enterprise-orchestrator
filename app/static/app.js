// Enterprise AI Orchestrator UI Client
let currentPersona = "devops_admin";
let personasData = {};
let currentJwtToken = "";
let auditPollingInterval = null;
let allAgentsList = [];
let agentSearchQuery = "";
let agentScopeFilter = "all";
let currentEditingAgent = null;

// Initialize on page load
document.addEventListener("DOMContentLoaded", async () => {
  if (window.lucide) window.lucide.createIcons();

  await loadPersonas();
  await loadAgents();
  await loadTools();
  await loadKnowledgeDocs();
  await loadAuditLogs();

  setupEventListeners();

  // Start background log polling
  auditPollingInterval = setInterval(loadAuditLogs, 4000);
});

// Setup event listeners
function setupEventListeners() {
  // Tab Switching
  const tabs = [
    { btn: "tabChatBtn", content: "tabChat" },
    { btn: "tabOnboardBtn", content: "tabOnboard" },
    { btn: "tabSwaggerBtn", content: "tabSwagger" },
    { btn: "tabRagBtn", content: "tabRag" },
    { btn: "tabAuditBtn", content: "tabAudit" }
  ];

  tabs.forEach(t => {
    const btn = document.getElementById(t.btn);
    btn.addEventListener("click", () => {
      tabs.forEach(other => {
        document.getElementById(other.btn).classList.remove("active", "bg-indigo-600", "text-white", "shadow-sm", "shadow-indigo-600/30");
        document.getElementById(other.btn).classList.add("text-slate-400");
        document.getElementById(other.content).classList.add("hidden");
        document.getElementById(other.content).classList.remove("flex");
      });
      btn.classList.add("active", "bg-indigo-600", "text-white", "shadow-sm", "shadow-indigo-600/30");
      btn.classList.remove("text-slate-400");
      const targetContent = document.getElementById(t.content);
      targetContent.classList.remove("hidden");
      targetContent.classList.add("flex");
      if (window.lucide) window.lucide.createIcons();
    });
  });

  // Persona Switcher
  const personaSelect = document.getElementById("personaSelect");
  personaSelect.addEventListener("change", (e) => {
    currentPersona = e.target.value;
    if (personasData[currentPersona]) {
      currentJwtToken = personasData[currentPersona].jwt;
    }
    appendSystemNotice(`Switched active persona to <strong>${personaSelect.options[personaSelect.selectedIndex].text}</strong>. New JWT claims applied.`);
    renderAgentsDirectory();
  });

  // JWT Modal
  document.getElementById("viewJwtBtn").addEventListener("click", showJwtModal);
  document.getElementById("closeJwtModal").addEventListener("click", () => {
    document.getElementById("jwtModal").classList.add("hidden");
  });

  // Chat Form
  document.getElementById("chatForm").addEventListener("submit", handleChatSubmit);

  // Quick Prompts
  document.querySelectorAll(".quick-prompt").forEach(btn => {
    btn.addEventListener("click", () => {
      const input = document.getElementById("chatInput");
      input.value = btn.innerText.trim();
      input.focus();
    });
  });

  // Agents Hub Directory Search & Filter Listeners
  const searchInput = document.getElementById("agentSearchInput");
  const clearSearchBtn = document.getElementById("clearAgentSearchBtn");
  if (searchInput) {
    searchInput.addEventListener("input", (e) => {
      agentSearchQuery = e.target.value.trim();
      if (clearSearchBtn) {
        if (agentSearchQuery) clearSearchBtn.classList.remove("hidden");
        else clearSearchBtn.classList.add("hidden");
      }
      renderAgentsDirectory();
    });
  }
  if (clearSearchBtn) {
    clearSearchBtn.addEventListener("click", () => {
      if (searchInput) searchInput.value = "";
      agentSearchQuery = "";
      clearSearchBtn.classList.add("hidden");
      renderAgentsDirectory();
    });
  }

  const filterAllBtn = document.getElementById("filterAllAgentsBtn");
  const filterMyBtn = document.getElementById("filterMyAgentsBtn");
  if (filterAllBtn && filterMyBtn) {
    filterAllBtn.addEventListener("click", () => {
      agentScopeFilter = "all";
      filterAllBtn.classList.add("bg-slate-800", "text-white", "shadow-sm");
      filterAllBtn.classList.remove("text-slate-400");
      filterMyBtn.classList.remove("bg-slate-800", "text-white", "shadow-sm");
      filterMyBtn.classList.add("text-slate-400");
      renderAgentsDirectory();
    });
    filterMyBtn.addEventListener("click", () => {
      agentScopeFilter = "mine";
      filterMyBtn.classList.add("bg-slate-800", "text-white", "shadow-sm");
      filterMyBtn.classList.remove("text-slate-400");
      filterAllBtn.classList.remove("bg-slate-800", "text-white", "shadow-sm");
      filterAllBtn.classList.add("text-slate-400");
      renderAgentsDirectory();
    });
  }

  // Create Agent Modal Listeners
  const openCreateModalBtn = document.getElementById("openCreateAgentModalBtn");
  const closeCreateModalBtn = document.getElementById("closeCreateAgentModalBtn");
  const createModal = document.getElementById("createAgentModal");
  if (openCreateModalBtn && createModal) {
    openCreateModalBtn.addEventListener("click", () => {
      createModal.classList.remove("hidden");
      setCreateModalTab("swagger");
    });
  }
  if (closeCreateModalBtn && createModal) {
    closeCreateModalBtn.addEventListener("click", () => {
      createModal.classList.add("hidden");
    });
  }

  // Modal Tab Switching
  document.getElementById("modalTabSwaggerBtn")?.addEventListener("click", () => setCreateModalTab("swagger"));
  document.getElementById("modalTabManifestBtn")?.addEventListener("click", () => setCreateModalTab("manifest"));
  document.getElementById("modalTabGuideBtn")?.addEventListener("click", () => setCreateModalTab("guide"));

  // Swagger Public Checkbox toggle
  const modalSwaggerPublicCheck = document.getElementById("modalSwaggerIsPublic");
  const modalSwaggerRestrictedSec = document.getElementById("modalSwaggerRestrictedSection");
  if (modalSwaggerPublicCheck && modalSwaggerRestrictedSec) {
    modalSwaggerPublicCheck.addEventListener("change", (e) => {
      if (e.target.checked) modalSwaggerRestrictedSec.classList.add("hidden");
      else modalSwaggerRestrictedSec.classList.remove("hidden");
    });
  }

  // Swagger Quick Samples in Modal
  document.getElementById("modalSampleDevOpsBtn")?.addEventListener("click", () => {
    fetch("/api/sample-specs").then(r => r.json()).then(res => {
      document.getElementById("modalSwaggerSpecInput").value = res.devops_sample || "";
      document.getElementById("modalSwaggerAgentName").value = "DevOps & Incident Manager";
      document.getElementById("modalSwaggerOwnerTeam").value = "Engineering";
      document.getElementById("modalSwaggerIconSelect").value = "wrench";
    });
  });
  document.getElementById("modalSampleFinanceBtn")?.addEventListener("click", () => {
    fetch("/api/sample-specs").then(r => r.json()).then(res => {
      document.getElementById("modalSwaggerSpecInput").value = res.finance_sample || "";
      document.getElementById("modalSwaggerAgentName").value = "ERP & Vendor Payment Agent";
      document.getElementById("modalSwaggerOwnerTeam").value = "Finance";
      document.getElementById("modalSwaggerIconSelect").value = "cart";
    });
  });

  // Submit Swagger Generate Agent & Tools
  document.getElementById("modalSubmitSwaggerBtn")?.addEventListener("click", handleModalSwaggerSubmit);

  // Access Limits Modal Listeners
  document.getElementById("closeAgentAccessModalBtn")?.addEventListener("click", () => {
    document.getElementById("agentAccessModal").classList.add("hidden");
  });
  document.getElementById("cancelEditAccessBtn")?.addEventListener("click", () => {
    document.getElementById("agentAccessModal").classList.add("hidden");
  });
  document.getElementById("editAccessIsPublic")?.addEventListener("change", (e) => {
    const area = document.getElementById("editAccessRestrictedArea");
    if (e.target.checked) area.classList.add("hidden");
    else area.classList.remove("hidden");
  });
  document.getElementById("saveEditAccessBtn")?.addEventListener("click", handleSaveAgentAccess);

  // Onboarding Form
  document.getElementById("onboardForm").addEventListener("submit", handleOnboardSubmit);
  document.getElementById("fillSampleAgentBtn").addEventListener("click", fillSampleAgent);
  document.getElementById("agentTypeSelect").addEventListener("change", (e) => {
    const row = document.getElementById("remoteEndpointRow");
    if (e.target.value === "remote_a2a") {
      row.classList.remove("hidden");
    } else {
      row.classList.add("hidden");
    }
  });

  // Swagger Importer
  document.getElementById("loadDevOpsSpecBtn").addEventListener("click", loadDevOpsSampleSpec);
  document.getElementById("loadFinanceSpecBtn").addEventListener("click", loadFinanceSampleSpec);
  document.getElementById("importSwaggerBtn").addEventListener("click", handleSwaggerImport);

  // RAG Upload
  document.getElementById("ragUploadForm").addEventListener("submit", handleRagUpload);

  // Audit Logs
  document.getElementById("refreshLogsBtn").addEventListener("click", loadAuditLogs);
  document.getElementById("auditFilterSelect").addEventListener("change", loadAuditLogs);
  document.getElementById("clearLogsBtn").addEventListener("click", async () => {
    await fetch("/api/audit/clear", { method: "POST" });
    await loadAuditLogs();
  });
}

// ----------------- Identity & Personas -----------------

async function loadPersonas() {
  try {
    const res = await fetch("/api/personas");
    const data = await res.json();
    personasData = data.personas;
    if (personasData[currentPersona]) {
      currentJwtToken = personasData[currentPersona].jwt;
    }
  } catch (err) {
    console.error("Failed to load personas:", err);
  }
}

function showJwtModal() {
  const p = personasData[currentPersona];
  if (!p) return;
  document.getElementById("jwtDecodedContent").innerText = JSON.stringify(p.user, null, 2);
  document.getElementById("jwtRawContent").innerText = p.jwt;
  document.getElementById("jwtModal").classList.remove("hidden");
}

// ----------------- Chat & Orchestration -----------------

async function handleChatSubmit(e) {
  e.preventDefault();
  const input = document.getElementById("chatInput");
  const prompt = input.value.trim();
  if (!prompt) return;

  input.value = "";
  appendUserMessage(prompt);

  const sendBtn = document.getElementById("sendBtn");
  sendBtn.disabled = true;

  // Add typing indicator
  const typingId = appendTypingIndicator();

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        prompt: prompt,
        persona: currentPersona,
        token: currentJwtToken
      })
    });

    const data = await res.json();
    removeMessage(typingId);
    renderOrchestratorResponse(data);
  } catch (err) {
    removeMessage(typingId);
    appendSystemNotice(`Error executing request: ${err.message}`, "error");
  } finally {
    sendBtn.disabled = false;
    loadAuditLogs();
  }
}

function appendUserMessage(text) {
  const chatHistory = document.getElementById("chatHistory");
  const msgEl = document.createElement("div");
  msgEl.className = "flex items-start justify-end gap-3 animate-fade-in";
  msgEl.innerHTML = `
    <div class="max-w-2xl bg-indigo-600/90 text-white rounded-2xl rounded-tr-sm px-4 py-3 text-sm shadow-md">
      <div class="flex items-center gap-1.5 mb-1 text-[11px] text-indigo-200">
        <i data-lucide="user" class="w-3 h-3"></i>
        <span>${personasData[currentPersona]?.user?.name || currentPersona}</span>
      </div>
      <p class="leading-relaxed">${escapeHtml(text)}</p>
    </div>
    <div class="w-8 h-8 rounded-lg bg-indigo-500 flex items-center justify-center flex-shrink-0 text-white text-xs font-bold">
      ${(personasData[currentPersona]?.user?.name || "U")[0]}
    </div>
  `;
  chatHistory.appendChild(msgEl);
  if (window.lucide) window.lucide.createIcons();
  chatHistory.scrollTop = chatHistory.scrollHeight;
}

function appendTypingIndicator() {
  const chatHistory = document.getElementById("chatHistory");
  const id = "typing-" + Date.now();
  const msgEl = document.createElement("div");
  msgEl.id = id;
  msgEl.className = "flex items-start gap-3.5 animate-fade-in";
  msgEl.innerHTML = `
    <div class="w-8 h-8 rounded-lg bg-indigo-600/80 flex items-center justify-center flex-shrink-0 text-white animate-pulse">
      <i data-lucide="cpu" class="w-4 h-4"></i>
    </div>
    <div class="bg-slate-800/80 border border-slate-700/60 rounded-2xl px-4 py-3 text-xs text-slate-400 flex items-center gap-2">
      <span class="inline-block w-2 h-2 rounded-full bg-indigo-400 animate-ping"></span>
      <span>Gemini Router analyzing prompt & checking ADK policies...</span>
    </div>
  `;
  chatHistory.appendChild(msgEl);
  if (window.lucide) window.lucide.createIcons();
  chatHistory.scrollTop = chatHistory.scrollHeight;
  return id;
}

function removeMessage(id) {
  const el = document.getElementById(id);
  if (el) el.remove();
}

function renderOrchestratorResponse(data) {
  const chatHistory = document.getElementById("chatHistory");
  const msgEl = document.createElement("div");
  msgEl.className = "flex items-start gap-3.5 animate-fade-in";

  const routing = data.routing || {};
  const agent = data.agent_info;
  const policy = data.policy_decision || {};
  const conf = data.pending_confirmation;
  const isDenial = data.action_taken === "POLICY_DENIED" || data.action_taken === "POLICY_BLOCKED";

  // Build telemetry pills
  let pillsHtml = "";
  if (routing.selected_agent_id) {
    pillsHtml += `
      <span class="inline-flex items-center gap-1 bg-indigo-950/80 text-indigo-300 border border-indigo-800/60 px-2 py-0.5 rounded-full text-[10px]">
        <i data-lucide="bot" class="w-3 h-3"></i>
        ${agent?.name || routing.selected_agent_id} (${Math.round((routing.confidence || 0.9) * 100)}%)
      </span>
    `;
  }
  if (routing.intent) {
    const intentColor = routing.intent === "tool_call" ? "bg-amber-950/80 text-amber-300 border-amber-800/60" : "bg-sky-950/80 text-sky-300 border-sky-800/60";
    pillsHtml += `
      <span class="inline-flex items-center gap-1 ${intentColor} border px-2 py-0.5 rounded-full text-[10px]">
        <i data-lucide="zap" class="w-3 h-3"></i>
        Intent: ${routing.intent}
      </span>
    `;
  }
  if (data.trace_id) {
    pillsHtml += `
      <span class="inline-flex items-center gap-1 bg-slate-900 text-slate-400 border border-slate-800 px-2 py-0.5 rounded-full text-[10px] font-mono">
        Trace: ${data.trace_id.slice(0, 8)}
      </span>
    `;
  }

  // Confirmation card if write operation pending
  let confirmationHtml = "";
  if (conf) {
    confirmationHtml = `
      <div class="mt-3 p-3.5 rounded-xl bg-amber-950/40 border border-amber-600/50 text-amber-200">
        <div class="flex items-center gap-2 font-semibold text-xs mb-1">
          <i data-lucide="alert-triangle" class="w-4 h-4 text-amber-400"></i>
          Human Write Confirmation Required
        </div>
        <p class="text-xs text-amber-300/90 mb-2">
          Executing this tool mutates production state. Under the ADK security policy, human authorization is required.
        </p>
        <div class="bg-slate-950/70 p-2.5 rounded-lg border border-slate-800 font-mono text-[11px] mb-3 text-slate-300">
          <strong>Tool:</strong> ${conf.tool_name}<br>
          <strong>Parameters:</strong> ${JSON.stringify(conf.parameters)}
        </div>
        <div class="flex gap-2">
          <button onclick="confirmAction('${conf.confirmation_id}', 'approve')" class="bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-xs px-3.5 py-1.5 rounded-lg flex items-center gap-1.5 transition">
            <i data-lucide="check" class="w-3.5 h-3.5"></i> Approve & Execute
          </button>
          <button onclick="confirmAction('${conf.confirmation_id}', 'reject')" class="bg-rose-900/60 hover:bg-rose-900 text-rose-300 text-xs px-3 py-1.5 rounded-lg border border-rose-800 flex items-center gap-1.5 transition">
            <i data-lucide="x" class="w-3.5 h-3.5"></i> Reject
          </button>
        </div>
      </div>
    `;
  }

  // Gateway context pill
  let gatewayHtml = "";
  if (data.gateway_context) {
    gatewayHtml = `
      <div class="mt-2 pt-2 border-t border-slate-700/60 flex items-center justify-between text-[11px] text-slate-400">
        <span class="flex items-center gap-1">
          <i data-lucide="lock" class="w-3 h-3 text-emerald-400"></i>
          Gateway SA: <code class="text-slate-300 font-mono">${data.gateway_context.service_account}</code>
        </span>
        <span>${data.duration_ms || 0}ms</span>
      </div>
    `;
  }

  const borderClass = isDenial ? "border-rose-700/80 bg-rose-950/20" : "border-slate-700/70 bg-slate-800/80";

  msgEl.innerHTML = `
    <div class="w-8 h-8 rounded-lg ${isDenial ? 'bg-rose-600' : 'bg-indigo-600'} flex items-center justify-center flex-shrink-0 text-white shadow">
      <i data-lucide="${isDenial ? 'shield-alert' : 'bot'}" class="w-4 h-4"></i>
    </div>
    <div class="flex-1 max-w-3xl ${borderClass} border rounded-2xl rounded-tl-sm p-4 text-sm text-slate-200">
      <div class="flex flex-wrap items-center gap-1.5 mb-2.5">
        ${pillsHtml}
      </div>
      <div class="prose prose-invert prose-sm max-w-none leading-relaxed text-slate-200">
        ${formatMarkdown(data.reply || "")}
      </div>
      ${confirmationHtml}
      ${gatewayHtml}
    </div>
  `;

  chatHistory.appendChild(msgEl);
  if (window.lucide) window.lucide.createIcons();
  chatHistory.scrollTop = chatHistory.scrollHeight;
}

async function confirmAction(confirmationId, action) {
  try {
    const res = await fetch("/api/chat/confirm", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        confirmation_id: confirmationId,
        action: action,
        persona: currentPersona
      })
    });
    const data = await res.json();
    renderOrchestratorResponse(data);
    loadAuditLogs();
  } catch (err) {
    appendSystemNotice(`Confirmation error: ${err.message}`, "error");
  }
}

function appendSystemNotice(text, type = "info") {
  const chatHistory = document.getElementById("chatHistory");
  const el = document.createElement("div");
  el.className = "flex justify-center text-xs text-slate-400 py-1 animate-fade-in";
  el.innerHTML = `<span class="bg-slate-900 border border-slate-800 px-3 py-1 rounded-full">${text}</span>`;
  chatHistory.appendChild(el);
  chatHistory.scrollTop = chatHistory.scrollHeight;
}

// ----------------- Agent Directory & Hub -----------------

async function loadAgents() {
  try {
    const res = await fetch("/api/agents");
    const data = await res.json();
    allAgentsList = data.agents || [];

    const badge = document.getElementById("agentsBadge");
    if (badge) badge.innerText = allAgentsList.length;

    // Populate dropdown in Swagger tab
    const select = document.getElementById("swaggerTargetAgent");
    if (select) {
      select.innerHTML = '<option value="">-- No specific agent (Global Registry) --</option>';
      allAgentsList.forEach(a => {
        const opt = document.createElement("option");
        opt.value = a.id;
        opt.innerText = `${a.name} (${a.owner_team})`;
        select.appendChild(opt);
      });
    }

    renderAgentsDirectory();
  } catch (err) {
    console.error("Error loading agents:", err);
  }
}

function renderAgentsDirectory() {
  const container = document.getElementById("agentsDirectoryGrid");
  if (!container) return;

  const currentPersonaData = personasData[currentPersona]?.user;
  const userSub = currentPersonaData?.sub;
  const userTeam = currentPersonaData?.team;
  const allowedAgentIds = currentPersonaData?.allowed_agent_ids || ["*"];

  // Calculate my agents count
  const myCount = allAgentsList.filter(agent => {
    const isAuthor = agent.author_id === userSub || (agent.author && agent.author.toLowerCase().includes(currentPersonaData?.name.toLowerCase()));
    const isMyTeam = userTeam && agent.owner_team.toLowerCase() === userTeam.toLowerCase();
    const isAssigned = allowedAgentIds.includes("*") || allowedAgentIds.includes(agent.id);
    return isAuthor || isMyTeam || isAssigned;
  }).length;

  const myBadge = document.getElementById("myAgentsCountBadge");
  if (myBadge) myBadge.innerText = myCount;

  // Filter agents based on scope and search
  const filtered = allAgentsList.filter(agent => {
    if (agentScopeFilter === "mine") {
      const isAuthor = agent.author_id === userSub || (agent.author && agent.author.toLowerCase().includes(currentPersonaData?.name.toLowerCase()));
      const isMyTeam = userTeam && agent.owner_team.toLowerCase() === userTeam.toLowerCase();
      const isAssigned = allowedAgentIds.includes("*") || allowedAgentIds.includes(agent.id);
      if (!isAuthor && !isMyTeam && !isAssigned) return false;
    }
    if (!agentSearchQuery) return true;
    const q = agentSearchQuery.toLowerCase();
    return (
      agent.name.toLowerCase().includes(q) ||
      agent.description.toLowerCase().includes(q) ||
      agent.owner_team.toLowerCase().includes(q) ||
      (agent.author && agent.author.toLowerCase().includes(q)) ||
      agent.allowed_tools.some(t => t.toLowerCase().includes(q))
    );
  });

  container.innerHTML = "";

  if (filtered.length === 0) {
    container.innerHTML = `
      <div class="col-span-1 md:col-span-2 bg-slate-900/40 border border-slate-800/80 rounded-2xl p-12 text-center max-w-md mx-auto space-y-3">
        <span class="text-4xl block">🔍</span>
        <h3 class="text-base font-semibold text-white">No agents found</h3>
        <p class="text-xs text-slate-400">
          No agents match your query "${escapeHtml(agentSearchQuery)}" in ${agentScopeFilter === 'mine' ? 'Your agents' : 'All agents'}.
        </p>
      </div>
    `;
    return;
  }

  filtered.forEach(agent => {
    const card = document.createElement("div");
    card.className = "bg-slate-900/80 border border-slate-800 hover:border-slate-700 rounded-2xl p-5 flex flex-col justify-between transition group shadow-sm";
    const isRemote = agent.agent_type === "remote_a2a";

    const badgeIconClass = getAgentBadgeClass(agent.icon, agent.owner_team);
    const iconSymbol = getAgentIconSymbol(agent.icon, agent.owner_team);

    card.innerHTML = `
      <div>
        <div class="flex items-start justify-between gap-3 mb-3">
          <div class="${badgeIconClass} w-10 h-10 rounded-xl flex items-center justify-center text-lg flex-shrink-0 shadow-inner">
            <span>${iconSymbol}</span>
          </div>
          <div class="flex items-center gap-1.5 flex-wrap justify-end">
            <span class="${agent.is_public !== false ? 'bg-slate-800 text-slate-300 border-slate-700/60' : 'bg-amber-950 text-amber-300 border-amber-800/60'} border text-[10px] px-2 py-0.5 rounded-full">
              ${agent.is_public !== false ? 'Public' : 'Restricted'}
            </span>
            <span class="text-[10px] px-2 py-0.5 rounded-full font-mono border ${isRemote ? 'bg-sky-950 text-sky-300 border-sky-800' : 'bg-indigo-950 text-indigo-300 border-indigo-800'}">
              ${isRemote ? 'Remote A2A' : 'ADK Agent'}
            </span>
          </div>
        </div>

        <h3 class="text-base font-bold text-white group-hover:text-indigo-300 transition-colors">
          ${escapeHtml(agent.name)}
        </h3>

        <div class="text-xs text-slate-400 mt-0.5 mb-2.5 flex items-center gap-1.5 flex-wrap">
          <span>by</span>
          <a href="javascript:void(0)" onclick="filterByAuthor('${escapeHtml(agent.author || agent.owner_team)}')" class="text-blue-400 hover:text-blue-300 hover:underline inline-flex items-center gap-0.5">
            <span>${escapeHtml(agent.author || agent.owner_team)}</span>
            <span class="text-[10px]">↗</span>
          </a>
          ${!agent.active ? '<span class="text-slate-500 font-normal">(deactivated)</span>' : ''}
        </div>

        <p class="text-xs text-slate-300 leading-relaxed line-clamp-3 mb-4">
          ${escapeHtml(agent.description)}
        </p>
      </div>

      <div class="pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-400">
        <div class="flex items-center gap-2 text-[11px] font-mono">
          <span class="bg-slate-800/80 px-2 py-0.5 rounded text-slate-300">
            Team: <strong>${escapeHtml(agent.owner_team)}</strong>
          </span>
          <span class="bg-slate-800/80 px-2 py-0.5 rounded text-slate-300">
            Tools: <strong>${agent.allowed_tools.length}</strong>
          </span>
        </div>

        <div class="flex items-center gap-2">
          <button onclick="openAgentAccessModal('${agent.id}')" class="text-[11px] text-slate-400 hover:text-white bg-slate-800 hover:bg-slate-700 px-2 py-1 rounded-lg transition cursor-pointer" title="Manage Access Limits and Roles">
            ⚙️ Limits
          </button>
          <button onclick="toggleAgentActive('${agent.id}')" class="text-[11px] text-slate-400 hover:text-white bg-slate-800 hover:bg-slate-700 px-2 py-1 rounded-lg transition cursor-pointer">
            ${agent.active ? 'Deactivate' : 'Activate'}
          </button>
          <button onclick="chatWithAgent('${agent.id}')" class="text-[11px] bg-indigo-600 hover:bg-indigo-500 text-white font-medium px-2.5 py-1 rounded-lg transition cursor-pointer shadow-sm">
            💬 Chat
          </button>
        </div>
      </div>
    `;

    container.appendChild(card);
  });
  if (window.lucide) window.lucide.createIcons();
}

function filterByAuthor(authorName) {
  const searchInput = document.getElementById("agentSearchInput");
  if (searchInput) {
    searchInput.value = authorName;
    agentSearchQuery = authorName;
    const clearBtn = document.getElementById("clearAgentSearchBtn");
    if (clearBtn) clearBtn.classList.remove("hidden");
    renderAgentsDirectory();
  }
}

function chatWithAgent(agentId) {
  const agent = allAgentsList.find(a => a.id === agentId);
  if (!agent) return;

  // Switch to Chat tab
  const chatTabBtn = document.getElementById("tabChatBtn");
  if (chatTabBtn) chatTabBtn.click();

  const chatInput = document.getElementById("chatInput");
  if (chatInput) {
    chatInput.value = `Ask ${agent.name}: `;
    chatInput.focus();
  }
}

function setCreateModalTab(tab) {
  const tabs = ["swagger", "manifest", "guide"];
  tabs.forEach(t => {
    const btn = document.getElementById(`modalTab${t.charAt(0).toUpperCase() + t.slice(1)}Btn`);
    const content = document.getElementById(`modalContent${t.charAt(0).toUpperCase() + t.slice(1)}`);
    if (t === tab) {
      btn?.classList.add("text-indigo-400", "border-b-2", "border-indigo-500", "font-bold");
      btn?.classList.remove("text-slate-400");
      content?.classList.remove("hidden");
    } else {
      btn?.classList.remove("text-indigo-400", "border-b-2", "border-indigo-500", "font-bold");
      btn?.classList.add("text-slate-400");
      content?.classList.add("hidden");
    }
  });
  if (window.lucide) window.lucide.createIcons();
}

async function handleModalSwaggerSubmit() {
  const specContent = document.getElementById("modalSwaggerSpecInput").value.trim();
  if (!specContent) {
    alert("Please provide an OpenAPI or Swagger specification.");
    return;
  }

  const agentName = document.getElementById("modalSwaggerAgentName").value.trim();
  const ownerTeam = document.getElementById("modalSwaggerOwnerTeam").value.trim() || "Engineering";
  const icon = document.getElementById("modalSwaggerIconSelect").value || "wrench";
  const isPublic = document.getElementById("modalSwaggerIsPublic").checked;

  let roles = ["*"];
  if (!isPublic) {
    const selected = [];
    document.querySelectorAll(".modal-swagger-role:checked").forEach(cb => selected.push(cb.value));
    roles = selected.length > 0 ? selected : ["*"];
  }

  const teamsInput = document.getElementById("modalSwaggerAllowedTeams").value.trim();
  const allowedTeams = teamsInput ? teamsInput.split(",").map(s => s.trim()).filter(Boolean) : ["*"];

  const currentPersonaUser = personasData[currentPersona]?.user;

  const payload = {
    spec_content: specContent,
    agent_name: agentName || undefined,
    owner_team: ownerTeam,
    author: currentPersonaUser?.name || "Enterprise User",
    author_id: currentPersonaUser?.sub || "user",
    icon: icon,
    is_public: isPublic,
    allowed_roles: roles,
    allowed_teams: isPublic ? ["*"] : allowedTeams,
    auto_register: true
  };

  const btn = document.getElementById("modalSubmitSwaggerBtn");
  btn.disabled = true;
  btn.innerText = "Generating Agent & Tools...";

  try {
    const res = await fetch("/api/agents/generate-from-swagger", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Failed to generate agent");

    alert(`Success! Generated agent '${data.agent.name}' with ${data.tools.length} ADK tools.`);
    document.getElementById("createAgentModal").classList.add("hidden");
    await loadAgents();
    await loadTools();
    await loadAuditLogs();
  } catch (err) {
    alert(`Swagger generation error: ${err.message}`);
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<i data-lucide="zap" class="w-4 h-4"></i><span>Generate Agent & Register Tools</span>';
    if (window.lucide) window.lucide.createIcons();
  }
}

function openAgentAccessModal(agentId) {
  const agent = allAgentsList.find(a => a.id === agentId);
  if (!agent) return;
  currentEditingAgent = agent;

  document.getElementById("editAccessModalTitle").innerText = `Access Limits: ${agent.name}`;
  const isPublicCheck = document.getElementById("editAccessIsPublic");
  isPublicCheck.checked = agent.is_public !== false;

  const restrictedArea = document.getElementById("editAccessRestrictedArea");
  if (isPublicCheck.checked) restrictedArea.classList.add("hidden");
  else restrictedArea.classList.remove("hidden");

  const allowedRoles = agent.allowed_roles || ["*"];
  document.querySelectorAll(".edit-role-check").forEach(cb => {
    cb.checked = allowedRoles.includes(cb.value);
  });

  const teams = (agent.allowed_teams || []).filter(t => t !== "*").join(", ");
  document.getElementById("editAccessTeamsInput").value = teams;

  document.getElementById("agentAccessModal").classList.remove("hidden");
}

async function handleSaveAgentAccess() {
  if (!currentEditingAgent) return;

  const isPublic = document.getElementById("editAccessIsPublic").checked;
  let roles = ["*"];
  if (!isPublic) {
    const selected = [];
    document.querySelectorAll(".edit-role-check:checked").forEach(cb => selected.push(cb.value));
    roles = selected.length > 0 ? selected : ["*"];
  }

  const teamsInput = document.getElementById("editAccessTeamsInput").value.trim();
  const allowedTeams = teamsInput ? teamsInput.split(",").map(s => s.trim()).filter(Boolean) : ["*"];

  const payload = {
    is_public: isPublic,
    allowed_roles: roles,
    allowed_teams: isPublic ? ["*"] : allowedTeams
  };

  try {
    const res = await fetch(`/api/agents/${currentEditingAgent.id}/access`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Failed to update access");

    alert(`Access limits updated for '${currentEditingAgent.name}'.`);
    document.getElementById("agentAccessModal").classList.add("hidden");
    await loadAgents();
  } catch (err) {
    alert(`Update error: ${err.message}`);
  }
}

function getAgentIconSymbol(icon, team) {
  switch (icon) {
    case 'wrench': return '🔧';
    case 'chart': return '📊';
    case 'shield': return '🛡️';
    case 'docs': return '📄';
    case 'cart': return '🛒';
    case 'user': return '👤';
    case 'bot': return '🤖';
    case 'code': return '💻';
    default:
      if (team?.toLowerCase().includes('it') || team?.toLowerCase().includes('engineer')) return '🔧';
      if (team?.toLowerCase().includes('hr') || team?.toLowerCase().includes('people')) return '👤';
      if (team?.toLowerCase().includes('finance')) return '🛒';
      return '🤖';
  }
}

function getAgentBadgeClass(icon, team) {
  switch (icon) {
    case 'chart': return 'bg-emerald-950/80 text-emerald-400 border border-emerald-800/60';
    case 'docs': return 'bg-emerald-950/80 text-emerald-400 border border-emerald-800/60';
    case 'shield': return 'bg-sky-950/80 text-sky-400 border border-sky-800/60';
    case 'cart': return 'bg-emerald-950/80 text-emerald-400 border border-emerald-800/60';
    case 'user': return 'bg-blue-950/80 text-blue-400 border border-blue-800/60';
    case 'wrench': return 'bg-emerald-950/80 text-emerald-400 border border-emerald-800/60';
    default: return 'bg-indigo-950/80 text-indigo-400 border border-indigo-800/60';
  }
}

async function handleOnboardSubmit(e) {
  e.preventDefault();
  const manifest = {
    id: document.getElementById("agentIdInput").value.trim(),
    name: document.getElementById("agentNameInput").value.trim(),
    owner_team: document.getElementById("agentTeamInput").value.trim(),
    agent_type: document.getElementById("agentTypeSelect").value,
    remote_endpoint: document.getElementById("agentEndpointInput").value.trim() || null,
    description: document.getElementById("agentDescInput").value.trim(),
    system_prompt: document.getElementById("agentPromptInput").value.trim(),
    allowed_tools: document.getElementById("agentToolsInput").value.split(",").map(s => s.trim()).filter(Boolean),
    knowledge_scopes: document.getElementById("agentScopesInput").value.split(",").map(s => s.trim()).filter(Boolean),
    active: true
  };

  try {
    const res = await fetch("/api/agents/onboard", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(manifest)
    });
    const data = await res.json();
    alert(`Agent '${manifest.name}' onboarded successfully!`);
    document.getElementById("onboardForm").reset();
    await loadAgents();
    await loadAuditLogs();
  } catch (err) {
    alert(`Failed to onboard agent: ${err.message}`);
  }
}

function fillSampleAgent() {
  document.getElementById("agentIdInput").value = "marketing_growth_agent";
  document.getElementById("agentNameInput").value = "Marketing & Brand Growth Agent";
  document.getElementById("agentTeamInput").value = "Marketing";
  document.getElementById("agentTypeSelect").value = "local_adk";
  document.getElementById("agentDescInput").value = "Handles marketing campaigns, brand identity standards, social media copy reviews, and growth analytics.";
  document.getElementById("agentPromptInput").value = "You are the Marketing Growth Agent. Advise team members on branding, messaging, and campaign metrics.";
  document.getElementById("agentToolsInput").value = "get_system_health";
  document.getElementById("agentScopesInput").value = "marketing_guidelines";
}

async function toggleAgentActive(agentId) {
  try {
    await fetch(`/api/agents/${agentId}/toggle`, { method: "POST" });
    await loadAgents();
    await loadAuditLogs();
  } catch (err) {
    console.error(err);
  }
}

// ----------------- Swagger / OpenAPI Importer -----------------

async function loadTools() {
  try {
    const res = await fetch("/api/tools");
    const data = await res.json();
    const tools = data.tools || [];

    document.getElementById("toolsBadge").innerText = tools.length;
    document.getElementById("toolsCount").innerText = `${tools.length} tools registered`;

    const container = document.getElementById("toolsListContainer");
    container.innerHTML = "";
    tools.forEach(tool => {
      const card = document.createElement("div");
      card.className = "p-3 rounded-xl bg-slate-800/70 border border-slate-700/80 text-xs space-y-1.5 hover:border-slate-600 transition";
      const isWrite = tool.is_write;
      const methodColor = tool.method === "GET" ? "bg-emerald-950 text-emerald-300 border-emerald-800" :
                         tool.method === "POST" ? "bg-amber-950 text-amber-300 border-amber-800" :
                         tool.method === "DELETE" ? "bg-rose-950 text-rose-300 border-rose-800" : "bg-sky-950 text-sky-300 border-sky-800";

      card.innerHTML = `
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <span class="px-2 py-0.5 rounded font-mono font-bold text-[10px] border ${methodColor}">${tool.method}</span>
            <span class="font-mono font-semibold text-white text-xs">${tool.name}</span>
          </div>
          <div class="flex items-center gap-1.5">
            ${isWrite ? '<span class="bg-amber-950/80 text-amber-300 border border-amber-800/60 px-1.5 py-0.5 rounded text-[10px]">Write (Confirmation)</span>' : '<span class="bg-emerald-950/80 text-emerald-300 border border-emerald-800/60 px-1.5 py-0.5 rounded text-[10px]">Read-Only</span>'}
          </div>
        </div>
        <p class="text-slate-300 text-[11px] leading-tight">${escapeHtml(tool.description)}</p>
        <div class="flex items-center justify-between text-[10px] text-slate-400 font-mono pt-1 border-t border-slate-700/50">
          <span>Path: ${tool.path}</span>
          <span>Agent: ${tool.owner_agent || 'Global'}</span>
        </div>
      `;
      container.appendChild(card);
    });
  } catch (err) {
    console.error("Error loading tools:", err);
  }
}

async function loadDevOpsSampleSpec() {
  const res = await fetch("/api/sample-specs");
  const data = await res.json();
  document.getElementById("swaggerSpecInput").value = data.devops_sample;
  document.getElementById("swaggerTargetAgent").value = "it_agent";
}

async function loadFinanceSampleSpec() {
  const res = await fetch("/api/sample-specs");
  const data = await res.json();
  document.getElementById("swaggerSpecInput").value = data.finance_sample;
  document.getElementById("swaggerTargetAgent").value = "finance_agent";
}

async function handleSwaggerImport() {
  const spec = document.getElementById("swaggerSpecInput").value.trim();
  const agentId = document.getElementById("swaggerTargetAgent").value || null;
  if (!spec) {
    alert("Please enter or load an OpenAPI spec first.");
    return;
  }

  try {
    const res = await fetch("/api/tools/import-swagger", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        spec_content: spec,
        target_agent_id: agentId
      })
    });
    const data = await res.json();
    if (res.ok) {
      alert(`Success! Imported ${data.imported_tools.length} ADK tools into the registry.`);
      await loadTools();
      await loadAgents();
      await loadAuditLogs();
    } else {
      alert(`Error: ${data.detail}`);
    }
  } catch (err) {
    alert(`Import failed: ${err.message}`);
  }
}

// ----------------- RAG Knowledge Stores -----------------

async function loadKnowledgeDocs() {
  try {
    const res = await fetch("/api/knowledge/documents");
    const data = await res.json();
    const docs = data.documents || [];

    const container = document.getElementById("ragDocsContainer");
    container.innerHTML = "";

    docs.forEach(doc => {
      const card = document.createElement("div");
      card.className = "p-4 rounded-xl bg-slate-800/70 border border-slate-700/80 text-xs space-y-2 hover:border-slate-600 transition";
      card.innerHTML = `
        <div class="flex items-center justify-between">
          <span class="font-bold text-white text-sm flex items-center gap-2">
            <i data-lucide="file-text" class="w-4 h-4 text-indigo-400"></i>
            ${escapeHtml(doc.title)}
          </span>
          <span class="bg-indigo-950 text-indigo-300 border border-indigo-800 px-2.5 py-0.5 rounded-full text-[10px] font-mono">
            Scope: ${doc.scope}
          </span>
        </div>
        <p class="text-slate-300 leading-relaxed font-sans text-xs bg-slate-900/60 p-2.5 rounded-lg border border-slate-800/80 whitespace-pre-line">${escapeHtml(doc.content)}</p>
        <div class="flex items-center justify-between text-[10px] text-slate-400">
          <span>Ingest Method: <strong>${doc.source_type}</strong></span>
          <span>Team: <strong>${doc.author_team}</strong></span>
        </div>
      `;
      container.appendChild(card);
    });
    if (window.lucide) window.lucide.createIcons();
  } catch (err) {
    console.error("Error loading knowledge docs:", err);
  }
}

async function handleRagUpload(e) {
  e.preventDefault();
  const payload = {
    title: document.getElementById("docTitleInput").value.trim(),
    scope: document.getElementById("docScopeInput").value.trim(),
    content: document.getElementById("docContentInput").value.trim(),
    source_type: "document_ai_pdf"
  };

  try {
    const res = await fetch("/api/knowledge/upload", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    alert(`Document '${payload.title}' ingested into scope '${payload.scope}'!`);
    document.getElementById("ragUploadForm").reset();
    await loadKnowledgeDocs();
    await loadAuditLogs();
  } catch (err) {
    alert(`Failed to ingest document: ${err.message}`);
  }
}

// ----------------- Observability & Audit Trail -----------------

async function loadAuditLogs() {
  const filter = document.getElementById("auditFilterSelect")?.value || "";
  try {
    const url = filter ? `/api/audit/logs?event_type=${filter}&limit=60` : `/api/audit/logs?limit=60`;
    const res = await fetch(url);
    const data = await res.json();
    const logs = data.logs || [];

    const container = document.getElementById("auditLogsContainer");
    if (!container) return;

    if (logs.length === 0) {
      container.innerHTML = '<div class="text-slate-500 text-center py-8">No audit logs recorded yet.</div>';
      return;
    }

    container.innerHTML = "";
    logs.forEach(log => {
      const item = document.createElement("div");
      item.className = "p-2.5 rounded-xl bg-slate-950/70 border border-slate-800 text-[11px] font-mono space-y-1 hover:border-slate-700 transition";

      const sevColor = log.severity === "WARNING" || log.severity === "ERROR" ? "text-rose-400 bg-rose-950/60 border-rose-800" :
                       log.severity === "NOTICE" ? "text-amber-400 bg-amber-950/60 border-amber-800" : "text-sky-400 bg-sky-950/60 border-sky-800";

      const timeStr = new Date(log.timestamp).toLocaleTimeString();

      item.innerHTML = `
        <div class="flex items-center justify-between text-[10px]">
          <div class="flex items-center gap-2">
            <span class="text-slate-500">${timeStr}</span>
            <span class="px-1.5 py-0.2 rounded border ${sevColor} font-semibold">${log.severity}</span>
            <span class="text-indigo-400 font-bold">${log.event_type}</span>
          </div>
          <span class="text-slate-500">Trace: ${log.trace_id?.slice(0, 8)}</span>
        </div>
        <p class="text-slate-200">${escapeHtml(log.message)}</p>
        <details class="text-slate-400 text-[10px] cursor-pointer">
          <summary class="text-slate-500 hover:text-slate-300">View Cloud Logging JSON Payload</summary>
          <pre class="bg-slate-900 p-2 mt-1 rounded border border-slate-800 text-emerald-400 overflow-x-auto">${JSON.stringify(log, null, 2)}</pre>
        </details>
      `;
      container.appendChild(item);
    });
  } catch (err) {
    console.error("Failed to load audit logs:", err);
  }
}

// ----------------- Helpers -----------------

function formatMarkdown(text) {
  if (!text) return "";
  let html = text
    .replace(/```json([\s\S]*?)```/g, '<pre class="bg-slate-950 p-3 rounded-lg border border-slate-800 font-mono text-emerald-400 my-2 text-xs overflow-x-auto">$1</pre>')
    .replace(/```([\s\S]*?)```/g, '<pre class="bg-slate-950 p-3 rounded-lg border border-slate-800 font-mono text-slate-300 my-2 text-xs overflow-x-auto">$1</pre>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/`([^`]+)`/g, '<code class="bg-slate-950 border border-slate-800 px-1 py-0.5 rounded text-amber-300 font-mono text-[11px]">$1</code>')
    .replace(/\n\n/g, '<br><br>')
    .replace(/\n/g, '<br>');
  return html;
}

function escapeHtml(text) {
  if (!text) return "";
  return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

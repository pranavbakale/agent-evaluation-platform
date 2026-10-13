const state = {
  tasks: [],
  runs: [],
  overview: null,
  selectedCategory: "All",
  selectedTask: null,
};

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail || `Request failed (${response.status})`);
  }
  return response.json();
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatValue(value) {
  const rendered = typeof value === "string" ? JSON.stringify(value) : JSON.stringify(value);
  return rendered === undefined ? String(value) : rendered;
}

function formatDuration(milliseconds) {
  return milliseconds >= 1000 ? `${(milliseconds / 1000).toFixed(2)}s` : `${Math.round(milliseconds)}ms`;
}

function relativeTime(iso) {
  const seconds = Math.max(0, Math.floor((Date.now() - new Date(iso).getTime()) / 1000));
  if (seconds < 60) return "just now";
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}

function showToast(message) {
  const toast = $("#toast");
  toast.textContent = message;
  toast.classList.add("show");
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => toast.classList.remove("show"), 2500);
}

function routeTo(route) {
  const validRoute = ["overview", "tasks", "runs", "validation"].includes(route) ? route : "overview";
  $$(".view").forEach((view) => view.classList.toggle("active", view.dataset.view === validRoute));
  $$(".nav-item").forEach((item) => item.classList.toggle("active", item.dataset.route === validRoute));
  const labels = { overview: "Overview", tasks: "Task library", runs: "Run history", validation: "Verifier quality" };
  $("#page-label").textContent = labels[validRoute];
  window.location.hash = validRoute;
  $(".sidebar").classList.remove("open");
  if (validRoute === "runs") refreshRuns();
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function renderOverview() {
  if (!state.overview) return;
  const { catalog, runs, validation, runner } = state.overview;
  $("#runner-label").textContent = `${runner} runner`;
  $("#metric-tasks").textContent = catalog.tasks;
  $("#nav-task-count").textContent = catalog.tasks;
  $("#metric-precision").textContent = `${Math.round(validation.precision * 100)}%`;
  $("#metric-recall").textContent = `${Math.round(validation.recall * 100)}%`;
  $("#hero-precision").textContent = `${Math.round(validation.precision * 100)}%`;
  $("#validation-precision").textContent = `${Math.round(validation.precision * 100)}%`;
  $("#validation-recall").textContent = `${Math.round(validation.recall * 100)}%`;
  $("#metric-runs").textContent = runs.total_runs;
  $("#metric-pass-rate").textContent = runs.total_runs ? `${Math.round(runs.pass_rate * 100)}% pass rate` : "No runs yet";
  $("#metric-average").textContent = runs.total_runs ? `${formatDuration(runs.average_duration_ms)} avg` : "— avg";
  renderRecentRuns();
}

function renderRecentRuns() {
  const target = $("#recent-runs");
  if (!state.runs.length) {
    target.className = "recent-runs empty-state compact";
    target.innerHTML = `
      <div class="empty-icon">↗</div><strong>No evaluations yet</strong>
      <p>Choose a task and run a submission to create the first trace.</p>
      <button class="button tiny" data-go="tasks">Choose a task</button>`;
    bindGoButtons(target);
    return;
  }
  target.className = "recent-runs";
  target.innerHTML = state.runs.slice(0, 4).map((run) => `
    <div class="recent-row">
      <span class="recent-status ${run.status}">${run.status === "passed" ? "✓" : "!"}</span>
      <span class="recent-name"><strong>${escapeHtml(run.task_title)}</strong><small>${escapeHtml(run.id)} · ${escapeHtml(run.runner)}</small></span>
      <span class="recent-score">${run.passed_cases}/${run.total_cases} cases</span>
      <span class="recent-time">${relativeTime(run.created_at)}</span>
    </div>`).join("");
}

function renderCategoryFilters() {
  const categories = ["All", ...new Set(state.tasks.map((task) => task.category))];
  $("#category-filters").innerHTML = categories.map((category) => `
    <button class="filter-chip ${state.selectedCategory === category ? "active" : ""}" data-category="${escapeHtml(category)}">${escapeHtml(category)}</button>`).join("");
  $$(".filter-chip").forEach((button) => button.addEventListener("click", () => {
    state.selectedCategory = button.dataset.category;
    renderCategoryFilters();
    renderTasks();
  }));
}

function renderTasks() {
  const query = $("#task-search").value.trim().toLowerCase();
  const tasks = state.tasks.filter((task) => {
    const inCategory = state.selectedCategory === "All" || task.category === state.selectedCategory;
    const matches = !query || `${task.title} ${task.category} ${task.summary}`.toLowerCase().includes(query);
    return inCategory && matches;
  });
  const target = $("#task-grid");
  if (!tasks.length) {
    target.innerHTML = `<div class="loading-card">No tasks match those filters.</div>`;
    return;
  }
  target.innerHTML = tasks.map((task) => {
    const index = state.tasks.findIndex((item) => item.id === task.id) + 1;
    return `
      <article class="task-card" data-task-id="${escapeHtml(task.id)}" data-index="${String(index).padStart(2, "0")}" tabindex="0">
        <div class="task-card-top"><span class="task-id">TASK_${String(index).padStart(2, "0")}</span><span class="difficulty ${task.difficulty.toLowerCase()}">${escapeHtml(task.difficulty)}</span></div>
        <h3>${escapeHtml(task.title)}</h3><p>${escapeHtml(task.summary)}</p>
        <div class="task-card-footer"><span class="category">${escapeHtml(task.category)}</span><span class="open-task">→</span></div>
      </article>`;
  }).join("");
  $$(".task-card", target).forEach((card) => {
    card.addEventListener("click", () => openTask(card.dataset.taskId));
    card.addEventListener("keydown", (event) => { if (event.key === "Enter") openTask(card.dataset.taskId); });
  });
}

async function openTask(taskId, priorResult = null) {
  try {
    const task = await api(`/api/tasks/${taskId}`);
    state.selectedTask = task;
    const index = state.tasks.findIndex((item) => item.id === task.id) + 1;
    $("#drawer-number").textContent = `TASK ${String(index).padStart(2, "0")}`;
    $("#drawer-title").textContent = task.title;
    $("#drawer-difficulty").textContent = task.difficulty;
    $("#drawer-category").textContent = task.category;
    $("#drawer-signature").textContent = task.signature;
    $("#drawer-instructions").textContent = task.instructions;
    $("#code-editor").value = task.starter_code;
    updateLineNumbers();
    $("#result-panel").innerHTML = priorResult ? renderResult(priorResult) : `<div class="result-placeholder"><span>⌁</span><strong>Ready when you are</strong><p>Run the code to see a case-by-case trace here.</p></div>`;
    $("#task-drawer").classList.add("open");
    $("#task-drawer").setAttribute("aria-hidden", "false");
    $("#drawer-backdrop").classList.add("open");
    document.body.style.overflow = "hidden";
    window.setTimeout(() => $("#code-editor").focus(), 250);
  } catch (error) {
    showToast(error.message);
  }
}

function closeTask() {
  $("#task-drawer").classList.remove("open");
  $("#task-drawer").setAttribute("aria-hidden", "true");
  $("#drawer-backdrop").classList.remove("open");
  document.body.style.overflow = "";
}

function updateLineNumbers() {
  const count = $("#code-editor").value.split("\n").length;
  $("#line-numbers").innerHTML = Array.from({ length: count }, (_, index) => index + 1).join("<br />");
}

function renderResult(result) {
  const icon = result.status === "passed" ? "✓" : result.status === "timeout" ? "◷" : "!";
  const subtitle = result.status === "passed"
    ? `${result.passed_cases} of ${result.total_cases} checks passed`
    : `${result.passed_cases} of ${result.total_cases} checks passed · review the trace below`;
  const error = result.error ? `<div class="result-error">${escapeHtml(result.error)}</div>` : "";
  const cases = result.cases?.length ? `<div class="case-list">${result.cases.map((testCase) => {
    const detail = testCase.error
      ? testCase.error
      : testCase.status === "passed"
        ? `received ${formatValue(testCase.actual)}`
        : `expected ${formatValue(testCase.expected)} · received ${formatValue(testCase.actual)}`;
    return `<div class="case-row">
      <span class="case-mark ${testCase.status}">${testCase.status === "passed" ? "✓" : "!"}</span>
      <span class="case-name"><strong>${escapeHtml(testCase.name)}</strong><small>${escapeHtml(detail)}</small></span>
      <span class="case-time">${testCase.duration_ms.toFixed(2)}ms</span>
    </div>`;
  }).join("")}</div>` : "";
  return `<div class="result-summary">
      <span class="result-icon ${result.status}">${icon}</span>
      <div><strong>${escapeHtml(result.status)}</strong><small>${subtitle}</small></div>
      <code>${formatDuration(result.duration_ms)} · ${escapeHtml(result.runner)}</code>
    </div>${error}${cases}`;
}

async function runEvaluation() {
  if (!state.selectedTask) return;
  const button = $("#run-evaluation");
  button.disabled = true;
  button.classList.add("loading");
  try {
    const result = await api("/api/runs", {
      method: "POST",
      body: JSON.stringify({ task_id: state.selectedTask.id, code: $("#code-editor").value }),
    });
    $("#result-panel").innerHTML = renderResult(result);
    showToast(result.status === "passed" ? "All checks passed" : "Evaluation complete — review the trace");
    await refreshData();
  } catch (error) {
    $("#result-panel").innerHTML = `<div class="result-error">${escapeHtml(error.message)}</div>`;
    showToast(error.message);
  } finally {
    button.disabled = false;
    button.classList.remove("loading");
  }
}

async function refreshRuns() {
  try {
    state.runs = await api("/api/runs?limit=100");
    renderRuns();
    renderRecentRuns();
  } catch (error) {
    showToast(error.message);
  }
}

function renderRuns() {
  const target = $("#run-table");
  $("#run-total-label").textContent = `${state.runs.length} total`;
  if (!state.runs.length) {
    target.innerHTML = `<div class="run-table-empty empty-state"><div class="empty-icon">↗</div><strong>No saved traces</strong><p>Your evaluation history will appear here.</p><button class="button tiny" data-go="tasks">Run the first one</button></div>`;
    bindGoButtons(target);
    return;
  }
  target.innerHTML = `<div class="run-table-header"><span>Task</span><span>Status</span><span>Cases</span><span>Duration</span><span>Created</span></div>` + state.runs.map((run) => `
    <div class="run-table-row" data-run-id="${escapeHtml(run.id)}" title="Open trace">
      <span class="run-task"><strong>${escapeHtml(run.task_title)}</strong><small>${escapeHtml(run.id)} · ${escapeHtml(run.runner)}</small></span>
      <span class="status-badge ${run.status}">${escapeHtml(run.status)}</span>
      <span>${run.passed_cases} / ${run.total_cases}</span><span>${formatDuration(run.duration_ms)}</span><span>${relativeTime(run.created_at)}</span>
    </div>`).join("");
  $$(".run-table-row", target).forEach((row) => row.addEventListener("click", () => {
    const run = state.runs.find((item) => item.id === row.dataset.runId);
    if (run) openTask(run.task_id, run);
  }));
}

function bindGoButtons(root = document) {
  $$('[data-go]', root).forEach((button) => {
    if (button.dataset.bound) return;
    button.dataset.bound = "true";
    button.addEventListener("click", () => routeTo(button.dataset.go));
  });
}

async function refreshData() {
  const [overview, runs] = await Promise.all([api("/api/overview"), api("/api/runs?limit=100")]);
  state.overview = overview;
  state.runs = runs;
  renderOverview();
  renderRuns();
}

async function initialize() {
  bindGoButtons();
  $$(".nav-item").forEach((button) => button.addEventListener("click", () => routeTo(button.dataset.route)));
  $("#mobile-menu").addEventListener("click", () => $(".sidebar").classList.toggle("open"));
  $("#close-drawer").addEventListener("click", closeTask);
  $("#drawer-backdrop").addEventListener("click", closeTask);
  $("#run-evaluation").addEventListener("click", runEvaluation);
  $("#task-search").addEventListener("input", renderTasks);
  $("#quick-find").addEventListener("click", () => {
    routeTo("tasks");
    window.setTimeout(() => $("#task-search").focus(), 50);
  });
  $("#code-editor").addEventListener("input", updateLineNumbers);
  $("#code-editor").addEventListener("scroll", (event) => { $("#line-numbers").scrollTop = event.target.scrollTop; });
  $("#code-editor").addEventListener("keydown", (event) => {
    if (event.key === "Tab") {
      event.preventDefault();
      const editor = event.target;
      const start = editor.selectionStart;
      editor.value = `${editor.value.slice(0, start)}    ${editor.value.slice(editor.selectionEnd)}`;
      editor.selectionStart = editor.selectionEnd = start + 4;
      updateLineNumbers();
    }
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeTask();
    if (event.key === "/" && !["INPUT", "TEXTAREA"].includes(document.activeElement.tagName)) {
      event.preventDefault(); routeTo("tasks"); window.setTimeout(() => $("#task-search").focus(), 50);
    }
    if ((event.metaKey || event.ctrlKey) && event.key === "Enter" && $("#task-drawer").classList.contains("open")) runEvaluation();
  });

  try {
    const [tasks, overview, runs] = await Promise.all([
      api("/api/tasks"), api("/api/overview"), api("/api/runs?limit=100"),
    ]);
    state.tasks = tasks;
    state.overview = overview;
    state.runs = runs;
    renderCategoryFilters();
    renderTasks();
    renderOverview();
    renderRuns();
  } catch (error) {
    showToast(`Could not load the workspace: ${error.message}`);
  }
  routeTo(window.location.hash.slice(1) || "overview");
}

initialize();


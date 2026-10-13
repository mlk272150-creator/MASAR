const dashboardUser = MasarApi.requireUser();
const dashboardToast = document.querySelector("#toast");
const taskDialog = document.querySelector("#task-dialog");
let dashboardToastTimer;

const dashboardStatusLabels = {
  pending: "بانتظار الموافقة",
  approved: "تمت الموافقة",
  in_progress: "قيد الإنجاز",
  completed: "مكتملة",
  cancelled: "ملغاة",
};

function notifyDashboard(message, isError = false) {
  dashboardToast.textContent = message;
  dashboardToast.classList.toggle("error", isError);
  dashboardToast.classList.add("visible");
  window.clearTimeout(dashboardToastTimer);
  dashboardToastTimer = window.setTimeout(() => dashboardToast.classList.remove("visible"), 3500);
}

function formatDashboardNumber(value) {
  return MasarApi.formatNumber(value);
}

async function refreshTaskPrice(form) {
  const output = document.querySelector("#task-price-value");
  const note = document.querySelector("#task-price-note");
  const values = new FormData(form);
  output.textContent = "…";
  try {
    const result = await MasarApi.request("/ai/pricing/estimate", {
      method: "POST",
      body: JSON.stringify({
        requested_task: {
          region: values.get("region"),
          profession: values.get("profession"),
          demand: Number(values.get("demand")),
          supply: Number(values.get("supply")),
        },
      }),
    });
    output.textContent = formatDashboardNumber(Math.round(result.predicted_price_points));
    note.textContent = `تقدير توضيحي من ${formatDashboardNumber(result.training_examples)} سجل اصطناعي.`;
  } catch (error) {
    output.textContent = "—";
    note.textContent = error.message;
  }
}

async function refreshBalance() {
  const balance = await MasarApi.request(`/users/${dashboardUser.id}/balance`);
  document.querySelector("#balance-value").textContent = formatDashboardNumber(balance.balance_points);
}

function renderTaskRow(task, role) {
  const row = document.createElement("tr");
  const title = document.createElement("td");
  const titleText = document.createElement("div");
  titleText.className = "task-title";
  titleText.textContent = task.title;
  const description = document.createElement("div");
  description.className = "task-subtitle";
  description.textContent = `${task.region} · ${task.profession}${task.description ? ` · ${task.description}` : ""}`;
  title.append(titleText, description);

  const roleCell = document.createElement("td");
  const roleTag = document.createElement("span");
  roleTag.className = "role-tag";
  roleTag.textContent = role === "owner" ? "صاحب المهمة" : "العامل";
  roleCell.append(roleTag);

  const statusCell = document.createElement("td");
  const status = document.createElement("span");
  status.className = `status-tag ${task.status}`;
  status.textContent = dashboardStatusLabels[task.status] || task.status;
  statusCell.append(status);

  const reward = document.createElement("td");
  reward.className = "reward-cell";
  reward.textContent = `${formatDashboardNumber(task.reward_points)} نقطة`;

  const actionCell = document.createElement("td");
  if (role === "owner" && task.status === "pending") {
    actionCell.append(makeTaskAction(task, "approve", "موافقة"));
  } else if (role === "worker" && ["approved", "in_progress"].includes(task.status)) {
    actionCell.append(makeTaskAction(task, "complete", "إنهاء"));
  } else {
    actionCell.textContent = "—";
  }
  row.append(title, roleCell, statusCell, reward, actionCell);
  return row;
}

function makeTaskAction(task, action, label) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "row-action";
  button.textContent = label;
  button.addEventListener("click", async () => {
    button.disabled = true;
    try {
      await MasarApi.request(`/tasks/${task.id}/${action}`, { method: "POST" });
      notifyDashboard(action === "approve" ? "تمت الموافقة على المهمة." : "تم تسجيل إنجاز المهمة.");
      await Promise.all([refreshTasks(), refreshBalance()]);
    } catch (error) {
      notifyDashboard(error.message, true);
      button.disabled = false;
    }
  });
  return button;
}

function renderMobileTask(task, role) {
  const card = document.createElement("article");
  card.className = "mobile-task-card";
  const top = document.createElement("div");
  top.className = "mobile-task-top";
  const title = document.createElement("strong");
  title.className = "task-title";
  title.textContent = task.title;
  const status = document.createElement("span");
  status.className = `status-tag ${task.status}`;
  status.textContent = dashboardStatusLabels[task.status] || task.status;
  top.append(title, status);
  const meta = document.createElement("div");
  meta.className = "mobile-task-meta";
  meta.textContent = `${role === "owner" ? "صاحب المهمة" : "العامل"} · ${formatDashboardNumber(task.reward_points)} نقطة`;
  card.append(top, meta);
  if (role === "owner" && task.status === "pending") {
    card.append(makeTaskAction(task, "approve", "الموافقة على المهمة"));
  } else if (role === "worker" && ["approved", "in_progress"].includes(task.status)) {
    card.append(makeTaskAction(task, "complete", "تسجيل الإنجاز"));
  }
  return card;
}

async function refreshTasks() {
  const tableBody = document.querySelector("#task-table-body");
  const mobileList = document.querySelector("#mobile-task-list");
  try {
    const tasks = await MasarApi.request("/tasks");
    const relatedTasks = tasks
      .filter((task) => task.user_id === dashboardUser.id || task.assignee_id === dashboardUser.id)
      .sort((left, right) => right.id - left.id);
    tableBody.replaceChildren();
    mobileList.replaceChildren();
    if (!relatedTasks.length) {
      tableBody.innerHTML = '<tr><td colspan="5" class="empty-row">لا توجد مهام مرتبطة بحسابك بعد. اطرح مهمتك الأولى للبدء.</td></tr>';
      mobileList.innerHTML = '<div class="empty-row">لا توجد مهام مرتبطة بحسابك بعد. اطرح مهمتك الأولى للبدء.</div>';
      return;
    }
    relatedTasks.forEach((task) => {
      const role = task.user_id === dashboardUser.id ? "owner" : "worker";
      tableBody.append(renderTaskRow(task, role));
      mobileList.append(renderMobileTask(task, role));
    });
  } catch (error) {
    tableBody.innerHTML = `<tr><td colspan="5" class="empty-row">${MasarApi.escape(error.message)}</td></tr>`;
    mobileList.textContent = error.message;
    throw error;
  }
}

function initializeDashboard() {
  const name = dashboardUser.username || dashboardUser.phone_number || "صديق مسار";
  document.querySelector("#welcome-name").textContent = name;
  document.querySelector("#user-name").textContent = name;
  document.querySelector("#user-avatar").textContent = [...name][0] || "م";
  document.querySelector("#date-label").textContent = new Intl.DateTimeFormat("ar", {
    weekday: "long", day: "numeric", month: "long",
  }).format(new Date());
  document.querySelector("#logout-button").addEventListener("click", () => MasarApi.signOut());
  document.querySelector("#refresh-tasks").addEventListener("click", async () => {
    try {
      await refreshTasks();
      await refreshBalance();
      notifyDashboard("تم تحديث لوحة التحكم.");
    } catch (error) {
      notifyDashboard(error.message, true);
    }
  });
  document.querySelector("#open-task-dialog").addEventListener("click", () => taskDialog.showModal());
  document.querySelector("#close-task-dialog").addEventListener("click", () => taskDialog.close());
  taskDialog.addEventListener("click", (event) => {
    if (event.target === taskDialog) taskDialog.close();
  });
  const taskForm = document.querySelector("#task-form");
  ["region", "profession", "demand", "supply"].forEach((name) => {
    taskForm.elements[name].addEventListener("change", () => refreshTaskPrice(taskForm));
  });
  document.querySelector("#open-task-dialog").addEventListener("click", () => refreshTaskPrice(taskForm));
  taskForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const values = new FormData(form);
    const payload = {
      user_id: dashboardUser.id,
      assignee_id: values.get("assignee_id") ? Number(values.get("assignee_id")) : null,
      title: values.get("title").trim(),
      description: values.get("description").trim() || null,
      region: values.get("region"),
      profession: values.get("profession"),
      demand: Number(values.get("demand")),
      supply: Number(values.get("supply")),
      priority: values.get("priority"),
    };
    const button = form.querySelector('button[type="submit"]');
    button.disabled = true;
    button.textContent = "جارٍ النشر…";
    try {
      await MasarApi.request("/tasks", { method: "POST", body: JSON.stringify(payload) });
      taskDialog.close();
      form.reset();
      form.elements.priority.value = "medium";
      form.elements.region.value = "نابلس";
      form.elements.profession.value = "كهرباء";
      form.elements.demand.value = "6";
      form.elements.supply.value = "6";
      document.querySelector("#task-price-value").textContent = "—";
      document.querySelector("#task-price-note").textContent = "يحسبه XGBoost عند تحديد التفاصيل.";
      notifyDashboard("تم نشر المهمة بنجاح.");
      await Promise.all([refreshTasks(), refreshBalance()]);
    } catch (error) {
      notifyDashboard(error.message, true);
    } finally {
      button.disabled = false;
      button.textContent = "نشر المهمة";
    }
  });
  Promise.all([refreshBalance(), refreshTasks()]).catch((error) => notifyDashboard(error.message, true));
}

initializeDashboard();

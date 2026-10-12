const $ = (selector) => document.querySelector(selector);

let currentClient = null;
let toastTimer = null;

async function api(path, { method = "GET", body } = {}) {
  const res = await fetch(path, {
    method,
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (res.status === 204) return null;
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`);
  return data;
}

function toast(message, isError = false) {
  const el = $("#toast");
  el.textContent = message;
  el.classList.toggle("error", isError);
  el.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { el.hidden = true; }, 3500);
}

async function run(action) {
  try {
    await action();
  } catch (err) {
    toast(err.message, true);
  }
}

function cell(tag, text, className) {
  const el = document.createElement(tag);
  el.textContent = text;
  if (className) el.className = className;
  return el;
}

const clientPath = (name) => `/clients/${encodeURIComponent(name)}`;

// ---------- Client list ----------
async function loadClients() {
  const clients = await api("/clients");
  const list = $("#client-list");
  list.replaceChildren();
  for (const c of clients) {
    const li = document.createElement("li");
    const btn = cell("button", c.name);
    btn.type = "button";
    btn.classList.toggle("active", c.name === currentClient);
    btn.addEventListener("click", () => run(() => selectClient(c.name)));
    li.append(btn);
    list.append(li);
  }
}

async function selectClient(name) {
  currentClient = name;
  $("#empty").hidden = true;
  $("#client-view").hidden = false;
  await Promise.all([loadClients(), loadClient()]);
}

// ---------- Client detail ----------
async function loadClient() {
  const name = currentClient;
  const [client, membership, workouts, progress] = await Promise.all([
    api(clientPath(name)),
    api(`${clientPath(name)}/membership`),
    api(`${clientPath(name)}/workouts`),
    api(`${clientPath(name)}/progress`),
  ]);
  renderHeader(client, membership);
  renderProfileForm(client);
  renderWorkouts(workouts);
  renderProgress(progress);
}

function renderHeader(client, membership) {
  $("#client-name").textContent = client.name;
  const badge = $("#membership-badge");
  badge.textContent = membership.status;
  badge.className = `badge ${membership.status.toLowerCase()}`;

  const orDash = (v) => (v === null || v === undefined || v === "" ? "-" : v);
  const stats = [
    ["Age", orDash(client.age)],
    ["Height", client.height ? `${client.height} cm` : "-"],
    ["Weight", client.weight ? `${client.weight} kg` : "-"],
    ["Target weight", client.target_weight ? `${client.target_weight} kg` : "-"],
    ["Calories", orDash(client.calories)],
    ["Program", orDash(client.program)],
    ["Renewal", orDash(membership.renewal_date)],
  ];
  const dl = $("#stats");
  dl.replaceChildren();
  for (const [label, value] of stats) {
    const box = document.createElement("div");
    box.append(cell("dt", label), cell("dd", String(value)));
    dl.append(box);
  }
}

function renderProfileForm(client) {
  const form = $("#profile-form");
  for (const el of form.elements) {
    if (!el.name) continue;
    const value = client[el.name];
    el.value = value === null || value === undefined ? "" : value;
  }
}

function renderWorkouts(workouts) {
  const body = $("#workout-rows");
  body.replaceChildren();
  for (const w of workouts) {
    const tr = document.createElement("tr");
    tr.append(cell("td", w.date), cell("td", w.workout_type), cell("td", String(w.duration_min)), cell("td", w.notes || ""));
    body.append(tr);
  }
  $("#workouts-empty").hidden = workouts.length > 0;
}

function renderProgress(entries) {
  const bars = $("#progress-bars");
  bars.replaceChildren();
  for (const p of entries) {
    const row = document.createElement("div");
    row.className = "bar-row";
    const track = document.createElement("div");
    track.className = "bar-track";
    const fill = document.createElement("div");
    fill.className = "bar-fill";
    fill.style.width = `${Math.min(Math.max(p.adherence, 0), 100)}%`;
    track.append(fill);
    row.append(cell("span", p.week), track, cell("span", `${p.adherence}%`));
    bars.append(row);
  }
  $("#progress-empty").hidden = entries.length > 0;
}

// ---------- Events ----------
$("#add-client-form").addEventListener("submit", (e) => {
  e.preventDefault();
  const form = e.currentTarget;
  run(async () => {
    const name = form.elements.name.value.trim();
    await api("/clients", { method: "POST", body: { name } });
    form.reset();
    toast(`Added ${name}`);
    await selectClient(name);
  });
});

$("#generate-program").addEventListener("click", () => run(async () => {
  const res = await api(`${clientPath(currentClient)}/program`, { method: "POST" });
  toast(`Program: ${res.program} (${res.category})`);
  await loadClient();
}));

$("#delete-client").addEventListener("click", () => run(async () => {
  if (!confirm(`Delete ${currentClient} and all their data?`)) return;
  await api(clientPath(currentClient), { method: "DELETE" });
  toast(`Deleted ${currentClient}`);
  currentClient = null;
  $("#client-view").hidden = true;
  $("#empty").hidden = false;
  await loadClients();
}));

$("#profile-form").addEventListener("submit", (e) => {
  e.preventDefault();
  const form = e.currentTarget;
  run(async () => {
    const body = {};
    for (const el of form.elements) {
      if (!el.name) continue;
      if (el.name === "membership_status") body[el.name] = el.value;
      else if (el.name === "membership_end") body[el.name] = el.value || null;
      else if (el.value !== "") body[el.name] = Number(el.value);
    }
    await api(clientPath(currentClient), { method: "PUT", body });
    toast("Profile saved");
    await loadClient();
  });
});

$("#workout-form").addEventListener("submit", (e) => {
  e.preventDefault();
  const form = e.currentTarget;
  run(async () => {
    const f = form.elements;
    await api(`${clientPath(currentClient)}/workouts`, {
      method: "POST",
      body: {
        date: f.date.value,
        workout_type: f.workout_type.value,
        duration_min: Number(f.duration_min.value),
        notes: f.notes.value,
      },
    });
    f.notes.value = "";
    toast("Workout added");
    await loadClient();
  });
});

$("#progress-form").addEventListener("submit", (e) => {
  e.preventDefault();
  const form = e.currentTarget;
  run(async () => {
    const f = form.elements;
    await api(`${clientPath(currentClient)}/progress`, {
      method: "POST",
      body: { week: f.week.value, adherence: Number(f.adherence.value) },
    });
    form.reset();
    toast("Progress added");
    await loadClient();
  });
});

for (const tab of document.querySelectorAll(".tab")) {
  tab.addEventListener("click", () => {
    for (const t of document.querySelectorAll(".tab")) t.classList.toggle("active", t === tab);
    for (const panel of document.querySelectorAll(".panel")) panel.hidden = panel.id !== `tab-${tab.dataset.tab}`;
  });
}

// ---------- Init ----------
$("#workout-form").elements.date.value = new Date().toISOString().slice(0, 10);
run(async () => {
  const [{ version }] = await Promise.all([api("/version"), loadClients()]);
  $("#version").textContent = `v${version}`;
});

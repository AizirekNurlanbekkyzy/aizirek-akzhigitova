"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import {
  acceptAssignment, changeRequestStatus, createEstimate, createInventoryItem, createRequest,
  decideEstimate, Estimate, getAssignments, getEstimates, getInventory, getMe, getMyAssignments,
  getRequests, getTechnicians, InventoryItem, login, recordStockMovement, registerCustomer,
  RequestItem, Role, scheduleAssignment, submitEstimate, Technician, UserProfile,
} from "@/lib/api";

type Language = "ru" | "en";
type Section = "dashboard" | "requests" | "estimates" | "technicians" | "schedule" | "inventory" | "tasks";

const text: Record<Language, Record<string, string>> = {
  ru: {
    subtitle: "Сервисные заявки и обслуживание", signIn: "Войти", register: "Создать аккаунт",
    email: "Электронная почта", password: "Пароль (не менее 12 символов)", org: "ID организации",
    name: "Ваше имя", dashboard: "Обзор", requests: "Заявки", estimates: "Сметы",
    technicians: "Специалисты", schedule: "Расписание", inventory: "Склад", tasks: "Мои задачи",
    welcome: "Добро пожаловать", totalRequests: "Всего заявок", openRequests: "Открытые",
    pendingEstimates: "Сметы на согласовании", lowStock: "Низкий остаток", newRequest: "Новая заявка",
    title: "Краткое название", description: "Опишите проблему (20–3000 символов)", create: "Создать",
    search: "Поиск по заявкам", refresh: "Обновить", empty: "Пока нет данных",
    status: "Статус", priority: "Приоритет", created: "Создана", action: "Действие",
    triage: "Взять в работу диспетчерам", cancel: "Отменить", save: "Сохранить",
    newEstimate: "Создать смету", request: "Заявка", amount: "Цена, тыйын", line: "Описание работ",
    submitEstimate: "Отправить на согласование", approve: "Согласовать", reject: "Отклонить",
    version: "Версия", total: "Итого", noTechs: "Специалисты не найдены", noSchedule: "Назначений пока нет",
    assign: "Назначить мастера", start: "Начало", end: "Окончание", scheduleButton: "Запланировать",
    accept: "Принять назначение", startWork: "Начать работу", complete: "Завершить",
    newItem: "Добавить позицию", sku: "Артикул", itemName: "Название", unit: "Ед. изм.", min: "Мин. остаток",
    stockMovement: "Операция склада", quantity: "Количество (+приход / −расход)", reason: "Причина",
    add: "Добавить", manager: "Управление FixFlow", customer: "Клиент", dispatcher: "Диспетчер",
    admin: "Администратор", technician: "Специалист", logout: "Выйти", noResults: "Ничего не найдено",
    ru: "Русский", en: "English", loadError: "Не удалось загрузить данные", recordCreated: "Сохранено",
  },
  en: {
    subtitle: "Service requests and maintenance", signIn: "Sign in", register: "Create account",
    email: "Email", password: "Password (at least 12 characters)", org: "Organization ID",
    name: "Your name", dashboard: "Dashboard", requests: "Requests", estimates: "Estimates",
    technicians: "Technicians", schedule: "Schedule", inventory: "Inventory", tasks: "My tasks",
    welcome: "Welcome", totalRequests: "Total requests", openRequests: "Open", pendingEstimates: "Pending estimates",
    lowStock: "Low stock", newRequest: "New request", title: "Short title",
    description: "Describe the issue (20–3000 characters)", create: "Create", search: "Search requests",
    refresh: "Refresh", empty: "No data yet", status: "Status", priority: "Priority", created: "Created",
    action: "Action", triage: "Move to triage", cancel: "Cancel", save: "Save", newEstimate: "Create estimate",
    request: "Request", amount: "Price, tyiyn", line: "Work description", submitEstimate: "Send for approval",
    approve: "Approve", reject: "Reject", version: "Version", total: "Total", noTechs: "No technicians found",
    noSchedule: "No assignments yet", assign: "Assign technician", start: "Start", end: "End",
    scheduleButton: "Schedule", accept: "Accept assignment", startWork: "Start work", complete: "Complete",
    newItem: "Add inventory item", sku: "SKU", itemName: "Name", unit: "Unit", min: "Minimum stock",
    stockMovement: "Stock movement", quantity: "Quantity (+receive / −issue)", reason: "Reason", add: "Add",
    manager: "FixFlow workspace", customer: "Customer", dispatcher: "Dispatcher", admin: "Administrator",
    technician: "Technician", logout: "Sign out", noResults: "No results", ru: "Русский", en: "English",
    loadError: "Could not load data", recordCreated: "Saved",
  },
};

const statusText: Record<Language, Record<string, string>> = {
  ru: { SUBMITTED: "Новая", TRIAGED: "На проверке", SCHEDULED: "Запланирована", ACCEPTED: "Принята", IN_PROGRESS: "В работе", COMPLETED: "Завершена", CLOSED: "Закрыта", CANCELED: "Отменена", BLOCKED: "Приостановлена", REOPENED: "Возобновлена", DRAFT: "Черновик", AWAITING_APPROVAL: "Ждёт согласования", APPROVED: "Согласована", REJECTED: "Отклонена", SUPERSEDED: "Заменена", OFFERED: "Предложена" },
  en: { SUBMITTED: "Submitted", TRIAGED: "Triaged", SCHEDULED: "Scheduled", ACCEPTED: "Accepted", IN_PROGRESS: "In progress", COMPLETED: "Completed", CLOSED: "Closed", CANCELED: "Canceled", BLOCKED: "Blocked", REOPENED: "Reopened", DRAFT: "Draft", AWAITING_APPROVAL: "Awaiting approval", APPROVED: "Approved", REJECTED: "Rejected", SUPERSEDED: "Superseded", OFFERED: "Offered" },
};

const managerRoles: Role[] = ["DISPATCHER", "ORGANIZATION_ADMIN"];

export default function Home() {
  const [language, setLanguage] = useState<Language>("ru");
  const [token, setToken] = useState("");
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [section, setSection] = useState<Section>("dashboard");
  const [authMode, setAuthMode] = useState<"login" | "register">("login");
  const [requests, setRequests] = useState<RequestItem[]>([]);
  const [estimates, setEstimates] = useState<Estimate[]>([]);
  const [inventory, setInventory] = useState<InventoryItem[]>([]);
  const [technicians, setTechnicians] = useState<Technician[]>([]);
  const [assignments, setAssignments] = useState<Awaited<ReturnType<typeof getAssignments>>>([]);
  const [myAssignments, setMyAssignments] = useState<Awaited<ReturnType<typeof getMyAssignments>>>([]);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [search, setSearch] = useState("");
  const [busy, setBusy] = useState(false);
  const t = text[language];

  useEffect(() => {
    setLanguage((localStorage.getItem("fixflow-lang") as Language) || "ru");
    const saved = localStorage.getItem("fixflow-token");
    if (saved) setToken(saved);
  }, []);

  const refresh = useCallback(async (activeToken: string, role: Role) => {
    setBusy(true);
    setError("");
    try {
      const requestRows = await getRequests(activeToken, search);
      setRequests(requestRows);
      const estimateRows = await Promise.all(requestRows.map((request) => getEstimates(activeToken, request.id).catch(() => [])));
      setEstimates(estimateRows.flat());
      if (managerRoles.includes(role)) {
        const [stock, team, scheduleRows] = await Promise.all([
          getInventory(activeToken), getTechnicians(activeToken), getAssignments(activeToken),
        ]);
        setInventory(stock); setTechnicians(team); setAssignments(scheduleRows);
      } else if (role === "TECHNICIAN") {
        setMyAssignments(await getMyAssignments(activeToken));
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : t.loadError);
      if (cause instanceof Error && cause.message.includes("401")) logout();
    } finally { setBusy(false); }
  }, [search, t.loadError]);

  useEffect(() => {
    let cancelled = false;
    if (!token) return;
    getMe(token).then((user) => { if (!cancelled) setProfile(user); }).catch(() => {
      localStorage.removeItem("fixflow-token"); setToken(""); setProfile(null);
    });
    return () => { cancelled = true; };
  }, [token]);

  useEffect(() => { if (token && profile) void refresh(token, profile.role); }, [token, profile, refresh]);

  const isManager = profile !== null && managerRoles.includes(profile.role);
  const allowedSections = useMemo<Section[]>(() => {
    if (!profile) return [];
    if (profile.role === "TECHNICIAN") return ["dashboard", "tasks"];
    return isManager ? ["dashboard", "requests", "estimates", "technicians", "schedule", "inventory"] : ["dashboard", "requests", "estimates"];
  }, [profile, isManager]);
  const visibleRequests = useMemo(() => requests.filter((item) =>
    `${item.title} ${item.description}`.toLowerCase().includes(search.toLowerCase())), [requests, search]);

  function logout() {
    localStorage.removeItem("fixflow-token");
    setToken(""); setProfile(null); setRequests([]); setEstimates([]); setInventory([]); setSection("dashboard");
  }

  async function authenticate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError("");
    const data = new FormData(event.currentTarget);
    const organization_id = String(data.get("organization_id"));
    try {
      if (authMode === "register") {
        await registerCustomer({ email: String(data.get("email")), name: String(data.get("name")), password: String(data.get("password")), organization_id });
      }
      const value = await login(String(data.get("email")), String(data.get("password")), organization_id);
      localStorage.setItem("fixflow-token", value); setToken(value);
    } catch (cause) { setError(cause instanceof Error ? cause.message : t.loadError); }
    finally { setBusy(false); }
  }

  async function act(action: () => Promise<unknown>) {
    setBusy(true); setError(""); setNotice("");
    try { await action(); setNotice(t.recordCreated); if (profile) await refresh(token, profile.role); }
    catch (cause) { setError(cause instanceof Error ? cause.message : t.loadError); }
    finally { setBusy(false); }
  }

  async function createRequestForm(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form = event.currentTarget; const data = new FormData(form);
    const payload = { title: String(data.get("title")), description: String(data.get("description")), priority: "NORMAL" };
    const payloadText = JSON.stringify(payload);
    const last = JSON.parse(sessionStorage.getItem("fixflow-create-retry") || "null") as { body: string; key: string } | null;
    const key = last?.body === payloadText ? last.key : crypto.randomUUID();
    sessionStorage.setItem("fixflow-create-retry", JSON.stringify({ body: payloadText, key }));
    await act(async () => { await createRequest(token, payload, key); sessionStorage.removeItem("fixflow-create-retry"); form.reset(); });
  }

  const navLabel: Record<Section, string> = {
    dashboard: t.dashboard, requests: t.requests, estimates: t.estimates, technicians: t.technicians,
    schedule: t.schedule, inventory: t.inventory, tasks: t.tasks,
  };

  if (!token || !profile) return <main className="auth-shell">
    <section className="auth-panel"><div className="brand-mark">F</div><p className="eyebrow">FIXFLOW · SERVICE OPERATIONS</p>
      <h1>{t.subtitle}</h1><p className="muted">{language === "ru" ? "Единое рабочее пространство для сервиса и выездных команд." : "One workspace for service operations and field teams."}</p>
      <div className="language-row"><button className={language === "ru" ? "active" : ""} onClick={() => { setLanguage("ru"); localStorage.setItem("fixflow-lang", "ru"); }}>RU</button><button className={language === "en" ? "active" : ""} onClick={() => { setLanguage("en"); localStorage.setItem("fixflow-lang", "en"); }}>EN</button></div>
    </section><form className="card auth-card" onSubmit={authenticate}>
      <div className="segmented"><button type="button" className={authMode === "login" ? "selected" : ""} onClick={() => setAuthMode("login")}>{t.signIn}</button><button type="button" className={authMode === "register" ? "selected" : ""} onClick={() => setAuthMode("register")}>{t.register}</button></div>
      {authMode === "register" && <label>{t.name}<input className="input" name="name" minLength={2} required /></label>}
      <label>{t.email}<input className="input" name="email" type="email" required /></label>
      <label>{t.password}<input className="input" name="password" type="password" minLength={authMode === "register" ? 12 : 1} required /></label>
      <label>{t.org}<input className="input" name="organization_id" placeholder="00000000-0000-0000-0000-000000000000" required /></label>
      {error && <p className="alert" role="alert">{error}</p>}<button className="button primary full" disabled={busy}>{busy ? "…" : authMode === "login" ? t.signIn : t.register}</button>
      <p className="form-note">{language === "ru" ? "Регистрация создаёт только клиентский аккаунт." : "Registration creates a customer account only."}</p>
    </form>
  </main>;

  return <main className="app-shell">
    <aside className="sidebar"><div className="logo"><span className="brand-mark small">F</span><strong>FixFlow</strong></div><p className="side-caption">{t.manager}</p>
      <nav>{allowedSections.map((item) => <button key={item} className={`nav-item ${section === item ? "current" : ""}`} onClick={() => setSection(item)}><span className="nav-dot" />{navLabel[item]}</button>)}</nav>
      <div className="side-bottom"><div className="profile-chip"><div className="avatar">{profile.name.slice(0, 1).toUpperCase()}</div><div><strong>{profile.name}</strong><small>{t[profile.role.toLowerCase().replace("organization_", "")] || profile.role}</small></div></div><button className="button ghost full" onClick={logout}>{t.logout}</button></div>
    </aside>
    <section className="main-area"><header className="page-header"><div><p className="eyebrow">{new Date().toLocaleDateString(language === "ru" ? "ru-RU" : "en-US", { weekday: "long", month: "long", day: "numeric" })}</p><h1>{navLabel[section]}</h1></div><div className="header-actions"><button className="button ghost" onClick={() => setLanguage(language === "ru" ? "en" : "ru")}>{language.toUpperCase()}</button><button className="button ghost" onClick={() => void refresh(token, profile.role)} disabled={busy}>{t.refresh}</button></div></header>
      {(error || notice) && <p className={error ? "alert toast" : "success toast"} role="status">{error || notice}</p>}
      {section === "dashboard" && <><div className="welcome-row"><div><h2>{t.welcome}, {profile.name.split(" ")[0]}</h2><p className="muted">{language === "ru" ? "Текущая картина по вашим сервисным операциям." : "A live view of your service operations."}</p></div></div><div className="stats-grid"><Stat label={t.totalRequests} value={requests.length} icon="↗"/><Stat label={t.openRequests} value={requests.filter((r) => !["COMPLETED", "CLOSED", "CANCELED"].includes(r.status)).length} icon="◷"/><Stat label={t.pendingEstimates} value={estimates.filter((e) => e.status === "AWAITING_APPROVAL").length} icon="◇"/>{isManager && <Stat label={t.lowStock} value={inventory.filter((i) => i.quantity_on_hand <= i.minimum_quantity).length} icon="▤"/>}</div><section className="card section-card"><div className="section-heading"><div><h2>{t.requests}</h2><p className="muted">{language === "ru" ? "Последние обновления из API" : "Latest updates from the API"}</p></div><button className="button secondary" onClick={() => setSection(profile.role === "TECHNICIAN" ? "tasks" : "requests")}>{t.requests} →</button></div><RequestTable items={requests.slice(0, 5)} language={language} labels={t} /></section></>}
      {section === "requests" && <div className="content-grid"><section className="card section-card"><div className="section-heading"><h2>{t.requests}</h2><input className="input search" value={search} onChange={(e) => setSearch(e.target.value)} placeholder={t.search}/></div><RequestTable items={visibleRequests} language={language} labels={t} /><p className="muted small-text">{visibleRequests.length} / {requests.length}</p>
        {isManager && <div className="request-actions">{requests.filter((r) => r.status === "SUBMITTED").slice(0, 8).map((r) => <button key={r.id} className="button secondary" onClick={() => void act(() => changeRequestStatus(token, r.id, "TRIAGED"))}>{t.triage}: {r.title}</button>)}</div>}
      </section>{profile.role === "CUSTOMER" && <form className="card form-card" onSubmit={createRequestForm}><p className="eyebrow">SERVICE DESK</p><h2>{t.newRequest}</h2><label>{t.title}<input className="input" name="title" minLength={5} maxLength={120} required /></label><label>{t.description}<textarea className="input" name="description" minLength={20} maxLength={3000} rows={5} required /></label><button className="button primary" disabled={busy}>{t.create} <span>↗</span></button></form>}</div>}
      {section === "estimates" && <EstimateSection language={language} token={token} role={profile.role} requests={requests} estimates={estimates} act={act} t={t} />}
      {section === "technicians" && <section className="card section-card"><div className="section-heading"><h2>{t.technicians}</h2><span className="badge">{technicians.length}</span></div>{technicians.length ? <div className="team-grid">{technicians.map((tech) => <article className="team-card" key={tech.id}><div className="avatar large">{tech.name.slice(0, 1)}</div><div><strong>{tech.name}</strong><p className="muted">{tech.active ? (language === "ru" ? "Активен" : "Active") : (language === "ru" ? "Неактивен" : "Inactive")}</p></div><span className="badge">{tech.id.slice(0, 8)}</span></article>)}</div> : <p className="muted">{t.noTechs}</p>}</section>}
      {section === "schedule" && <ScheduleSection language={language} token={token} requests={requests} technicians={technicians} assignments={assignments} act={act} t={t} />}
      {section === "inventory" && <InventorySection token={token} role={profile.role} inventory={inventory} act={act} t={t} />}
      {section === "tasks" && <TaskSection token={token} tasks={myAssignments} requests={requests} act={act} language={language} t={t} />}
    </section>
  </main>;
}

function Stat({ label, value, icon }: { label: string; value: number; icon: string }) {
  return <article className="stat-card"><div className="stat-top"><span>{label}</span><span className="stat-icon">{icon}</span></div><strong>{value}</strong></article>;
}

function RequestTable({ items, language, labels }: { items: RequestItem[]; language: Language; labels: Record<string, string> }) {
  if (!items.length) return <div className="empty-state"><span>○</span><p>{labels.empty}</p></div>;
  return <div className="table-wrap"><table className="data-table"><thead><tr><th>{labels.request || labels.title}</th><th>{labels.status}</th><th>{labels.priority}</th><th>{labels.created}</th></tr></thead><tbody>{items.map((item) => <tr key={item.id}><td><strong>{item.title}</strong><small>{item.description}</small></td><td><span className={`badge status-${item.status.toLowerCase()}`}>{statusText[language][item.status] || item.status}</span></td><td>{item.priority}</td><td>{new Date(item.created_at).toLocaleDateString(language === "ru" ? "ru-RU" : "en-US")}</td></tr>)}</tbody></table></div>;
}

function EstimateSection({ language, token, role, requests, estimates, act, t }: {
  language: Language; token: string; role: Role; requests: RequestItem[]; estimates: Estimate[];
  act: (action: () => Promise<unknown>) => Promise<void>; t: Record<string, string>;
}) {
  const managerial = managerRoles.includes(role);
  const owned = requests.map((request) => ({ request, estimates: estimates.filter((item) => item.request_id === request.id) }));
  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const data = new FormData(event.currentTarget); const form = event.currentTarget;
    await act(async () => { await createEstimate(token, String(data.get("request_id")), crypto.randomUUID(), Number(data.get("price")), String(data.get("description"))); form.reset(); });
  }
  return <div className="content-grid"><section className="card section-card"><div className="section-heading"><h2>{t.estimates}</h2></div>{owned.flatMap(({ request, estimates: versions }) => versions.map((estimate) => <article className="estimate-card" key={estimate.id}><div><div className="estimate-title"><strong>{request.title}</strong><span className="badge">{t.version} {estimate.version}</span><span className={`badge status-${estimate.status.toLowerCase()}`}>{statusText[language][estimate.status] || estimate.status}</span></div><p className="muted">{estimate.comment || estimate.lines.map((line) => line.description).join(", ")}</p><strong>{(estimate.total_tyiyn / 100).toLocaleString(language === "ru" ? "ru-RU" : "en-US", { style: "currency", currency: "KGS" })}</strong></div><div className="button-row">{managerial && estimate.status === "DRAFT" && <button className="button secondary" onClick={() => void act(() => submitEstimate(token, estimate.id))}>{t.submitEstimate}</button>}{role === "CUSTOMER" && estimate.status === "AWAITING_APPROVAL" && <><button className="button primary" onClick={() => void act(() => decideEstimate(token, estimate.id, true))}>{t.approve}</button><button className="button danger" onClick={() => void act(() => decideEstimate(token, estimate.id, false))}>{t.reject}</button></>}</div></article>))}{!estimates.length && <div className="empty-state"><span>◇</span><p>{t.empty}</p></div>}</section>{managerial && <form className="card form-card" onSubmit={create}><p className="eyebrow">ESTIMATE</p><h2>{t.newEstimate}</h2><label>{t.request}<select className="input" name="request_id" required>{requests.map((request) => <option key={request.id} value={request.id}>{request.title}</option>)}</select></label><label>{t.line}<input className="input" name="description" minLength={2} maxLength={500} required /></label><label>{t.amount}<input className="input" name="price" type="number" min={0} step={1} required /></label><button className="button primary">{t.create}</button></form>}</div>;
}

function ScheduleSection({ language, token, requests, technicians, assignments, act, t }: {
  language: Language; token: string; requests: RequestItem[]; technicians: Technician[]; assignments: Awaited<ReturnType<typeof getAssignments>>;
  act: (action: () => Promise<unknown>) => Promise<void>; t: Record<string, string>;
}) {
  async function schedule(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const data = new FormData(event.currentTarget); const form = event.currentTarget;
    await act(() => scheduleAssignment(token, String(data.get("request_id")), String(data.get("technician_id")), new Date(String(data.get("starts_at"))).toISOString(), new Date(String(data.get("ends_at"))).toISOString()).then((value) => { form.reset(); return value; }));
  }
  return <div className="content-grid"><section className="card section-card"><div className="section-heading"><h2>{t.schedule}</h2><span className="badge">{assignments.length}</span></div>{assignments.length ? <div className="schedule-list">{assignments.map((assignment) => <article className="schedule-item" key={assignment.id}><div className="schedule-date"><strong>{new Date(assignment.starts_at).toLocaleDateString(language === "ru" ? "ru-RU" : "en-US", { day: "2-digit", month: "short" })}</strong><small>{new Date(assignment.starts_at).toLocaleTimeString(language === "ru" ? "ru-RU" : "en-US", { hour: "2-digit", minute: "2-digit" })}</small></div><div><strong>{assignment.request_title}</strong><p className="muted">{assignment.technician_name} · {new Date(assignment.ends_at).toLocaleTimeString(language === "ru" ? "ru-RU" : "en-US", { hour: "2-digit", minute: "2-digit" })}</p></div><span className="badge">{statusText[language][assignment.status] || assignment.status}</span></article>)}</div> : <div className="empty-state"><span>◷</span><p>{t.noSchedule}</p></div>}</section><form className="card form-card" onSubmit={schedule}><p className="eyebrow">DISPATCH</p><h2>{t.assign}</h2><label>{t.request}<select className="input" name="request_id" required>{requests.filter((r) => r.status === "TRIAGED").map((request) => <option key={request.id} value={request.id}>{request.title}</option>)}</select></label><label>{t.technicians}<select className="input" name="technician_id" required>{technicians.map((tech) => <option key={tech.id} value={tech.id}>{tech.name}</option>)}</select></label><label>{t.start}<input className="input" name="starts_at" type="datetime-local" required /></label><label>{t.end}<input className="input" name="ends_at" type="datetime-local" required /></label><button className="button primary">{t.scheduleButton}</button></form></div>;
}

function InventorySection({ token, role, inventory, act, t }: {
  token: string; role: Role; inventory: InventoryItem[]; act: (action: () => Promise<unknown>) => Promise<void>; t: Record<string, string>;
}) {
  async function add(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const data = new FormData(event.currentTarget); const form = event.currentTarget;
    await act(() => createInventoryItem(token, { sku: String(data.get("sku")), name: String(data.get("name")), unit: String(data.get("unit")), minimum_quantity: Number(data.get("minimum")) }).then((item) => { form.reset(); return item; }));
  }
  async function movement(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const data = new FormData(event.currentTarget); const form = event.currentTarget;
    await act(() => recordStockMovement(token, String(data.get("item_id")), Number(data.get("quantity")), String(data.get("reason")), crypto.randomUUID()).then((result) => { form.reset(); return result; }));
  }
  return <div className="content-grid"><section className="card section-card"><div className="section-heading"><h2>{t.inventory}</h2><span className="badge">{inventory.length}</span></div><div className="table-wrap"><table className="data-table"><thead><tr><th>{t.itemName}</th><th>{t.sku}</th><th>{t.quantity}</th><th>{t.min}</th></tr></thead><tbody>{inventory.map((item) => <tr key={item.id}><td><strong>{item.name}</strong><small>{item.unit}</small></td><td>{item.sku}</td><td><span className={item.quantity_on_hand <= item.minimum_quantity ? "stock-low" : "stock-good"}>{item.quantity_on_hand}</span></td><td>{item.minimum_quantity}</td></tr>)}</tbody></table></div></section><div className="form-stack">{role === "ORGANIZATION_ADMIN" && <form className="card form-card" onSubmit={add}><p className="eyebrow">CATALOG</p><h2>{t.newItem}</h2><label>{t.sku}<input className="input" name="sku" required /></label><label>{t.itemName}<input className="input" name="name" minLength={2} required /></label><label>{t.unit}<input className="input" name="unit" required /></label><label>{t.min}<input className="input" name="minimum" type="number" min={0} defaultValue={0} required /></label><button className="button primary">{t.add}</button></form>}{inventory.length > 0 && <form className="card form-card" onSubmit={movement}><p className="eyebrow">STOCK</p><h2>{t.stockMovement}</h2><label>{t.itemName}<select className="input" name="item_id">{inventory.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label><label>{t.quantity}<input className="input" name="quantity" type="number" step={1} required /></label><label>{t.reason}<input className="input" name="reason" minLength={3} required /></label><button className="button primary">{t.save}</button></form>}</div></div>;
}

function TaskSection({ token, tasks, requests, act, language, t }: {
  token: string; tasks: Awaited<ReturnType<typeof getMyAssignments>>; act: (action: () => Promise<unknown>) => Promise<void>;
  requests: RequestItem[]; language: Language; t: Record<string, string>;
}) {
  return <section className="card section-card"><div className="section-heading"><h2>{t.tasks}</h2><span className="badge">{tasks.length}</span></div>{tasks.map((task) => { const request = requests.find((item) => item.id === task.request_id); return <article className="task-card" key={task.id}><div><p className="eyebrow">{statusText[language][request?.status || task.status] || request?.status || task.status}</p><strong>{request?.title || task.request_id}</strong><p className="muted">{new Date(task.starts_at).toLocaleString(language === "ru" ? "ru-RU" : "en-US")}</p></div><div className="button-row">{task.status === "OFFERED" && <button className="button primary" onClick={() => void act(() => acceptAssignment(token, task.id))}>{t.accept}</button>}{task.status === "ACCEPTED" && request?.status === "ACCEPTED" && <button className="button secondary" onClick={() => void act(() => changeRequestStatus(token, task.request_id, "IN_PROGRESS"))}>{t.startWork}</button>}{task.status === "ACCEPTED" && request?.status === "IN_PROGRESS" && <button className="button primary" onClick={() => void act(() => changeRequestStatus(token, task.request_id, "COMPLETED"))}>{t.complete}</button>}</div></article>;})}{!tasks.length && <div className="empty-state"><span>✓</span><p>{t.empty}</p></div>}</section>;
}

// Keep API requests on the same origin as the web app. Next.js proxies this
// path to the backend, so localhost/LAN access and browser CORS stay consistent.
const API = "/api/v1";

export class ApiError extends Error {
  constructor(message: string, readonly status?: number) {
    super(message);
    this.name = "ApiError";
  }
}

export type Role = "CUSTOMER" | "DISPATCHER" | "ORGANIZATION_ADMIN" | "TECHNICIAN";
export type UserProfile = { id: string; name: string; email: string; role: Role };
export type RequestItem = {
  id: string;
  title: string;
  description: string;
  priority: string;
  status: string;
  created_at: string;
  service_address?: string | null;
  desired_visit_at?: string | null;
  property_id?: string | null;
  asset_id?: string | null;
  category_id?: string | null;
};
export type Page<T> = { items: T[]; page: number; page_size: number; total: number };
export type Assignment = {
  id: string; request_id: string; technician_id: string; starts_at: string; ends_at: string;
  status: string; created_at: string; request_title?: string; technician_name?: string;
};
export type Technician = { id: string; user_id: string; name: string; active: boolean };
export type Estimate = {
  id: string; request_id: string; version: number; previous_version_id: string | null;
  status: string; total_tyiyn: number; comment: string | null; created_at: string;
  decided_at: string | null; lines: { kind: string; description: string; quantity: number; unit_price_tyiyn: number }[];
};
export type InventoryItem = {
  id: string; sku: string; name: string; unit: string; quantity_on_hand: number; minimum_quantity: number;
};

async function call<T>(path: string, token?: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (init.body && !(init.body instanceof FormData)) headers.set("Content-Type", "application/json");
  let response: Response;
  try {
    response = await fetch(`${API}${path}`, { ...init, headers, cache: "no-store" });
  } catch (cause) {
    if (cause instanceof TypeError) {
      throw new ApiError("API_UNAVAILABLE");
    }
    throw cause;
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new ApiError(typeof body.detail === "string" ? body.detail : `Request failed (${response.status})`, response.status);
  }
  return response.json() as Promise<T>;
}

export async function login(email: string, password: string, organizationId?: string): Promise<string> {
  const body = await call<{ access_token: string }>("/auth/login", undefined, {
    method: "POST", body: JSON.stringify({ email, password, ...(organizationId ? { organization_id: organizationId } : {}) }),
  });
  return body.access_token;
}

export function registerCustomer(input: { email: string; password: string }) {
  return call<{ id: string; email: string; role: Role }>("/auth/register", undefined, {
    method: "POST", body: JSON.stringify(input),
  });
}

export function getMe(token: string) { return call<UserProfile>("/auth/me", token); }

export async function getRequests(token: string, search = ""): Promise<RequestItem[]> {
  const first = await call<Page<RequestItem>>(`/requests?page=1&page_size=100&search=${encodeURIComponent(search)}`, token);
  const pages = await Promise.all(Array.from({ length: Math.ceil(first.total / 100) - 1 }, (_, index) =>
    call<Page<RequestItem>>(`/requests?page=${index + 2}&page_size=100&search=${encodeURIComponent(search)}`, token)));
  return [first, ...pages].flatMap((page) => page.items);
}

export function createRequest(token: string, input: {
  title: string; description: string; service_address?: string; priority: string; desired_visit_at?: string; property_id?: string; asset_id?: string; category_id?: string;
}, idempotencyKey: string) {
  return call<RequestItem>("/requests", token, {
    method: "POST", headers: { "Idempotency-Key": idempotencyKey }, body: JSON.stringify(input),
  });
}

export function changeRequestStatus(token: string, requestId: string, status: string) {
  return call<RequestItem>(`/requests/${requestId}/status`, token, {
    method: "PATCH", body: JSON.stringify({ status }),
  });
}

export function getTechnicians(token: string) { return call<Technician[]>("/technicians", token); }
export function getAssignments(token: string) { return call<Assignment[]>("/assignments", token); }
export function getMyAssignments(token: string) { return call<Assignment[]>("/technician/assignments", token); }
export function scheduleAssignment(token: string, requestId: string, technicianId: string, startsAt: string, endsAt: string) {
  return call<Assignment>(`/requests/${requestId}/assignments`, token, {
    method: "POST", body: JSON.stringify({ technician_id: technicianId, starts_at: startsAt, ends_at: endsAt }),
  });
}
export function acceptAssignment(token: string, assignmentId: string) {
  return call<Assignment>(`/assignments/${assignmentId}/accept`, token, { method: "POST" });
}

export function getEstimates(token: string, requestId: string) {
  return call<Estimate[]>(`/requests/${requestId}/estimates`, token);
}
export function createEstimate(token: string, requestId: string, idempotencyKey: string, price: number, description: string) {
  return call<Estimate>(`/requests/${requestId}/estimates`, token, {
    method: "POST", headers: { "Idempotency-Key": idempotencyKey },
    body: JSON.stringify({ comment: "", lines: [{ kind: "LABOR", description, quantity: 1, unit_price_tyiyn: price }] }),
  });
}
export function submitEstimate(token: string, estimateId: string) {
  return call<Estimate>(`/estimates/${estimateId}/submit`, token, { method: "POST" });
}
export function decideEstimate(token: string, estimateId: string, approved: boolean) {
  return call<Estimate>(`/estimates/${estimateId}/decision`, token, {
    method: "POST", body: JSON.stringify({ approved }),
  });
}

export function getInventory(token: string) { return call<InventoryItem[]>("/inventory/items", token); }
export function createInventoryItem(token: string, input: { sku: string; name: string; unit: string; minimum_quantity: number }) {
  return call<InventoryItem>("/inventory/items", token, { method: "POST", body: JSON.stringify(input) });
}
export function recordStockMovement(token: string, itemId: string, quantity_delta: number, reason: string, idempotencyKey: string) {
  return call(`/inventory/items/${itemId}/movements`, token, {
    method: "POST", headers: { "Idempotency-Key": idempotencyKey }, body: JSON.stringify({ quantity_delta, reason }),
  });
}

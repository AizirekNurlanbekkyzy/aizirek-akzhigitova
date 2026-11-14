const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export type RequestItem = { id: string; title: string; description: string; priority: string; status: string; created_at: string };
export type Page<T> = { items: T[]; page: number; page_size: number; total: number };

export async function login(email: string, password: string, organizationId: string): Promise<string> {
  const response = await fetch(`${API}/auth/login`, { method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, organization_id: organizationId }) });
  const body = await response.json();
  if (!response.ok) throw new Error(body.detail ?? "Sign in failed");
  return body.access_token as string;
}

export async function getRequests(token: string, search = ""): Promise<Page<RequestItem>> {
  const response = await fetch(`${API}/requests?search=${encodeURIComponent(search)}`, { headers: { Authorization: `Bearer ${token}` }, cache: "no-store" });
  if (!response.ok) throw new Error((await response.json()).detail ?? "Could not load requests");
  return response.json() as Promise<Page<RequestItem>>;
}

export async function createRequest(token: string, input: { title: string; description: string; priority: string }, idempotencyKey: string): Promise<RequestItem> {
  const response = await fetch(`${API}/requests`, { method: "POST", headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json", "Idempotency-Key": idempotencyKey }, body: JSON.stringify(input) });
  const body = await response.json();
  if (!response.ok) throw new Error(body.detail ?? "Could not create request");
  return body as RequestItem;
}

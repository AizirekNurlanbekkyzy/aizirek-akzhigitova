import { describe, expect, it, mock } from "bun:test";
import { getRequests } from "../src/lib/api";

describe("requests API client", () => {
  it("sends bearer authorization and returns the server page", async () => {
    const oldFetch = globalThis.fetch;
    globalThis.fetch = mock(async (_input: RequestInfo | URL, init?: RequestInit) => {
      expect(new Headers(init?.headers).get("Authorization")).toBe("Bearer token-1");
      return Response.json({ items: [], page: 1, page_size: 20, total: 0 });
    }) as typeof fetch;
    try {
      expect(await getRequests("token-1")).toEqual({ items: [], page: 1, page_size: 20, total: 0 });
    } finally { globalThis.fetch = oldFetch; }
  });
});

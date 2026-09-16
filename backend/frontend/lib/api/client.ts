/**
 * Knowra — Centralized API Client
 * Handles JWT injection, silent token refresh on 401, and typed error responses.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

// ─── Session Storage Keys ──────────────────────────────────────────────────────
const ACCESS_TOKEN_KEY = "knowra_access_token";
const REFRESH_TOKEN_KEY = "knowra_refresh_token";

// ─── Error Type ───────────────────────────────────────────────────────────────
export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
    public readonly detail?: unknown
  ) {
    super(message);
    this.name = "ApiError";
  }
}

// ─── Cookie Helpers ───────────────────────────────────────────────────────────
function setCookie(name: string, value: string, maxAgeSec: number = 604800) {
  if (typeof document !== "undefined") {
    document.cookie = `${name}=${encodeURIComponent(value)}; path=/; max-age=${maxAgeSec}; SameSite=Lax`;
  }
}

function removeCookie(name: string) {
  if (typeof document !== "undefined") {
    document.cookie = `${name}=; path=/; max-age=0; SameSite=Lax`;
  }
}

// ─── Token Management ─────────────────────────────────────────────────────────
export const tokenStore = {
  getAccessToken(): string | null {
    if (typeof window === "undefined") return null;
    return localStorage.getItem(ACCESS_TOKEN_KEY);
  },
  getRefreshToken(): string | null {
    if (typeof window === "undefined") return null;
    return localStorage.getItem(REFRESH_TOKEN_KEY);
  },
  setTokens(access: string, refresh: string): void {
    localStorage.setItem(ACCESS_TOKEN_KEY, access);
    localStorage.setItem(REFRESH_TOKEN_KEY, refresh);
    setCookie(ACCESS_TOKEN_KEY, access);
  },
  clearTokens(): void {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    localStorage.removeItem("knowra_session");
    removeCookie(ACCESS_TOKEN_KEY);
  },
};

// ─── Token Refresh ────────────────────────────────────────────────────────────
let refreshPromise: Promise<string> | null = null;

async function refreshAccessToken(): Promise<string> {
  if (refreshPromise) return refreshPromise;

  refreshPromise = (async () => {
    const refreshToken = tokenStore.getRefreshToken();
    if (!refreshToken) {
      tokenStore.clearTokens();
      throw new ApiError(401, "NO_REFRESH_TOKEN", "Session expired. Please log in again.");
    }

    const res = await fetch(`${API_BASE}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (!res.ok) {
      tokenStore.clearTokens();
      throw new ApiError(401, "REFRESH_FAILED", "Session expired. Please log in again.");
    }

    const data = await res.json();
    tokenStore.setTokens(data.access_token, data.refresh_token ?? refreshToken);
    return data.access_token as string;
  })().finally(() => {
    refreshPromise = null;
  });

  return refreshPromise;
}

// ─── Core Request ─────────────────────────────────────────────────────────────
interface RequestOptions extends RequestInit {
  skipAuth?: boolean;
  _isRetry?: boolean;
}

export async function apiRequest<T = unknown>(
  path: string,
  options: RequestOptions = {}
): Promise<T> {
  const { skipAuth = false, _isRetry = false, ...fetchOptions } = options;

  const headers = new Headers(fetchOptions.headers);
  headers.set("Content-Type", "application/json");

  if (!skipAuth) {
    const token = tokenStore.getAccessToken();
    if (token) headers.set("Authorization", `Bearer ${token}`);
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...fetchOptions,
    headers,
  });

  // Silent token refresh on first 401
  if (res.status === 401 && !_isRetry && !skipAuth) {
    try {
      const newToken = await refreshAccessToken();
      headers.set("Authorization", `Bearer ${newToken}`);
      const retryRes = await fetch(`${API_BASE}${path}`, {
        ...fetchOptions,
        headers,
      });
      if (!retryRes.ok) await throwApiError(retryRes);
      return retryRes.json() as Promise<T>;
    } catch {
      tokenStore.clearTokens();
      if (typeof window !== "undefined") window.location.href = "/login";
      throw new ApiError(401, "SESSION_EXPIRED", "Session expired.");
    }
  }

  if (!res.ok) await throwApiError(res);

  // 204 No Content
  if (res.status === 204) return undefined as T;

  return res.json() as Promise<T>;
}

async function throwApiError(res: Response): Promise<never> {
  let body: { detail?: string; code?: string } = {};
  try {
    body = await res.json();
  } catch {
    /* non-JSON error body */
  }
  throw new ApiError(
    res.status,
    body.code ?? "API_ERROR",
    body.detail ?? `Request failed with status ${res.status}`,
    body
  );
}

// ─── HTTP Helpers ─────────────────────────────────────────────────────────────
export const api = {
  get<T>(path: string, opts?: RequestOptions): Promise<T> {
    return apiRequest<T>(path, { method: "GET", ...opts });
  },
  post<T>(path: string, body?: unknown, opts?: RequestOptions): Promise<T> {
    return apiRequest<T>(path, {
      method: "POST",
      body: body !== undefined ? JSON.stringify(body) : undefined,
      ...opts,
    });
  },
  put<T>(path: string, body?: unknown, opts?: RequestOptions): Promise<T> {
    return apiRequest<T>(path, {
      method: "PUT",
      body: body !== undefined ? JSON.stringify(body) : undefined,
      ...opts,
    });
  },
  patch<T>(path: string, body?: unknown, opts?: RequestOptions): Promise<T> {
    return apiRequest<T>(path, {
      method: "PATCH",
      body: body !== undefined ? JSON.stringify(body) : undefined,
      ...opts,
    });
  },
  delete<T>(path: string, opts?: RequestOptions): Promise<T> {
    return apiRequest<T>(path, { method: "DELETE", ...opts });
  },
};

// ─── Streaming SSE Helper ─────────────────────────────────────────────────────
export async function* apiStream(
  path: string,
  body: unknown
): AsyncGenerator<string> {
  const token = tokenStore.getAccessToken();
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(body),
  });

  if (!res.ok || !res.body) {
    await throwApiError(res);
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    const chunk = decoder.decode(value, { stream: true });
    // Parse SSE lines: "data: ..."
    for (const line of chunk.split("\n")) {
      if (line.startsWith("data: ")) {
        const payload = line.slice(6).trim();
        if (payload && payload !== "[DONE]") yield payload;
      }
    }
  }
}

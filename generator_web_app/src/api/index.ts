// Universal REST API Service
// Author: Michael B. Lance / Antigravity
// ---------------------------------------------------------------------------------------------------------------------------

export const API_BASE: string =
  import.meta.env.VITE_API_URL || "https://pronghorn-count.arcc.uwyo.edu/api/v1";

// ---------------------------------------------------------------------------------------------------------------------------
// Core Request Dispatcher

async function request<T>(
  path: string,
  init: RequestInit = {},
  params?: Record<string, any>,
): Promise<T> {
  const query = params ? `?${new URLSearchParams(params)}` : "";
  const res = await fetch(`${API_BASE}/${path}${query}`, {
    credentials: "include",
    headers: {
      ...(!(init.body instanceof FormData) && { "Content-Type": "application/json" }),
      ...init.headers,
    },
    ...init,
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.message || `HTTP ${res.status} ${res.statusText}`);
  }

  return res.status === 204 ? (undefined as T) : res.json();
}

// ---------------------------------------------------------------------------------------------------------------------------
// Clean REST Client

export const api = {
  get<T>(path: string, params?: Record<string, any>): Promise<T> {
    return request<T>(path, { method: "GET" }, params);
  },

  post<T, B = any>(path: string, body?: B): Promise<T> {
    return request<T>(path, {
      method: "POST",
      body: body instanceof FormData ? body : JSON.stringify(body),
    });
  },

  patch<T, B = any>(path: string, body?: B): Promise<T> {
    return request<T>(path, {
      method: "PATCH",
      body: body instanceof FormData ? body : JSON.stringify(body),
    });
  },

  async delete<B = any>(path: string, body?: B): Promise<boolean> {
    await request(path, {
      method: "DELETE",
      ...(body !== undefined && {
        body: body instanceof FormData ? body : JSON.stringify(body),
      }),
    });
    return true;
  },
};

export default api;

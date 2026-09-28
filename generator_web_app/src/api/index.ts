// Universal REST API Service
// Author: Michael B. Lance / Antigravity
// ---------------------------------------------------------------------------------------------------------------------------

export const API_BASE: string =
  import.meta.env.VITE_API_URL || "https://pronghorn-count.arcc.uwyo.edu/api/v1";

// ---------------------------------------------------------------------------------------------------------------------------
// Core Request Dispatcher

function buildQueryString(params?: Record<string, any>): string {
  if (!params) return "";
  const sp = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === "") continue;
    if (Array.isArray(value)) {
      for (const item of value) {
        if (item !== undefined && item !== null && item !== "") {
          sp.append(key, String(item));
        }
      }
    } else {
      sp.append(key, String(value));
    }
  }
  const str = sp.toString();
  return str ? `?${str}` : "";
}

async function request<T>(
  path: string,
  init: RequestInit = {},
  params?: Record<string, any>,
): Promise<T> {
  const query = buildQueryString(params);
  const res = await fetch(`${API_BASE}/${path}${query}`, {
    credentials: "include",
    headers: {
      ...(!(init.body instanceof FormData) && { "Content-Type": "application/json" }),
      ...init.headers,
    },
    ...init,
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    let errMsg = `HTTP ${res.status} ${res.statusText}`;
    if (text) {
      try {
        const body = JSON.parse(text);
        errMsg = body.message || body.error || errMsg;
      } catch {
        errMsg = text;
      }
    }
    throw new Error(errMsg);
  }

  const text = await res.text();
  if (!text || text.trim() === "") {
    return undefined as T;
  }
  try {
    return JSON.parse(text) as T;
  } catch {
    return text as unknown as T;
  }
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

  all: Promise.all.bind(Promise),
  allSettled: Promise.allSettled.bind(Promise),
};

// Ergonomic helper: enable fetch.all() globally
if (typeof window !== "undefined" && window.fetch) {
  (window.fetch as any).all = Promise.all.bind(Promise);
  (window.fetch as any).allSettled = Promise.allSettled.bind(Promise);
}

export default api;

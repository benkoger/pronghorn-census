// Templated REST API Client mirroring the backend database abstraction pattern
// Author: Michael B. Lance / Antigravity
// ---------------------------------------------------------------------------------------------------------------------------

import { ApiError, type apiError } from "./errors";
import type { PrimaryKey } from "@/types/models/base";

export const api_url_base: string =
  import.meta.env.VITE_API_URL || "https://pronghorn-count.arcc.uwyo.edu/api/v1";

export const api_url: URL = new URL(api_url_base);

export type ModelConstructor<T> = new (data: any, ...args: any[]) => T;

export interface RequestOptions extends Omit<RequestInit, "body"> {
  params?: Record<string, any>;
  body?: any;
}

// ---------------------------------------------------------------------------------------------------------------------------
// URL & Query Utilities

export function buildUrl(endpoint: string, params?: Record<string, any>): string {
  let fullUrl: string;

  if (endpoint.startsWith("http://") || endpoint.startsWith("https://")) {
    fullUrl = endpoint;
  } else {
    const cleanBase = api_url.origin + api_url.pathname.replace(/\/+$/, "");
    const cleanPath = endpoint.replace(/^\/+/, "");
    fullUrl = `${cleanBase}/${cleanPath}`;
  }

  if (params && Object.keys(params).length > 0) {
    const searchParams = new URLSearchParams();
    for (const [key, value] of Object.entries(params)) {
      if (value === undefined || value === null) continue;

      if (Array.isArray(value)) {
        for (const item of value) {
          if (item !== undefined && item !== null) {
            searchParams.append(key, String(item));
          }
        }
      } else {
        searchParams.append(key, String(value));
      }
    }
    const queryString = searchParams.toString();
    if (queryString) {
      fullUrl += (fullUrl.includes("?") ? "&" : "?") + queryString;
    }
  }

  return fullUrl;
}

// ---------------------------------------------------------------------------------------------------------------------------
// Core Request Handler

async function request<T = any>(
  endpoint: string,
  options: RequestOptions = {},
): Promise<T> {
  const { params, body, headers, ...customConfig } = options;
  const url = buildUrl(endpoint, params);

  const requestHeaders: HeadersInit = {
    ...(!(body instanceof FormData) && { "Content-Type": "application/json" }),
    ...headers,
  };

  const config: RequestInit = {
    method: options.method || "GET",
    credentials: "include",
    headers: requestHeaders,
    ...customConfig,
  };

  if (body !== undefined) {
    config.body =
      body instanceof FormData || typeof body === "string"
        ? body
        : JSON.stringify(body);
  }

  const response = await fetch(url, config);

  if (!response.ok) {
    let errorData: apiError;
    try {
      errorData = await response.json();
    } catch {
      errorData = {
        error: response.statusText || "Request Failed",
        message: `HTTP ${response.status} ${response.statusText}`,
        code: response.status,
      };
    }
    throw new ApiError(errorData);
  }

  if (response.status === 204) {
    return undefined as unknown as T;
  }

  const contentType = response.headers.get("content-type");
  if (contentType && contentType.includes("application/json")) {
    return await response.json();
  }

  return (await response.text()) as unknown as T;
}

// ---------------------------------------------------------------------------------------------------------------------------
// Templated API Client Operations

function instantiate<T>(data: any, model?: ModelConstructor<T>): T {
  if (!model || data === null || data === undefined) {
    return data as T;
  }
  if (Array.isArray(data)) {
    return data.map((item) => new model(item)) as unknown as T;
  }
  return new model(data);
}

export const apiClient = {
  request,

  async get<T>(
    endpoint: string,
    idOrSubpath?: PrimaryKey,
    model?: ModelConstructor<T>,
    params?: Record<string, any>,
    options?: RequestOptions,
  ): Promise<T> {
    const path =
      idOrSubpath !== undefined && idOrSubpath !== ""
        ? `${endpoint}/${idOrSubpath}`
        : endpoint;
    const data = await request<any>(path, { method: "GET", params, ...options });
    return instantiate(data, model);
  },

  async getAll<T>(
    endpoint: string,
    model?: ModelConstructor<T>,
    params?: Record<string, any>,
    options?: RequestOptions,
  ): Promise<T[]> {
    const data = await request<any[]>(endpoint, {
      method: "GET",
      params,
      ...options,
    });
    if (!Array.isArray(data)) {
      return [];
    }
    return model ? data.map((item) => new model(item)) : data;
  },

  async getChildren<T>(
    parentEndpoint: string,
    parentId: PrimaryKey,
    childEndpoint: string,
    model?: ModelConstructor<T>,
    params?: Record<string, any>,
    options?: RequestOptions,
  ): Promise<T[]> {
    const path = `${parentEndpoint}/${parentId}/${childEndpoint}`;
    const data = await request<any[]>(path, {
      method: "GET",
      params,
      ...options,
    });
    if (!Array.isArray(data)) {
      return [];
    }
    return model ? data.map((item) => new model(item)) : data;
  },

  async insert<T, B = any>(
    endpoint: string,
    body: B,
    model?: ModelConstructor<T>,
    options?: RequestOptions,
  ): Promise<T> {
    const data = await request<any>(endpoint, {
      method: "POST",
      body,
      ...options,
    });
    return instantiate(data, model);
  },

  async update<T, B = any>(
    endpoint: string,
    idOrBody: PrimaryKey | B,
    body?: B,
    model?: ModelConstructor<T>,
    options?: RequestOptions,
  ): Promise<T> {
    let path = endpoint;
    let payload = idOrBody;

    if (body !== undefined) {
      path = `${endpoint}/${idOrBody}`;
      payload = body;
    }

    const data = await request<any>(path, {
      method: "PATCH",
      body: payload,
      ...options,
    });
    return instantiate(data, model);
  },

  async delete(
    endpoint: string,
    id?: PrimaryKey,
    options?: RequestOptions,
  ): Promise<boolean> {
    const path = id !== undefined && id !== "" ? `${endpoint}/${id}` : endpoint;
    await request<any>(path, { method: "DELETE", ...options });
    return true;
  },

  async post<T, B = any>(
    endpoint: string,
    body?: B,
    model?: ModelConstructor<T>,
    options?: RequestOptions,
  ): Promise<T> {
    const data = await request<any>(endpoint, {
      method: "POST",
      body,
      ...options,
    });
    return instantiate(data, model);
  },

  async patch<T, B = any>(
    endpoint: string,
    body?: B,
    model?: ModelConstructor<T>,
    options?: RequestOptions,
  ): Promise<T> {
    const data = await request<any>(endpoint, {
      method: "PATCH",
      body,
      ...options,
    });
    return instantiate(data, model);
  },

  async put<T, B = any>(
    endpoint: string,
    body?: B,
    model?: ModelConstructor<T>,
    options?: RequestOptions,
  ): Promise<T> {
    const data = await request<any>(endpoint, {
      method: "PUT",
      body,
      ...options,
    });
    return instantiate(data, model);
  },

  createResourceClient<T, CreateReq = any, UpdateReq = any>(
    endpoint: string,
    model?: ModelConstructor<T>,
  ) {
    return {
      endpoint,
      get: (id: PrimaryKey, options?: RequestOptions) =>
        this.get<T>(endpoint, id, model, undefined, options),
      getAll: (params?: Record<string, any>, options?: RequestOptions) =>
        this.getAll<T>(endpoint, model, params, options),
      getChildren: <C>(
        id: PrimaryKey,
        childEndpoint: string,
        childModel?: ModelConstructor<C>,
        params?: Record<string, any>,
        options?: RequestOptions,
      ) =>
        this.getChildren<C>(
          endpoint,
          id,
          childEndpoint,
          childModel,
          params,
          options,
        ),
      create: (data: CreateReq, options?: RequestOptions) =>
        this.insert<T, CreateReq>(endpoint, data, model, options),
      update: (
        idOrBody: PrimaryKey | UpdateReq,
        data?: UpdateReq,
        options?: RequestOptions,
      ) =>
        this.update<T, UpdateReq>(endpoint, idOrBody, data, model, options),
      delete: (id?: PrimaryKey, options?: RequestOptions) =>
        this.delete(endpoint, id, options),
    };
  },
};

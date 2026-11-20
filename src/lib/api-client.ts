/**
 * FLOWSTATE Centralized API Client
 * Connects Next.js Frontend to FastAPI Backend
 */

import { isValidUuid, DEFAULT_ORG_ID } from './utils';

export class ApiError extends Error {
  status: number;
  code: string;
  details?: any;

  constructor(status: number, code: string, message: string, details?: any) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

interface RequestOptions extends Omit<RequestInit, 'body'> {
  params?: Record<string, string | number | boolean | undefined | null>;
  skipOrgHeader?: boolean;
}

const STORAGE_KEY_TOKEN = 'flowstate_auth_token';
const STORAGE_KEY_ORG = 'flowstate_active_org_id';

class ApiClient {
  private baseUrl: string;

  constructor() {
    this.baseUrl = (
      process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'
    ).replace(/\/+$/, '');
  }

  public getBaseUrl(): string {
    return this.baseUrl;
  }

  public getAuthToken(): string | null {
    if (typeof window === 'undefined') return null;
    return localStorage.getItem(STORAGE_KEY_TOKEN);
  }

  public setAuthToken(token: string | null): void {
    if (typeof window === 'undefined') return;
    if (token) {
      localStorage.setItem(STORAGE_KEY_TOKEN, token);
    } else {
      localStorage.removeItem(STORAGE_KEY_TOKEN);
    }
  }

  public getActiveOrgId(): string | null {
    if (typeof window === 'undefined') return null;
    const stored = localStorage.getItem(STORAGE_KEY_ORG);
    if (!stored || stored === 'org_default' || !isValidUuid(stored)) {
      localStorage.setItem(STORAGE_KEY_ORG, DEFAULT_ORG_ID);
      return DEFAULT_ORG_ID;
    }
    return stored;
  }

  public setActiveOrgId(orgId: string | null): void {
    if (typeof window === 'undefined') return;
    if (orgId) {
      localStorage.setItem(STORAGE_KEY_ORG, orgId);
    } else {
      localStorage.removeItem(STORAGE_KEY_ORG);
    }
  }

  private buildUrl(endpoint: string, params?: Record<string, any>): string {
    const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
    const url = new URL(`${this.baseUrl}${cleanEndpoint}`);

    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
          url.searchParams.append(key, String(value));
        }
      });
    }

    return url.toString();
  }

  private async request<T>(
    endpoint: string,
    method: string,
    body?: any,
    options: RequestOptions = {}
  ): Promise<T> {
    const url = this.buildUrl(endpoint, options.params);
    const headers = new Headers(options.headers || {});

    // 1. Attach Bearer token
    const token = this.getAuthToken();
    if (token && !headers.has('Authorization')) {
      headers.set('Authorization', `Bearer ${token}`);
    }

    // 2. Attach Active Organization ID for tenant context resolution
    if (!options.skipOrgHeader) {
      const activeOrgId = this.getActiveOrgId();
      if (activeOrgId && !headers.has('X-Organization-Id')) {
        headers.set('X-Organization-Id', activeOrgId);
      }
    }

    // 3. Configure Body and Content-Type
    let requestBody: any = undefined;
    if (body !== undefined) {
      if (body instanceof FormData) {
        // Let browser set multipart/form-data boundary automatically
        requestBody = body;
      } else {
        if (!headers.has('Content-Type')) {
          headers.set('Content-Type', 'application/json');
        }
        requestBody = JSON.stringify(body);
      }
    }

    let response: Response;
    try {
      response = await fetch(url, {
        ...options,
        method,
        headers,
        body: requestBody,
      });
    } catch (networkError: any) {
      throw new ApiError(
        0,
        'NETWORK_ERROR',
        networkError.message || 'Unable to connect to the backend server. Please check your network or server status.'
      );
    }

    // 4. Handle HTTP Errors
    if (!response.ok) {
      let errorData: any = {};
      try {
        errorData = await response.json();
      } catch {
        errorData = { message: response.statusText };
      }

      const status = response.status;
      const code = errorData?.error?.code || (errorData?.detail ? 'VALIDATION_ERROR' : `HTTP_${status}`);
      const message =
        errorData?.error?.message ||
        (typeof errorData?.detail === 'string'
          ? errorData.detail
          : Array.isArray(errorData?.detail)
          ? errorData.detail.map((d: any) => `${d.loc?.slice(-1)[0]}: ${d.msg}`).join(', ')
          : errorData?.message || `Request failed with status ${status}`);

      // Handle 401 Unauthorized (session expired or invalid token)
      if (status === 401) {
        if (typeof window !== 'undefined') {
          this.setAuthToken(null);
          // Dispatch session expired event
          window.dispatchEvent(new CustomEvent('flowstate:auth_expired'));
        }
      }

      throw new ApiError(status, code, message, errorData?.error?.details || errorData?.detail);
    }

    // 5. Parse 204 No Content vs JSON
    if (response.status === 204) {
      return {} as T;
    }

    try {
      return (await response.json()) as T;
    } catch {
      return {} as T;
    }
  }

  public get<T>(endpoint: string, options?: RequestOptions): Promise<T> {
    return this.request<T>(endpoint, 'GET', undefined, options);
  }

  public post<T>(endpoint: string, data?: any, options?: RequestOptions): Promise<T> {
    return this.request<T>(endpoint, 'POST', data, options);
  }

  public patch<T>(endpoint: string, data?: any, options?: RequestOptions): Promise<T> {
    return this.request<T>(endpoint, 'PATCH', data, options);
  }

  public put<T>(endpoint: string, data?: any, options?: RequestOptions): Promise<T> {
    return this.request<T>(endpoint, 'PUT', data, options);
  }

  public delete<T>(endpoint: string, options?: RequestOptions): Promise<T> {
    return this.request<T>(endpoint, 'DELETE', undefined, options);
  }
}

export const apiClient = new ApiClient();

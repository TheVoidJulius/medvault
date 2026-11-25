export class ApiError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
  }
}

export type Api = <T = unknown>(url: string, init?: RequestInit) => Promise<T>;

function readDetail(body: unknown, status: number): string {
  const detail = (body as { detail?: unknown } | null)?.detail;
  if (Array.isArray(detail)) return detail.map((d: { msg?: string }) => d.msg).filter(Boolean).join('; ');
  if (typeof detail === 'string') return detail;
  return `Request failed with status ${status}.`;
}

export function createApi(token: string | null, onUnauthorized: () => void): Api {
  return async <T,>(url: string, init: RequestInit = {}) => {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...((init.headers as Record<string, string>) || {}),
    };
    if (token) headers.Authorization = `Bearer ${token}`;
    const res = await fetch(url, { ...init, headers });
    if (res.status === 401 && token) {
      onUnauthorized();
      throw new ApiError('Your session ended. Sign in again to continue.', 401);
    }
    if (!res.ok) {
      const body = await res.json().catch(() => null);
      throw new ApiError(readDetail(body, res.status), res.status);
    }
    return (await res.json()) as T;
  };
}

export const errorText = (err: unknown) => (err instanceof Error ? err.message : 'Something went wrong.');

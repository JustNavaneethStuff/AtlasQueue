const API_BASE = import.meta.env.VITE_API_URL || "";
const API_KEY = import.meta.env.VITE_API_KEY || "dev-api-key";

async function fetchApi<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": API_KEY,
      ...options.headers,
    },
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}

export interface Task {
  id: string;
  name: string;
  status: string;
  priority: number;
  attempts: number;
  max_retries: number;
  created_at: string;
  error: string | null;
}

export interface AdminStats {
  tasks_by_status: Record<string, number>;
  queue_depths: Record<string, number>;
  active_workers: number;
  workers: Array<{
    id: string;
    hostname: string;
    status: string;
    last_seen_at: string;
  }>;
}

export interface TaskEvent {
  id: string;
  event_type: string;
  from_status: string | null;
  to_status: string | null;
  message: string | null;
  created_at: string;
}

export const api = {
  getStats: () => fetchApi<AdminStats>("/v1/admin/stats"),
  getTasks: (status?: string) =>
    fetchApi<{ tasks: Task[] }>(`/v1/tasks${status ? `?status=${status}` : ""}`),
  getTask: (id: string) => fetchApi<Task>(`/v1/tasks/${id}`),
  getTaskEvents: (id: string) => fetchApi<TaskEvent[]>(`/v1/tasks/${id}/events`),
  retryTask: (id: string) =>
    fetchApi<Task>(`/v1/tasks/${id}/retry`, { method: "POST" }),
  cancelTask: (id: string) =>
    fetchApi<Task>(`/v1/tasks/${id}/cancel`, { method: "POST" }),
  getWorkers: () => fetchApi<AdminStats["workers"]>("/v1/workers"),
};

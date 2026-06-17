import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import { api } from "../api";

export default function TaskDetail() {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();

  const { data: task } = useQuery({
    queryKey: ["task", id],
    queryFn: () => api.getTask(id!),
    enabled: !!id,
  });

  const { data: events } = useQuery({
    queryKey: ["task-events", id],
    queryFn: () => api.getTaskEvents(id!),
    enabled: !!id,
  });

  const retry = useMutation({
    mutationFn: () => api.retryTask(id!),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["task", id] }),
  });

  const cancel = useMutation({
    mutationFn: () => api.cancelTask(id!),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["task", id] }),
  });

  if (!task) return <p>Loading...</p>;

  return (
    <div>
      <h1>{task.name}</h1>
      <div className="card">
        <p><strong>ID:</strong> {task.id}</p>
        <p><strong>Status:</strong> <span className={`status status-${task.status}`}>{task.status}</span></p>
        <p><strong>Attempts:</strong> {task.attempts}/{task.max_retries}</p>
        {task.error && <p><strong>Error:</strong> {task.error}</p>}
        <div style={{ display: "flex", gap: "0.5rem", marginTop: "1rem" }}>
          {(task.status === "dead_letter" || task.status === "failed") && (
            <button onClick={() => retry.mutate()}>Retry</button>
          )}
          {!["completed", "cancelled", "dead_letter"].includes(task.status) && (
            <button className="danger" onClick={() => cancel.mutate()}>Cancel</button>
          )}
        </div>
      </div>

      <h2>Event Timeline</h2>
      <table>
        <thead>
          <tr>
            <th>Time</th>
            <th>Event</th>
            <th>From</th>
            <th>To</th>
            <th>Message</th>
          </tr>
        </thead>
        <tbody>
          {events?.map((e) => (
            <tr key={e.id}>
              <td>{new Date(e.created_at).toLocaleString()}</td>
              <td>{e.event_type}</td>
              <td>{e.from_status ?? "-"}</td>
              <td>{e.to_status ?? "-"}</td>
              <td>{e.message ?? "-"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

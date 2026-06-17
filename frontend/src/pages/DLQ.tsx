import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../api";

export default function DLQ() {
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["dlq-tasks"],
    queryFn: () => api.getTasks("dead_letter"),
  });

  const retry = useMutation({
    mutationFn: (id: string) => api.retryTask(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["dlq-tasks"] }),
  });

  if (isLoading) return <p>Loading...</p>;

  return (
    <div>
      <h1>Dead Letter Queue</h1>
      <table>
        <thead>
          <tr>
            <th>Name</th>
            <th>Error</th>
            <th>Attempts</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {data?.tasks.map((task) => (
            <tr key={task.id}>
              <td><Link to={`/tasks/${task.id}`}>{task.name}</Link></td>
              <td>{task.error ?? "-"}</td>
              <td>{task.attempts}/{task.max_retries}</td>
              <td>
                <button onClick={() => retry.mutate(task.id)}>Replay</button>
              </td>
            </tr>
          ))}
          {data?.tasks.length === 0 && (
            <tr><td colSpan={4}>No dead letter tasks</td></tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

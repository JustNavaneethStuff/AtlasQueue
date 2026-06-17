import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../api";

export default function Tasks() {
  const { data, isLoading } = useQuery({ queryKey: ["tasks"], queryFn: () => api.getTasks() });

  if (isLoading) return <p>Loading...</p>;

  return (
    <div>
      <h1>Tasks</h1>
      <table>
        <thead>
          <tr>
            <th>Name</th>
            <th>Status</th>
            <th>Priority</th>
            <th>Attempts</th>
            <th>Created</th>
          </tr>
        </thead>
        <tbody>
          {data?.tasks.map((task) => (
            <tr key={task.id}>
              <td><Link to={`/tasks/${task.id}`}>{task.name}</Link></td>
              <td><span className={`status status-${task.status}`}>{task.status}</span></td>
              <td>{task.priority}</td>
              <td>{task.attempts}/{task.max_retries}</td>
              <td>{new Date(task.created_at).toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

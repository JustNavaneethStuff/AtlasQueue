import { useQuery } from "@tanstack/react-query";
import { api } from "../api";

export default function Workers() {
  const { data, isLoading } = useQuery({ queryKey: ["workers"], queryFn: api.getWorkers });

  if (isLoading) return <p>Loading...</p>;

  return (
    <div>
      <h1>Workers</h1>
      <table>
        <thead>
          <tr>
            <th>Hostname</th>
            <th>Status</th>
            <th>Last Seen</th>
          </tr>
        </thead>
        <tbody>
          {data?.map((w) => (
            <tr key={w.id}>
              <td>{w.hostname}</td>
              <td>{w.status}</td>
              <td>{new Date(w.last_seen_at).toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

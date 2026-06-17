import { useQuery } from "@tanstack/react-query";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from "recharts";
import { api } from "../api";

const COLORS = ["#38bdf8", "#86efac", "#fcd34d", "#fca5a5", "#c4b5fd", "#94a3b8"];

export default function Overview() {
  const { data, isLoading, error } = useQuery({ queryKey: ["stats"], queryFn: api.getStats });

  if (isLoading) return <p>Loading...</p>;
  if (error) return <p>Error: {(error as Error).message}</p>;
  if (!data) return null;

  const statusData = Object.entries(data.tasks_by_status).map(([name, value]) => ({ name, value }));
  const queueData = Object.entries(data.queue_depths).map(([name, value]) => ({ name, value }));

  return (
    <div>
      <h1>Queue Overview</h1>
      <div className="grid">
        <div className="card">
          <div>Active Workers</div>
          <div className="stat-value">{data.active_workers}</div>
        </div>
        <div className="card">
          <div>Total Tasks</div>
          <div className="stat-value">
            {Object.values(data.tasks_by_status).reduce((a, b) => a + b, 0)}
          </div>
        </div>
        <div className="card">
          <div>DLQ Depth</div>
          <div className="stat-value">{data.queue_depths.dlq ?? 0}</div>
        </div>
      </div>

      <div className="card" style={{ marginTop: "1rem" }}>
        <h3>Tasks by Status</h3>
        <ResponsiveContainer width="100%" height={250}>
          <PieChart>
            <Pie data={statusData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} label>
              {statusData.map((_, i) => (
                <Cell key={i} fill={COLORS[i % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip />
          </PieChart>
        </ResponsiveContainer>
      </div>

      <div className="card">
        <h3>Queue Depths</h3>
        <ResponsiveContainer width="100%" height={250}>
          <BarChart data={queueData}>
            <XAxis dataKey="name" />
            <YAxis />
            <Tooltip />
            <Bar dataKey="value" fill="#38bdf8" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

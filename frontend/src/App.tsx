import { NavLink, Route, Routes } from "react-router-dom";
import Overview from "./pages/Overview";
import Tasks from "./pages/Tasks";
import TaskDetail from "./pages/TaskDetail";
import Workers from "./pages/Workers";
import DLQ from "./pages/DLQ";

export default function App() {
  return (
    <>
      <nav>
        <strong>Atlas Queue</strong>
        <NavLink to="/" end>Overview</NavLink>
        <NavLink to="/tasks">Tasks</NavLink>
        <NavLink to="/workers">Workers</NavLink>
        <NavLink to="/dlq">Dead Letter</NavLink>
      </nav>
      <main>
        <Routes>
          <Route path="/" element={<Overview />} />
          <Route path="/tasks" element={<Tasks />} />
          <Route path="/tasks/:id" element={<TaskDetail />} />
          <Route path="/workers" element={<Workers />} />
          <Route path="/dlq" element={<DLQ />} />
        </Routes>
      </main>
    </>
  );
}

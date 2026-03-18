import { Routes, Route, Navigate } from "react-router-dom";
import { isAuthenticated } from "./lib/auth";
import Layout from "./components/Layout";
import LoginPage from "./pages/LoginPage";
import TrainingsPage from "./pages/TrainingsPage";
import TrainingBuilderPage from "./pages/TrainingBuilderPage";
import SearchPage from "./pages/SearchPage";
import AssignmentsPage from "./pages/AssignmentsPage";
import DashboardPage from "./pages/DashboardPage";
import IncidentsPage from "./pages/IncidentsPage";
import ProceduresPage from "./pages/ProceduresPage";
import ProcedureDetailPage from "./pages/ProcedureDetailPage";
import RolesPage from "./pages/RolesPage";
import RoleDetailPage from "./pages/RoleDetailPage";
import UsersPage from "./pages/UsersPage";
import CompliancePage from "./pages/CompliancePage";
import ChangeEventsPage from "./pages/ChangeEventsPage";

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  return isAuthenticated() ? <>{children}</> : <Navigate to="/login" />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="/dashboard" />} />
        <Route path="procedures" element={<ProceduresPage />} />
        <Route path="procedures/:id" element={<ProcedureDetailPage />} />
        <Route path="roles" element={<RolesPage />} />
        <Route path="roles/:id" element={<RoleDetailPage />} />
        <Route path="users" element={<UsersPage />} />
        <Route path="compliance" element={<CompliancePage />} />
        <Route path="change-events" element={<ChangeEventsPage />} />
        <Route path="trainings" element={<TrainingsPage />} />
        <Route path="trainings/:id" element={<TrainingBuilderPage />} />
        <Route path="search" element={<SearchPage />} />
        <Route path="assignments" element={<AssignmentsPage />} />
        <Route path="dashboard" element={<DashboardPage />} />
        <Route path="incidents" element={<IncidentsPage />} />
      </Route>
    </Routes>
  );
}

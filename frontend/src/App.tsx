import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
} from "react-router-dom";
import { AuthProvider, useAuth } from "./hooks/useAuth";
import { AppLayout } from "./layouts/AppLayout";
import { LoginPage } from "./pages/LoginPage";
import { OverviewPage } from "./pages/OverviewPage";
import { NewRequestPage } from "./pages/NewRequestPage";
import { MyRequestsPage } from "./pages/MyRequestsPage";
import { RequestDetailPage } from "./pages/RequestDetailPage";
import { InboxPage } from "./pages/InboxPage";
import { GrantsPage } from "./pages/GrantsPage";
import { AuditExplorerPage } from "./pages/AuditExplorerPage";
import { CompliancePage } from "./pages/CompliancePage";
import { SimulationPage } from "./pages/SimulationPage";
import { ExceptionsPage } from "./pages/ExceptionsPage";
import { PoliciesPage } from "./pages/PoliciesPage";
import { ComingSoon } from "./pages/ComingSoon";

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } },
});

function Protected({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  if (loading)
    return (
      <div className="min-h-screen grid place-items-center bg-canvas text-muted">
        Loading…
      </div>
    );
  if (!user) return <Navigate to="/login" replace />;
  return <AppLayout>{children}</AppLayout>;
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/" element={<Protected><OverviewPage /></Protected>} />
      <Route
        path="/requests/new"
        element={<Protected><NewRequestPage /></Protected>}
      />
      <Route
        path="/requests"
        element={<Protected><MyRequestsPage /></Protected>}
      />
      <Route
        path="/requests/:requestId"
        element={<Protected><RequestDetailPage /></Protected>}
      />
      <Route path="/inbox" element={<Protected><InboxPage /></Protected>} />
      <Route path="/policies" element={<Protected><PoliciesPage /></Protected>} />
      <Route path="/exceptions" element={<Protected><ExceptionsPage /></Protected>} />
      <Route path="/grants" element={<Protected><GrantsPage /></Protected>} />
      <Route path="/compliance" element={<Protected><CompliancePage /></Protected>} />
      <Route path="/simulation" element={<Protected><SimulationPage /></Protected>} />
      <Route path="/audit" element={<Protected><AuditExplorerPage /></Protected>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <AppRoutes />
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
}

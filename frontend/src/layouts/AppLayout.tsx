import { useState } from "react";
import type { ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { Sidebar } from "../components/Sidebar";
import { useAuth } from "../hooks/useAuth";
import { api } from "../api/client";
import type { Notification } from "../types";

function NotificationsBell() {
  const [open, setOpen] = useState(false);
  const { data: notes = [] } = useQuery({
    queryKey: ["notifications"],
    queryFn: () => api.get<Notification[]>("/notifications"),
    refetchInterval: 15000,
  });
  const unread = notes.filter((n) => n.status !== "READ").length;

  return (
    <div className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        className="relative h-9 w-9 rounded-full bg-card border border-line grid place-items-center hover:border-primary/40"
        title="Notifications"
      >
        <span className="text-muted">◈</span>
        {unread > 0 && (
          <span className="absolute -top-1 -right-1 h-4 min-w-4 px-1 rounded-full bg-primary text-white text-[10px] grid place-items-center">
            {unread > 9 ? "9+" : unread}
          </span>
        )}
      </button>
      {open && (
        <div className="absolute right-0 mt-2 w-80 card p-2 z-20 animate-fade-up max-h-96 overflow-y-auto">
          {notes.length === 0 ? (
            <div className="p-4 text-sm text-muted text-center">
              No notifications yet.
            </div>
          ) : (
            notes.slice(0, 12).map((n) => (
              <div
                key={n.id}
                className="rounded-xl px-3 py-2.5 hover:bg-canvas/60"
              >
                <div className="text-sm text-ink">{n.subject}</div>
                <div className="flex items-center gap-2 mt-1">
                  <span className="chip bg-primary-soft text-primary-deep">
                    {n.notification_type.replace(/_/g, " ").toLowerCase()}
                  </span>
                  <span className="text-xs text-muted">
                    {new Date(n.created_at).toLocaleDateString()}
                  </span>
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}

export function AppLayout({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth();
  const initials = user?.name
    .split(" ")
    .map((p) => p[0])
    .slice(0, 2)
    .join("");

  return (
    <div className="flex min-h-screen bg-canvas">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <header className="h-16 shrink-0 border-b border-line bg-canvas/80 backdrop-blur sticky top-0 z-10 flex items-center gap-4 px-8">
          <div className="flex-1">
            <input
              className="input max-w-sm bg-card/60"
              placeholder="Search requests, policies, resources…"
            />
          </div>
          <div className="flex items-center gap-3">
            <NotificationsBell />
            <div className="text-right leading-tight">
              <div className="text-sm font-semibold text-ink">{user?.name}</div>
              <div className="text-xs text-muted capitalize">
                {user?.role.replace(/_/g, " ").toLowerCase()}
              </div>
            </div>
            <div className="h-9 w-9 rounded-full bg-primary-soft text-primary-deep grid place-items-center text-sm font-semibold">
              {initials}
            </div>
            <button
              onClick={logout}
              className="btn-ghost text-xs px-2.5 py-1.5"
              title="Sign out"
            >
              Sign out
            </button>
          </div>
        </header>
        <main className="flex-1 px-8 py-7 max-w-[1200px] w-full mx-auto animate-fade-up">
          {children}
        </main>
      </div>
    </div>
  );
}

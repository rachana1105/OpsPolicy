import { NavLink } from "react-router-dom";

const NAV = [
  { to: "/", label: "Overview", end: true },
  { to: "/requests", label: "My Requests" },
  { to: "/inbox", label: "Approval Inbox" },
  { to: "/policies", label: "Policies" },
  { to: "/exceptions", label: "Exceptions" },
  { to: "/grants", label: "Access Grants" },
  { to: "/compliance", label: "Compliance" },
  { to: "/simulation", label: "Policy Simulation" },
  { to: "/audit", label: "Audit Explorer" },
];

export function Sidebar() {
  return (
    <aside className="w-60 shrink-0 bg-sidebar text-white/70 flex flex-col min-h-screen">
      <div className="px-5 py-6">
        <div className="flex items-center gap-2.5">
          <div className="h-8 w-8 rounded-xl bg-primary grid place-items-center shadow-glow">
            <span className="font-display text-white text-lg leading-none">O</span>
          </div>
          <div>
            <div className="font-display text-white text-lg leading-none">
              OpsPolicy
            </div>
            <div className="text-[10px] uppercase tracking-widest text-white/40 mt-0.5">
              Governance
            </div>
          </div>
        </div>
      </div>

      <nav className="flex-1 px-3 space-y-0.5">
        {NAV.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            className={({ isActive }) =>
              `block rounded-xl px-3 py-2.5 text-sm font-medium transition-colors ${
                isActive
                  ? "bg-primary text-white shadow-soft"
                  : "text-white/60 hover:bg-sidebarHover hover:text-white"
              }`
            }
          >
            {item.label}
          </NavLink>
        ))}
      </nav>

      <div className="px-5 py-4 text-[11px] text-white/30">
        Northstar Enterprises
      </div>
    </aside>
  );
}

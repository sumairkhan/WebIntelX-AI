"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Bell, ChevronDown, Command, Gauge, Globe, LayoutGrid, Lock, LogOut, Menu, Shield, Sparkles, TriangleAlert } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useState, useSyncExternalStore } from "react";
import { clearStoredToken, getStoredToken, healthApi } from "@/lib/api";
import { cn } from "@/lib/utils";

const fallbackEmail = "operator@webintelx.ai";
const authChangeEvent = "webintelx-auth-change";

function subscribeToAuth(listener: () => void) {
  window.addEventListener("storage", listener);
  window.addEventListener(authChangeEvent, listener);
  return () => {
    window.removeEventListener("storage", listener);
    window.removeEventListener(authChangeEvent, listener);
  };
}

function getUserEmail() {
  const token = getStoredToken();
  if (!token) return fallbackEmail;
  try {
    const payload = JSON.parse(atob(token.split(".")[1] ?? ""));
    return typeof payload?.email === "string" ? payload.email : fallbackEmail;
  } catch {
    return fallbackEmail;
  }
}

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: Gauge },
  { href: "/websites", label: "Websites", icon: Globe },
  { href: "/events", label: "Events", icon: Shield },
  { href: "/findings", label: "Findings", icon: TriangleAlert },
  { href: "/investigations", label: "Investigations", icon: Sparkles },
  { href: "/incidents", label: "Incidents", icon: Bell },
  { href: "/attack-graph", label: "Attack Graph", icon: LayoutGrid },
  { href: "/threat-intelligence", label: "Threat Intel", icon: Lock },
  { href: "/reports", label: "Reports", icon: Command },
  { href: "/settings", label: "Settings", icon: ChevronDown },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [commandOpen, setCommandOpen] = useState(false);
  const userEmail = useSyncExternalStore(subscribeToAuth, getUserEmail, () => fallbackEmail);
  const healthQuery = useQuery({ queryKey: ["health"], queryFn: healthApi.get, refetchInterval: 30000, retry: false });
  const systemStatus = healthQuery.isLoading ? "Checking API" : healthQuery.data?.status === "healthy" ? "API Healthy" : healthQuery.isError ? "API Unavailable" : "API Degraded";

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setCommandOpen((value) => !value);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  const commandItems = useMemo(
    () => [
      { href: "/dashboard", label: "Dashboard" },
      { href: "/websites", label: "Websites" },
      { href: "/events", label: "Events" },
      { href: "/findings", label: "Findings" },
      { href: "/investigations", label: "Investigations" },
      { href: "/incidents", label: "Incidents" },
      { href: "/reports", label: "Reports" },
      { href: "/settings", label: "Settings" },
    ],
    [],
  );

  const handleLogout = () => {
    clearStoredToken();
    router.push("/login");
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-50">
      <div className="flex min-h-screen">
        <aside
          className={cn(
            "fixed inset-y-0 left-0 z-30 w-72 border-r border-slate-800 bg-slate-950/95 p-5 backdrop-blur xl:static xl:translate-x-0",
            mobileOpen ? "translate-x-0" : "-translate-x-full xl:translate-x-0",
          )}
        >
          <div className="mb-8 flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-cyan-500/15 text-cyan-300 ring-1 ring-cyan-400/30">
              <Shield className="h-5 w-5" />
            </div>
            <div>
              <p className="text-base font-semibold">WebIntelX AI</p>
              <p className="text-xs text-slate-400">Security Intelligence</p>
            </div>
          </div>

          <nav className="space-y-1">
            {navItems.map(({ href, label, icon: Icon }) => {
              const active = pathname === href || pathname.startsWith(`${href}/`);
              return (
                <Link
                  key={href}
                  href={href}
                  className={cn(
                    "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition",
                    active ? "bg-slate-800 text-white ring-1 ring-slate-700" : "text-slate-300 hover:bg-slate-900 hover:text-slate-100",
                  )}
                >
                  <Icon className="h-4 w-4" />
                  {label}
                </Link>
              );
            })}
          </nav>

          <div className="mt-10 rounded-2xl border border-cyan-500/20 bg-cyan-500/5 p-4">
            <div className="flex items-center gap-2 text-cyan-300">
              <span className="h-2.5 w-2.5 rounded-full bg-emerald-400" />
              <span className="text-xs font-medium uppercase tracking-[0.2em]">System</span>
            </div>
            <p className="mt-3 text-sm text-slate-300">{systemStatus}</p>
          </div>
        </aside>

        <div className="flex-1">
          <header className="sticky top-0 z-20 border-b border-slate-800 bg-slate-950/80 backdrop-blur">
            <div className="flex items-center justify-between gap-4 px-5 py-4">
              <div className="flex items-center gap-3 xl:hidden">
                <button
                  type="button"
                  onClick={() => setMobileOpen((value) => !value)}
                  className="rounded-lg border border-slate-700 bg-slate-900 p-2 text-slate-300"
                >
                  <Menu className="h-4 w-4" />
                </button>
              </div>

              <div className="hidden items-center gap-2 rounded-xl border border-slate-800 bg-slate-900 px-3 py-2 text-sm text-slate-400 md:flex">
                <Command className="h-4 w-4 text-cyan-300" />
                <span>Search</span>
              </div>

              <div className="ml-auto flex items-center gap-3">
                <button
                  type="button"
                  onClick={() => setCommandOpen(true)}
                  className="hidden rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-slate-300 md:inline-flex"
                >
                  Ctrl + K
                </button>
                <div className="hidden items-center gap-2 rounded-xl border border-slate-800 bg-slate-900 px-3 py-2 text-sm text-slate-300 md:flex">
                  <span>{userEmail}</span>
                  <ChevronDown className="h-4 w-4 text-slate-500" />
                </div>
                <button
                  type="button"
                  onClick={handleLogout}
                  className="inline-flex items-center gap-2 rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-200 transition hover:bg-slate-800"
                >
                  <LogOut className="h-4 w-4" />
                  Logout
                </button>
              </div>
            </div>
          </header>

          <main className="p-5 md:p-7">{children}</main>
        </div>
      </div>

      {commandOpen && (
        <div className="fixed inset-0 z-50 flex items-start justify-center bg-slate-950/70 p-6 pt-20 backdrop-blur-sm">
          <div className="w-full max-w-2xl rounded-2xl border border-slate-700 bg-slate-900 p-4 shadow-2xl">
            <div className="mb-4 flex items-center gap-2 rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-300">
              <Command className="h-4 w-4 text-cyan-300" />
              Quick navigation
            </div>
            <div className="space-y-2">
              {commandItems.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={() => setCommandOpen(false)}
                  className="block rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-200 hover:border-cyan-500/40 hover:text-cyan-200"
                >
                  {item.label}
                </Link>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

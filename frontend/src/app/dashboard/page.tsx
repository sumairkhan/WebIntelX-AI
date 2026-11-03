"use client";

import { useEffect, useState } from "react";
import { useQueries, useQuery } from "@tanstack/react-query";
import { Activity, Bell, Globe2, ShieldAlert } from "lucide-react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { AppShell } from "@/components/app-shell";
import { eventsApi, findingsApi, incidentsApi, Website, websitesApi } from "@/lib/api";

type ActivityChartDay = {
  name: string;
  events: number;
  findings: number;
};

function buildActivityChartData(events: Awaited<ReturnType<typeof eventsApi.list>> = [], findings: Awaited<ReturnType<typeof findingsApi.list>> = []): ActivityChartDay[] {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return Array.from({ length: 7 }, (_, offset) => {
    const day = new Date(today);
    day.setDate(day.getDate() - (6 - offset));
    const nextDay = new Date(day);
    nextDay.setDate(nextDay.getDate() + 1);
    return {
      name: day.toLocaleDateString(undefined, { weekday: "short" }),
      events: events.filter((event) => Date.parse(event.timestamp) >= day.getTime() && Date.parse(event.timestamp) < nextDay.getTime()).length,
      findings: findings.filter((finding) => finding.created_at && Date.parse(finding.created_at) >= day.getTime() && Date.parse(finding.created_at) < nextDay.getTime()).length,
    };
  });
}

function MetricCard({ label, value, detail, tone }: { label: string; value: string; detail: string; tone: "cyan" | "green" | "amber" | "red" }) {
  const tones = {
    cyan: "bg-cyan-500/10 text-cyan-200 ring-cyan-500/20",
    green: "bg-emerald-500/10 text-emerald-200 ring-emerald-500/20",
    amber: "bg-amber-500/10 text-amber-200 ring-amber-500/20",
    red: "bg-red-500/10 text-red-200 ring-red-500/20",
  };

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900 p-4">
      <div className={`mb-4 inline-flex rounded-full px-2.5 py-1 text-xs ring-1 ${tones[tone]}`}>{label}</div>
      <div className="text-3xl font-semibold text-white">{value}</div>
      <div className="mt-2 text-sm text-slate-400">{detail}</div>
    </div>
  );
}

export default function DashboardPage() {
  const { data: websites = [] } = useQuery({
    queryKey: ["websites"],
    queryFn: websitesApi.list,
  });

  const telemetryQueries = useQueries({ queries: websites.map((website: Website) => ({
    queryKey: ["website-telemetry", website.id],
    queryFn: () => eventsApi.telemetry(website.id),
    retry: false,
  })) });
  const eventsQueries = useQueries({ queries: websites.map((website: Website) => ({
    queryKey: ["events", website.id],
    queryFn: () => eventsApi.list(website.id, 100),
    retry: false,
  })) });
  const findingsQueries = useQueries({ queries: websites.map((website: Website) => ({
    queryKey: ["findings", website.id],
    queryFn: () => findingsApi.list(website.id),
    retry: false,
  })) });
  const incidentsQueries = useQueries({ queries: websites.map((website: Website) => ({
    queryKey: ["incidents", website.id],
    queryFn: () => incidentsApi.list(website.id),
    retry: false,
  })) });

  const telemetry = telemetryQueries.flatMap((query) => query.data ? [query.data] : []);
  const events = eventsQueries.flatMap((query) => query.data ?? []);
  const findings = findingsQueries.flatMap((query) => query.data ?? []);
  const incidents = incidentsQueries.flatMap((query) => query.data ?? []);
  const [hydrated, setHydrated] = useState(false);
  useEffect(() => {
    setHydrated(true);
  }, []);
  const eventCount = telemetry.reduce((total, item) => total + item.event_count, 0);
  const findingCount = telemetry.reduce((total, item) => total + item.finding_count, 0);
  const latestEvents = [...events].sort((a, b) => Date.parse(b.timestamp) - Date.parse(a.timestamp));
  const latestIncident = [...incidents].sort((a, b) => (b.risk_score ?? 0) - (a.risk_score ?? 0))[0];
  const sampleSessions = new Set(events.map((item) => item.session_id).filter(Boolean)).size;
  const chartData = hydrated ? buildActivityChartData(events, findings) : [];
  const isLoading = websites.length > 0 && telemetryQueries.some((query) => query.isLoading);
  const dataError = telemetryQueries.some((query) => query.isError);

  return (
    <AppShell>
      <div className="space-y-6">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-sm font-medium uppercase tracking-[0.2em] text-cyan-300">Overview</p>
            <h1 className="mt-2 text-3xl font-semibold text-white">Security overview</h1>
          </div>
          <div className="flex items-center gap-3">
            <div className="rounded-xl border border-slate-800 bg-slate-900 px-3 py-2 text-sm text-slate-300">
              {websites.length === 1 ? websites[0].domain : `${websites.length} websites`}
            </div>
            <div className="rounded-xl border border-emerald-500/25 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-300">
              Last 7 days · observed events
            </div>
          </div>
        </div>

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <MetricCard label="Total Events" value={isLoading ? "..." : String(eventCount)} detail="Backend telemetry total" tone="cyan" />
          <MetricCard label="Sessions Observed" value={String(sampleSessions)} detail="Latest event sample" tone="green" />
          <MetricCard label="Findings" value={isLoading ? "..." : String(findingCount)} detail="Backend detection records" tone="amber" />
          <MetricCard label="Incidents" value={String(incidents.length)} detail={incidentsQueries.some((query) => query.isError) ? "Incident data unavailable" : "Backend incident records"} tone="red" />
        </div>

        <div className="grid gap-6 xl:grid-cols-[1.5fr_0.8fr]">
          <div className="rounded-3xl border border-slate-800 bg-slate-900 p-5">
            <div className="mb-4 flex items-center justify-between">
              <div>
                <p className="text-lg font-semibold text-white">Security Activity</p>
                <p className="text-sm text-slate-400">Counts from returned event and finding records</p>
              </div>
              <div className="flex gap-2 text-xs text-slate-300">
                <span className="rounded-full bg-cyan-500/10 px-2 py-1 text-cyan-200">Events sample</span>
                <span className="rounded-full bg-amber-500/10 px-2 py-1 text-amber-200">Findings</span>
              </div>
            </div>

            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData}>
                  <CartesianGrid stroke="#1f2937" strokeDasharray="3 3" />
                  <XAxis dataKey="name" stroke="#94a3b8" />
                  <YAxis stroke="#94a3b8" />
                  <Tooltip />
                  <Bar dataKey="events" fill="#22d3ee" radius={[8, 8, 0, 0]} />
                  <Bar dataKey="findings" fill="#fbbf24" radius={[8, 8, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="space-y-4 rounded-3xl border border-slate-800 bg-slate-900 p-5">
            <div className="flex items-center justify-between">
              <p className="text-lg font-semibold text-white">Incident Risk</p>
              <ShieldAlert className="h-5 w-5 text-cyan-300" />
            </div>
            {latestIncident ? <div className="border border-slate-800 bg-slate-950 p-4"><p className="text-xs uppercase tracking-widest text-slate-500">Highest recorded incident</p><p className="mt-2 text-2xl font-semibold text-white">{latestIncident.risk_score} / 100</p><p className="mt-1 text-sm text-slate-300">{latestIncident.risk_level} · {latestIncident.title}</p></div> : <p className="text-sm text-slate-400">No incident risk records are available.</p>}
          </div>
        </div>

        <div className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
          <div className="rounded-3xl border border-slate-800 bg-slate-900 p-5">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-white">Recent Security Activity</h2>
              <Activity className="h-5 w-5 text-cyan-300" />
            </div>
            <div className="space-y-3">
              {latestEvents.length ? (
                latestEvents.slice(0, 5).map((item) => (
                  <div key={item.id} className="flex items-center justify-between rounded-xl border border-slate-800 bg-slate-950 p-3">
                    <div>
                      <p className="font-medium text-slate-100">{item.event_type}</p>
                      <p className="text-xs text-slate-400">{item.endpoint || item.source} · {new Date(item.timestamp).toLocaleString()}</p>
                    </div>
                    <span className="rounded-full bg-slate-800 px-2 py-1 text-xs text-slate-300">{item.method || "Unknown"}</span>
                  </div>
                ))
              ) : (
                <div className="rounded-xl border border-dashed border-slate-700 bg-slate-950 p-5 text-sm text-slate-400">
                  No telemetry received yet. Connect a website and install the SDK.
                </div>
              )}
            </div>
          </div>

          <div className="rounded-3xl border border-slate-800 bg-slate-900 p-5">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-white">Monitoring</h2>
              <Globe2 className="h-5 w-5 text-cyan-300" />
            </div>
            <p className="text-4xl font-semibold text-white">{websites.filter((site) => site.status.toLowerCase() === "active").length}</p>
            <p className="mt-1 text-sm text-slate-400">Active websites</p>
            {dataError && <p className="mt-4 text-sm text-amber-200">Some telemetry summaries are unavailable.</p>}
            <div className="mt-5 flex items-center gap-2 text-sm text-slate-300"><Bell className="h-4 w-4 text-cyan-300" />{incidents.length} incident records</div>
          </div>
        </div>
      </div>
    </AppShell>
  );
}

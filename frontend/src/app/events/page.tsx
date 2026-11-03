"use client";

import { useQuery } from "@tanstack/react-query";
import { AppShell } from "@/components/app-shell";
import { eventsApi, websitesApi } from "@/lib/api";

export default function EventsPage() {
  const { data: websites = [] } = useQuery({
    queryKey: ["websites"],
    queryFn: websitesApi.list,
  });
  const websiteId = websites[0]?.id ?? null;

  const { data: events = [] } = useQuery({
    queryKey: ["events", websiteId],
    enabled: !!websiteId,
    queryFn: () => eventsApi.list(websiteId as number, 80),
  });

  return (
    <AppShell>
      <div className="space-y-5">
        <div>
          <p className="text-sm uppercase tracking-[0.2em] text-cyan-300">Security events</p>
          <h1 className="mt-2 text-3xl font-semibold text-white">Events</h1>
        </div>

        {events.length === 0 ? (
          <div className="rounded-3xl border border-dashed border-slate-700 bg-slate-900 p-10 text-slate-300">No events recorded yet. Connect a website to begin ingesting telemetry.</div>
        ) : (
          <div className="overflow-hidden rounded-3xl border border-slate-800 bg-slate-900">
            <table className="min-w-full text-left text-sm text-slate-200">
              <thead className="bg-slate-950 text-xs uppercase tracking-[0.15em] text-slate-400">
                <tr>
                  <th className="px-5 py-3">Timestamp</th>
                  <th className="px-5 py-3">Type</th>
                  <th className="px-5 py-3">Endpoint</th>
                  <th className="px-5 py-3">Status</th>
                </tr>
              </thead>
              <tbody>
                {events.map((event) => (
                  <tr key={event.id} className="border-t border-slate-800">
                    <td className="px-5 py-4">{new Date(event.timestamp).toLocaleString()}</td>
                    <td className="px-5 py-4 text-cyan-200">{event.event_type}</td>
                    <td className="px-5 py-4 text-slate-300">{event.endpoint || "—"}</td>
                    <td className="px-5 py-4">{event.status_code ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </AppShell>
  );
}

"use client";

import { useQuery } from "@tanstack/react-query";
import { AppShell } from "@/components/app-shell";
import { incidentsApi, websitesApi } from "@/lib/api";

export default function IncidentsPage() {
  const { data: websites = [] } = useQuery({ queryKey: ["websites"], queryFn: websitesApi.list });
  const websiteId = websites[0]?.id ?? null;

  const { data: incidents = [] } = useQuery({
    queryKey: ["incidents", websiteId],
    enabled: !!websiteId,
    queryFn: () => incidentsApi.list(websiteId as number),
  });

  return (
    <AppShell>
      <div className="space-y-5">
        <div>
          <p className="text-sm uppercase tracking-[0.2em] text-cyan-300">Incident response</p>
          <h1 className="mt-2 text-3xl font-semibold text-white">Incidents</h1>
        </div>

        {incidents.length === 0 ? (
          <div className="rounded-3xl border border-dashed border-slate-700 bg-slate-900 p-10 text-slate-300">No incidents yet. Investigations and risk evaluation will create records here.</div>
        ) : (
          <div className="space-y-3">
            {incidents.map((incident) => (
              <div key={incident.id} className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="text-lg font-semibold text-white">{incident.title}</p>
                    <p className="text-sm text-slate-400">{incident.incident_id} • {incident.status}</p>
                  </div>
                  <span className="rounded-full bg-red-500/10 px-2.5 py-1 text-xs font-medium text-red-300">{incident.risk_level}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </AppShell>
  );
}

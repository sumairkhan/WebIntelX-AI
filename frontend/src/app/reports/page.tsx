"use client";

import { useQuery } from "@tanstack/react-query";
import { AppShell } from "@/components/app-shell";
import { reportsApi, websitesApi } from "@/lib/api";

export default function ReportsPage() {
  const { data: websites = [] } = useQuery({ queryKey: ["websites"], queryFn: websitesApi.list });
  const websiteId = websites[0]?.id ?? null;

  const { data: reports = [] } = useQuery({
    queryKey: ["reports", websiteId],
    enabled: !!websiteId,
    queryFn: () => reportsApi.list(websiteId as number),
  });

  return (
    <AppShell>
      <div className="space-y-5">
        <div>
          <p className="text-sm uppercase tracking-[0.2em] text-cyan-300">Reporting</p>
          <h1 className="mt-2 text-3xl font-semibold text-white">Reports</h1>
        </div>

        {reports.length === 0 ? (
          <div className="rounded-3xl border border-dashed border-slate-700 bg-slate-900 p-10 text-slate-300">No reports generated yet. Investigation output and event summaries will appear here.</div>
        ) : (
          <div className="space-y-3">
            {reports.map((report, index) => (
              <div key={`${report.website_id}-${index}`} className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
                <p className="text-lg font-semibold text-white">{report.summary}</p>
                <p className="mt-2 text-sm text-slate-400">Facts: {report.facts?.length ?? 0}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </AppShell>
  );
}

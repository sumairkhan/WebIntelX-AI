"use client";

import { useQuery } from "@tanstack/react-query";
import { AppShell } from "@/components/app-shell";
import { findingsApi, websitesApi } from "@/lib/api";

export default function FindingsPage() {
  const { data: websites = [] } = useQuery({ queryKey: ["websites"], queryFn: websitesApi.list });
  const websiteId = websites[0]?.id ?? null;

  const { data: findings = [] } = useQuery({
    queryKey: ["findings", websiteId],
    enabled: !!websiteId,
    queryFn: () => findingsApi.list(websiteId as number),
  });

  return (
    <AppShell>
      <div className="space-y-5">
        <div>
          <p className="text-sm uppercase tracking-[0.2em] text-cyan-300">Detections</p>
          <h1 className="mt-2 text-3xl font-semibold text-white">Findings</h1>
        </div>

        {findings.length === 0 ? (
          <div className="rounded-3xl border border-dashed border-slate-700 bg-slate-900 p-10 text-slate-300">No findings yet. Detection rules and ML models will report anomalies here.</div>
        ) : (
          <div className="space-y-3">
            {findings.map((finding) => (
              <div key={finding.id} className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="text-lg font-semibold text-white">{finding.finding_type}</p>
                    <p className="text-sm text-slate-400">{finding.agent_name || "System"}</p>
                  </div>
                  <span className="rounded-full bg-amber-500/15 px-2.5 py-1 text-xs font-medium text-amber-300">
                    {finding.confidence ? "MEDIUM" : "LOW"}
                  </span>
                </div>
                <p className="mt-3 text-sm text-slate-300">Confidence: {Number(finding.confidence ?? 0).toFixed(2)}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </AppShell>
  );
}

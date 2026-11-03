"use client";

import { useQuery } from "@tanstack/react-query";
import { AppShell } from "@/components/app-shell";
import { threatIntelApi, websitesApi } from "@/lib/api";

export default function ThreatIntelPage() {
  const { data: websites = [] } = useQuery({ queryKey: ["websites"], queryFn: websitesApi.list });
  const websiteId = websites[0]?.id ?? null;

  const { data: intel = [] } = useQuery({
    queryKey: ["threat-intel", websiteId],
    enabled: !!websiteId,
    queryFn: () => threatIntelApi.check(websiteId as number, "1.1.1.1", "ip").then((result) => [result]).catch(() => []),
  });

  return (
    <AppShell>
      <div className="space-y-5">
        <div>
          <p className="text-sm uppercase tracking-[0.2em] text-cyan-300">Threat intelligence</p>
          <h1 className="mt-2 text-3xl font-semibold text-white">Indicators</h1>
        </div>

        <div className="rounded-3xl border border-slate-800 bg-slate-900 p-5">
          {intel.length === 0 ? (
            <div className="text-slate-300">No indicators checked yet.</div>
          ) : (
            <div className="space-y-3">
              {intel.map((item, index) => (
                <div key={`${item.indicator}-${index}`} className="rounded-xl border border-slate-800 bg-slate-950 p-4">
                  <div className="flex items-center justify-between">
                    <p className="font-medium text-white">{item.indicator}</p>
                    <span className="rounded-full bg-cyan-500/10 px-2 py-1 text-xs text-cyan-200">{item.provider || "internal"}</span>
                  </div>
                  <p className="mt-2 text-sm text-slate-300">Type: {item.indicator_type || "ip"}</p>
                  <p className="text-sm text-slate-300">Reputation: {item.reputation || "unknown"}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </AppShell>
  );
}

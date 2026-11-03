"use client";

import { useQuery } from "@tanstack/react-query";
import { AppShell } from "@/components/app-shell";
import { GraphEdgeRecord, GraphNodeRecord, graphApi, websitesApi } from "@/lib/api";

export default function AttackGraphPage() {
  const { data: websites = [] } = useQuery({ queryKey: ["websites"], queryFn: websitesApi.list });
  const websiteId = websites[0]?.id ?? null;

  const { data: graph } = useQuery({
    queryKey: ["graph", websiteId],
    enabled: !!websiteId,
    queryFn: () => graphApi.get(websiteId as number),
  });

  const nodes = graph?.nodes ?? [];
  const edges = graph?.edges ?? [];

  return (
    <AppShell>
      <div className="space-y-5">
        <div>
          <p className="text-sm uppercase tracking-[0.2em] text-cyan-300">Attack path</p>
          <h1 className="mt-2 text-3xl font-semibold text-white">Attack graph</h1>
        </div>

        <div className="grid gap-5 lg:grid-cols-[1fr_300px]">
          <div className="rounded-3xl border border-slate-800 bg-slate-900 p-5">
            <div className="flex min-h-[480px] flex-wrap gap-3 rounded-2xl border border-dashed border-slate-700 bg-slate-950 p-4">
              {nodes.length === 0 ? (
                <div className="m-auto text-sm text-slate-400">No relationship graph available yet.</div>
              ) : (
                nodes.map((node: GraphNodeRecord, index: number) => (
                  <div key={`${node.id ?? index}`} className="flex h-20 w-20 items-center justify-center rounded-2xl border border-cyan-500/30 bg-cyan-500/10 text-center text-xs text-cyan-100">
                    {node.label}
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="rounded-3xl border border-slate-800 bg-slate-900 p-5">
            <h2 className="text-lg font-semibold text-white">Relationships</h2>
            <div className="mt-4 space-y-3">
              {edges.length === 0 ? (
                <p className="text-sm text-slate-400">No edges discovered.</p>
              ) : (
                edges.map((edge: GraphEdgeRecord, index: number) => (
                  <div key={`${edge.source}-${edge.target}-${index}`} className="rounded-xl border border-slate-800 bg-slate-950 p-3 text-sm text-slate-300">
                    {edge.source} → {edge.target}
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  );
}

"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { AppShell } from "@/components/app-shell";
import { investigationsApi, websitesApi } from "@/lib/api";

export default function InvestigationsPage() {
  const { data: websites = [] } = useQuery({ queryKey: ["websites"], queryFn: websitesApi.list });
  const websiteId = websites[0]?.id ?? null;

  const { data: investigations = [] } = useQuery({
    queryKey: ["investigations", websiteId],
    enabled: !!websiteId,
    queryFn: () => investigationsApi.list(websiteId as number),
  });

  return (
    <AppShell>
      <div className="space-y-5">
        <div>
          <p className="text-sm uppercase tracking-[0.2em] text-cyan-300">AI investigations</p>
          <h1 className="mt-2 text-3xl font-semibold text-white">Investigations</h1>
        </div>

        {investigations.length === 0 ? (
          <div className="rounded-3xl border border-dashed border-slate-700 bg-slate-900 p-10 text-slate-300">No investigations yet. Correlated activity will appear here.</div>
        ) : (
          <div className="grid gap-4">
            {investigations.map((item) => (
              <div key={item.id} className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="text-lg font-semibold text-white">{item.title || item.investigation_id}</p>
                    <p className="text-sm text-slate-400">{item.status}</p>
                  </div>
                  <Link href={`/investigations/${item.investigation_id}`} className="text-cyan-300 hover:text-cyan-200">
                    View
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </AppShell>
  );
}

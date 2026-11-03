"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useParams } from "next/navigation";
import { eventsApi, isWebsiteConnected, websitesApi } from "@/lib/api";
import { AppShell } from "@/components/app-shell";

export default function WebsiteDetailPage() {
  const params = useParams<{ id: string }>();
  const websiteId = Number(params.id);

  const { data: website } = useQuery({
    queryKey: ["website", websiteId],
    enabled: Number.isFinite(websiteId),
    queryFn: () => websitesApi.get(websiteId),
  });
  const { data: telemetry } = useQuery({
    queryKey: ["website-telemetry", websiteId],
    enabled: Number.isSafeInteger(websiteId) && websiteId > 0,
    queryFn: () => eventsApi.telemetry(websiteId),
    retry: false,
  });

  return (
    <AppShell>
      <div className="space-y-5">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-sm uppercase tracking-[0.2em] text-cyan-300">Website</p>
            <h1 className="mt-2 text-3xl font-semibold text-white">{website?.name || "Loading..."}</h1>
          </div>
          <div className="flex gap-3">
            <Link href={`/websites/${websiteId}/settings`} className="rounded-xl border border-slate-700 bg-slate-900 px-4 py-2 text-sm text-slate-200 hover:border-cyan-500/40">
              Settings
            </Link>
            <Link href={`/websites/${websiteId}/integration`} className="rounded-xl bg-cyan-500 px-4 py-2 text-sm font-medium text-slate-950 hover:bg-cyan-400">
              Integration
            </Link>
          </div>
        </div>

        <div className="grid gap-4 md:grid-cols-3">
          <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
            <p className="text-sm text-slate-400">Domain</p>
            <p className="mt-3 text-xl font-semibold text-white">{website?.domain || "—"}</p>
          </div>
          <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
            <p className="text-sm text-slate-400">Status</p>
            <p className="mt-3 text-xl font-semibold text-white">{website ? website.status.toLowerCase() !== "active" ? "Inactive" : isWebsiteConnected(website, telemetry) ? "Connected" : "Waiting for Telemetry" : "Loading..."}</p>
          </div>
          <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
            <p className="text-sm text-slate-400">Telemetry</p>
            <p className="mt-3 text-xl font-semibold text-white">{telemetry ? `${telemetry.event_count} events` : "Not available"}</p>
            <p className="mt-1 text-xs text-slate-500">Risk is not evaluated in this view.</p>
          </div>
        </div>
        <div className="flex gap-3"><Link href={`/websites/${websiteId}/setup`} className="text-sm text-cyan-300 hover:text-cyan-200">Continue setup</Link><Link href={`/websites/${websiteId}/verify`} className="text-sm text-cyan-300 hover:text-cyan-200">Verify connection</Link></div>
      </div>
    </AppShell>
  );
}

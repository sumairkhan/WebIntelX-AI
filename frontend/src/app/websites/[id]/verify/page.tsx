"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useParams } from "next/navigation";
import { CheckCircle2, Circle, LoaderCircle } from "lucide-react";
import { AppShell } from "@/components/app-shell";
import { eventsApi, isWebsiteConnected, websitesApi } from "@/lib/api";

export default function WebsiteVerifyPage() {
  const params = useParams<{ id: string }>();
  const websiteId = Number(params.id);

  const { data: website, isLoading: websiteLoading } = useQuery({
    queryKey: ["website", websiteId],
    enabled: Number.isSafeInteger(websiteId) && websiteId > 0,
    queryFn: () => websitesApi.get(websiteId),
  });

  const telemetryQuery = useQuery({
    queryKey: ["website-telemetry", websiteId],
    enabled: false,
    queryFn: () => eventsApi.telemetry(websiteId),
    retry: false,
  });

  if (websiteLoading) return <AppShell><p className="text-sm text-slate-400">Loading website...</p></AppShell>;
  if (!website) return <AppShell><div className="border border-red-900/50 bg-red-950/30 p-5 text-sm text-red-200">Website could not be loaded. Verify your account access.</div></AppShell>;

  const telemetry = telemetryQuery.data;
  const connected = !telemetryQuery.isError && isWebsiteConnected(website, telemetry);
  const websiteUrl = website.origin;

  return (
    <AppShell>
      <div className="mx-auto max-w-3xl">
        <p className="text-xs font-semibold uppercase tracking-widest text-cyan-300">Connection verification</p>
        <h1 className="mt-2 text-3xl font-semibold text-white">Verify {website.domain}</h1>
        <p className="mt-2 text-sm text-slate-400">Registered website: <a href={websiteUrl ?? undefined} target="_blank" rel="noopener noreferrer" className="text-cyan-300 underline">{websiteUrl ?? website.domain}</a></p>
        <p className="mt-2 text-sm text-slate-400">Install the SDK on this website, open it in another tab, browse for a few seconds, then return here and select Check Again.</p>

        <div className="mt-6 space-y-4">
          {["Checking SDK...", "Checking telemetry...", "Checking ingestion..."].map((step) => (
            <div key={step} className="flex items-center gap-3 rounded-xl border border-slate-800 bg-slate-950 px-4 py-3 text-slate-300">
              {telemetryQuery.isFetching ? <LoaderCircle className="h-4 w-4 animate-spin text-cyan-300" /> : connected ? <CheckCircle2 className="h-4 w-4 text-emerald-300" /> : <Circle className="h-4 w-4 text-slate-600" />}
              <span>{step}</span>
            </div>
          ))}
        </div>

        {telemetryQuery.error ? <div role="alert" className="mt-8 border border-red-800/50 bg-red-950/20 p-5 text-sm text-red-200"><p className="font-semibold">Connection could not be verified.</p><p className="mt-2">{telemetryQuery.error.message}</p><p className="mt-2">Please check the SDK installation, connection key, API endpoint, registered website URL/origin, backend availability, and browser console errors.</p></div> : connected && telemetry?.last_event ? <div className="mt-8 border border-emerald-700/50 bg-emerald-950/20 p-5 text-sm text-slate-200"><p className="font-semibold text-emerald-200">✓ SDK detected</p><p className="mt-1 text-emerald-200">✓ Telemetry received</p><p className="mt-1 text-emerald-200">✓ Ingestion working</p><p className="mt-2 font-semibold text-emerald-200">Website connected successfully.</p><p className="mt-2">Events received: {telemetry.event_count}</p><p className="mt-1">Last event: {telemetry.last_event.event_type}</p><p className="mt-1">Last received: {new Date(telemetry.last_event.created_at).toLocaleString()}</p></div> : <div className="mt-8 border border-amber-700/50 bg-amber-950/20 p-5 text-sm text-amber-100"><p className="font-semibold">We have not received telemetry yet.</p><p className="mt-2">Open your registered website and make sure the WebIntelX SDK is installed correctly. Browse the site, then select Check Again.</p></div>}

        <div className="mt-6">
          <div className="flex flex-wrap gap-3">
            <button type="button" onClick={() => telemetryQuery.refetch()} disabled={telemetryQuery.isFetching} className="rounded-xl bg-cyan-500 px-4 py-2.5 font-medium text-slate-950 hover:bg-cyan-400 disabled:opacity-60">{telemetryQuery.isFetching ? "Checking..." : "Check Again"}</button>
            {websiteUrl && <a href={`${websiteUrl}/`} target="_blank" rel="noopener noreferrer" className="rounded-xl border border-slate-700 bg-slate-900 px-4 py-2.5 font-medium text-slate-200 hover:border-cyan-500/40">Open Website</a>}
            {connected && <Link href="/dashboard" className="rounded-xl border border-slate-700 bg-slate-900 px-4 py-2.5 font-medium text-slate-200 hover:border-cyan-500/40">Open Security Dashboard</Link>}
            <Link href={`/websites/${websiteId}/setup`} className="rounded-xl border border-slate-700 bg-slate-900 px-4 py-2.5 font-medium text-slate-200">Installation Instructions</Link>
          </div>
        </div>
      </div>
    </AppShell>
  );
}

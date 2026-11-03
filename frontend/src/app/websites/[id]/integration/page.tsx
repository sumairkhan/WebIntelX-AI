"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, CheckCircle2, CircleHelp, LoaderCircle } from "lucide-react";
import { AppShell } from "@/components/app-shell";
import { useBrowserStoredValue } from "@/lib/browser-storage";
import { eventsApi, isWebsiteConnected, WebsiteType, websitesApi } from "@/lib/api";
import { WebsiteCredentialsPanel } from "@/components/website-credentials-panel";

const names: Record<WebsiteType, string> = {
  custom: "Custom Website",
  wordpress: "WordPress",
  shopify: "Shopify",
  woocommerce: "WooCommerce",
  other: "Other",
};

export default function WebsiteIntegrationPage() {
  const params = useParams<{ id: string }>();
  const websiteId = Number(params.id);
  const [integrationType] = useBrowserStoredValue<WebsiteType>(`webintelx-website-${websiteId}-type`, "custom", (value) =>
    value && value in names ? value as WebsiteType : "custom",
  );
  const { data: website, isLoading: websiteLoading } = useQuery({ queryKey: ["website", websiteId], enabled: Number.isSafeInteger(websiteId) && websiteId > 0, queryFn: () => websitesApi.get(websiteId) });
  const telemetryQuery = useQuery({ queryKey: ["website-telemetry", websiteId], enabled: !!website, queryFn: () => eventsApi.telemetry(websiteId), retry: false });

  if (websiteLoading) return <AppShell><p className="text-sm text-slate-400">Loading integration...</p></AppShell>;
  if (!website) return <AppShell><div className="border border-red-900/50 bg-red-950/30 p-5 text-sm text-red-200">Website could not be loaded. Verify your account access.</div></AppShell>;

  const telemetry = telemetryQuery.data;
  const connected = isWebsiteConnected(website, telemetry);
  const connectionStatus = website.status !== "active" ? "Inactive" : telemetryQuery.isError ? "Unavailable" : connected ? "Connected" : "Waiting for Telemetry";

  return <AppShell>
    <div className="mx-auto max-w-4xl">
      <Link href={`/websites/${websiteId}`} className="inline-flex items-center gap-2 text-sm text-slate-400 hover:text-white"><ArrowLeft className="h-4 w-4" /> {website.domain}</Link>
      <div className="mt-5 border-b border-slate-800 pb-6"><p className="text-xs font-semibold uppercase tracking-widest text-cyan-300">Website integration</p><h1 className="mt-2 text-3xl font-semibold text-white">Connection details</h1><p className="mt-1 text-sm text-slate-400">SDK connection and telemetry status for {website.domain}.</p></div>
      <div className="mt-6 grid gap-4 sm:grid-cols-2">
        <div className="border border-slate-800 bg-slate-900 p-5"><p className="text-xs uppercase tracking-widest text-slate-500">Connection Status</p><p className={`mt-2 font-semibold ${connected ? "text-emerald-300" : connectionStatus === "Inactive" ? "text-slate-400" : "text-amber-200"}`}>{connectionStatus}</p></div>
        <div className="border border-slate-800 bg-slate-900 p-5"><p className="text-xs uppercase tracking-widest text-slate-500">SDK Status</p><p className="mt-2 font-semibold text-white">{connected ? "Telemetry detected" : "Not detected"}</p></div>
        <div className="border border-slate-800 bg-slate-900 p-5"><p className="text-xs uppercase tracking-widest text-slate-500">Last Telemetry Received</p><p className="mt-2 text-sm text-white">{telemetry?.last_event ? `${telemetry.last_event.event_type} · ${new Date(telemetry.last_event.created_at).toLocaleString()}` : "No event received"}</p></div>
        <div className="border border-slate-800 bg-slate-900 p-5"><p className="text-xs uppercase tracking-widest text-slate-500">Integration Type</p><p className="mt-2 font-semibold text-white">{names[integrationType]} · JavaScript SDK</p></div>
      </div>
      <div className="mt-6 flex flex-wrap gap-3"><Link href={`/websites/${websiteId}/setup`} className="inline-flex items-center gap-2 rounded-lg bg-cyan-400 px-4 py-2.5 text-sm font-semibold text-slate-950">View Installation Instructions</Link><button type="button" onClick={() => telemetryQuery.refetch()} disabled={telemetryQuery.isFetching} className="inline-flex items-center gap-2 rounded-lg border border-slate-700 px-4 py-2.5 text-sm text-slate-200 disabled:opacity-60">{telemetryQuery.isFetching ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <CheckCircle2 className="h-4 w-4" />} Verify Connection</button></div>
      {telemetryQuery.isError && <p role="alert" className="mt-4 border border-red-800/50 bg-red-950/20 p-3 text-sm text-red-200">Could not retrieve telemetry from the backend: {telemetryQuery.error.message}</p>}
      {!connected && !telemetryQuery.isError && <p className="mt-4 flex items-start gap-2 text-sm text-slate-400"><CircleHelp className="mt-0.5 h-4 w-4 shrink-0" />The SDK is considered detected only after actual telemetry arrives. No connection status is inferred from configuration alone.</p>}
      <WebsiteCredentialsPanel website={website} />
    </div>
  </AppShell>;
}

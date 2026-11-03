"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { ArrowLeft, LoaderCircle } from "lucide-react";
import { toast } from "sonner";
import { AppShell } from "@/components/app-shell";
import { useBrowserStoredValue } from "@/lib/browser-storage";
import { eventsApi, isWebsiteConnected, WebsiteType, websitesApi } from "@/lib/api";
import { WebsiteCredentialsPanel } from "@/components/website-credentials-panel";

const integrationNames: Record<WebsiteType, string> = { custom: "Custom Website", wordpress: "WordPress", shopify: "Shopify", woocommerce: "WooCommerce", other: "Other" };

export default function WebsiteSettingsPage() {
  const params = useParams<{ id: string }>();
  const websiteId = Number(params.id);
  const router = useRouter();
  const queryClient = useQueryClient();
  const [draft, setDraft] = useState<{ id: number; name: string; domain: string } | null>(null);
  const [integrationType] = useBrowserStoredValue<WebsiteType>(`webintelx-website-${websiteId}-type`, "custom", (value) =>
    value && value in integrationNames ? value as WebsiteType : "custom",
  );
  const [saving, setSaving] = useState(false);
  const [confirmRemove, setConfirmRemove] = useState(false);
  const [removing, setRemoving] = useState(false);

  const { data: website, isLoading } = useQuery({ queryKey: ["website", websiteId], enabled: Number.isSafeInteger(websiteId) && websiteId > 0, queryFn: () => websitesApi.get(websiteId) });
  const telemetryQuery = useQuery({ queryKey: ["website-telemetry", websiteId], enabled: !!website, queryFn: () => eventsApi.telemetry(websiteId), retry: false });

  if (isLoading) return <AppShell><p className="text-sm text-slate-400">Loading settings...</p></AppShell>;
  if (!website) return <AppShell><div className="border border-red-900/50 bg-red-950/30 p-5 text-sm text-red-200">Website could not be loaded. Verify your account access.</div></AppShell>;

  const name = draft?.id === websiteId ? draft.name : website.name;
  const domain = draft?.id === websiteId ? draft.domain : website.domain;

  const updateWebsite = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSaving(true);
    try {
      const normalizedDomain = new URL(domain.includes("://") ? domain : `https://${domain}`).hostname.toLowerCase().replace(/\.$/, "");
      await websitesApi.update(websiteId, { name: name.trim(), domain: normalizedDomain });
      setDraft({ id: websiteId, name: name.trim(), domain: normalizedDomain });
      await queryClient.invalidateQueries({ queryKey: ["websites"] });
      await queryClient.invalidateQueries({ queryKey: ["website", websiteId] });
      toast.success("Website settings updated.");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Website update failed.");
    } finally {
      setSaving(false);
    }
  };

  const removeWebsite = async () => {
    setRemoving(true);
    try {
      await websitesApi.remove(websiteId);
      toast.success("Website removed from active monitoring.");
      router.push("/websites");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Website could not be removed.");
      setRemoving(false);
    }
  };

  const connectionStatus = website.status !== "active" ? "Inactive" : telemetryQuery.isError ? "Unavailable" : isWebsiteConnected(website, telemetryQuery.data) ? "Connected" : "Waiting for Telemetry";

  return <AppShell>
    <div className="mx-auto max-w-4xl">
      <Link href={`/websites/${websiteId}`} className="inline-flex items-center gap-2 text-sm text-slate-400 hover:text-white"><ArrowLeft className="h-4 w-4" /> {website.domain}</Link>
      <div className="mt-5 border-b border-slate-800 pb-6"><p className="text-xs font-semibold uppercase tracking-widest text-cyan-300">Configuration</p><h1 className="mt-2 text-3xl font-semibold text-white">Website settings</h1></div>
      <form onSubmit={updateWebsite} className="mt-6 max-w-2xl space-y-5">
        <div><label htmlFor="site-name" className="mb-2 block text-sm font-medium text-slate-200">Website Name</label><input id="site-name" value={name} onChange={(event) => setDraft({ id: websiteId, name: event.target.value, domain })} required minLength={1} className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3.5 py-3 text-white outline-none focus:border-cyan-400" /></div>
        <div><label htmlFor="site-domain" className="mb-2 block text-sm font-medium text-slate-200">Domain</label><input id="site-domain" value={domain} onChange={(event) => setDraft({ id: websiteId, name, domain: event.target.value })} required className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3.5 py-3 text-white outline-none focus:border-cyan-400" /></div>
        <div className="grid gap-3 border-y border-slate-800 py-4 text-sm sm:grid-cols-2"><span className="text-slate-500">Status</span><span className="text-white">{website.status}</span><span className="text-slate-500">Created At</span><span className="text-white">{website.created_at ? new Date(website.created_at).toLocaleString() : "Not available"}</span><span className="text-slate-500">Integration Method</span><span className="text-white">{integrationNames[integrationType]} · JavaScript SDK</span><span className="text-slate-500">Connection Status</span><span className="text-white">{connectionStatus}</span></div>
        <button type="submit" disabled={saving} className="inline-flex items-center gap-2 rounded-lg bg-cyan-400 px-4 py-2.5 text-sm font-semibold text-slate-950 disabled:opacity-60">{saving && <LoaderCircle className="h-4 w-4 animate-spin" />}{saving ? "Saving..." : "Update Website"}</button>
      </form>
      <div className="mt-7 flex flex-wrap gap-3 border-t border-slate-800 pt-5"><button type="button" onClick={() => telemetryQuery.refetch()} disabled={telemetryQuery.isFetching} className="rounded-lg border border-slate-700 px-4 py-2.5 text-sm text-slate-200">{telemetryQuery.isFetching ? "Checking..." : "Verify Connection"}</button><Link href={`/websites/${websiteId}/integration`} className="rounded-lg border border-slate-700 px-4 py-2.5 text-sm text-slate-200">Integration Details</Link><button type="button" onClick={() => setConfirmRemove(true)} className="rounded-lg border border-red-900/60 px-4 py-2.5 text-sm text-red-200">Remove Website</button></div>
      <WebsiteCredentialsPanel website={website} />
    </div>
    {confirmRemove && <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"><section role="dialog" aria-modal="true" aria-labelledby="settings-remove-title" className="w-full max-w-lg border border-slate-700 bg-slate-900 p-6"><h2 id="settings-remove-title" className="text-xl font-semibold text-white">Remove {website.domain}?</h2><p className="mt-3 text-sm leading-6 text-slate-300">Removing this website will stop monitoring and deactivate its ingestion credentials. Future telemetry will be rejected. Historical data follows the backend retention policy and is not permanently deleted by this action.</p><div className="mt-6 flex justify-end gap-3"><button type="button" onClick={() => setConfirmRemove(false)} disabled={removing} className="rounded-lg border border-slate-700 px-4 py-2.5 text-sm text-slate-200">Cancel</button><button type="button" onClick={removeWebsite} disabled={removing} className="rounded-lg bg-red-500 px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-60">{removing ? "Removing..." : "Remove Website"}</button></div></section></div>}
  </AppShell>;
}

"use client";

import { useQueries, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";
import { Activity, ArrowUpRight, Settings2, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { AppShell } from "@/components/app-shell";
import { eventsApi, isWebsiteConnected, Website, websitesApi } from "@/lib/api";

const actionClass = "inline-flex items-center gap-1.5 text-sm text-slate-300 hover:text-cyan-200";

export default function WebsitesPage() {
  const queryClient = useQueryClient();
  const [removing, setRemoving] = useState<Website | null>(null);
  const [isRemoving, setIsRemoving] = useState(false);
  const { data: websites = [], isLoading } = useQuery({
    queryKey: ["websites"],
    queryFn: websitesApi.list,
  });
  const telemetryQueries = useQueries({
    queries: websites.map((website) => ({
      queryKey: ["website-telemetry", website.id],
      queryFn: () => eventsApi.telemetry(website.id),
      retry: false,
    })),
  });

  const removeWebsite = async () => {
    if (!removing) return;
    setIsRemoving(true);
    try {
      await websitesApi.remove(removing.id);
      await queryClient.invalidateQueries({ queryKey: ["websites"] });
      await queryClient.invalidateQueries({ queryKey: ["website-telemetry", removing.id] });
      toast.success("Website removed from active monitoring.");
      setRemoving(null);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Website could not be removed.");
    } finally {
      setIsRemoving(false);
    }
  };

  return (
    <AppShell>
      <div className="space-y-5">
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-cyan-300">WebIntelX inventory</p>
            <h1 className="mt-2 text-3xl font-semibold text-white">Websites</h1>
            <p className="mt-1 text-sm text-slate-400">Manage the websites connected to your WebIntelX account.</p>
          </div>
          <Link href="/websites/new" className="w-fit rounded-lg bg-cyan-400 px-4 py-2.5 text-sm font-semibold text-slate-950 hover:bg-cyan-300">
            Add Website
          </Link>
        </div>

        {isLoading ? (
          <div className="border border-slate-800 bg-slate-900 p-10 text-slate-400">Loading websites...</div>
        ) : websites.length === 0 ? (
          <div className="border border-dashed border-slate-700 bg-slate-900 p-10 text-center">
            <Activity className="mx-auto h-7 w-7 text-cyan-300" />
            <p className="mt-4 font-medium text-white">No websites yet</p>
            <p className="mt-1 text-sm text-slate-400">Add your first website to begin setting up telemetry.</p>
            <Link href="/websites/new" className="mt-5 inline-flex rounded-lg bg-cyan-400 px-4 py-2.5 text-sm font-semibold text-slate-950">Add Website</Link>
          </div>
        ) : (
          <div className="overflow-x-auto border border-slate-800 bg-slate-900">
            <table className="min-w-[1050px] w-full text-left text-sm text-slate-200">
              <thead className="bg-slate-950 text-[11px] uppercase tracking-[0.14em] text-slate-400">
                <tr>
                  <th className="px-4 py-3">Website</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Last Telemetry</th>
                  <th className="px-4 py-3">Events</th>
                  <th className="px-4 py-3">Findings</th>
                  <th className="px-4 py-3">Risk</th>
                  <th className="px-4 py-3">Actions</th>
                </tr>
              </thead>
              <tbody>
                {websites.map((site, index) => {
                  const query = telemetryQueries[index];
                  const telemetry = query?.data;
                  const status = site.status.toLowerCase() !== "active"
                    ? "Inactive"
                    : query?.isError
                      ? "Status unavailable"
                      : isWebsiteConnected(site, telemetry)
                        ? "Connected"
                        : "Waiting for Telemetry";
                  const statusTone = status === "Connected" ? "text-emerald-300" : status === "Inactive" ? "text-slate-400" : status === "Waiting for Telemetry" ? "text-amber-200" : "text-red-200";
                  return (
                  <tr key={site.id} className="border-t border-slate-800">
                    <td className="px-4 py-4"><p className="font-medium text-white">{site.name}</p><p className="mt-0.5 text-xs text-slate-400">{site.domain}</p></td>
                    <td className={`px-4 py-4 ${statusTone}`}>{status}</td>
                    <td className="px-4 py-4 text-slate-300">{query?.isLoading ? "Loading..." : telemetry?.last_event?.created_at ? new Date(telemetry.last_event.created_at).toLocaleString() : "No telemetry"}</td>
                    <td className="px-4 py-4">{telemetry?.event_count ?? (query?.isError ? "Unavailable" : "—")}</td>
                    <td className="px-4 py-4">{telemetry?.finding_count ?? (query?.isError ? "Unavailable" : "—")}</td>
                    <td className="px-4 py-4 text-slate-500">Not evaluated</td>
                    <td className="px-4 py-4">
                      <div className="flex items-center gap-4">
                        <Link href={`/websites/${site.id}`} className={actionClass}>View</Link>
                        <Link href={`/websites/${site.id}/integration`} className={actionClass}>Integration</Link>
                        <Link href={`/websites/${site.id}/settings`} aria-label={`Settings for ${site.domain}`} className={actionClass}><Settings2 className="h-4 w-4" /></Link>
                        <button type="button" onClick={() => setRemoving(site)} className="inline-flex items-center gap-1.5 text-sm text-red-300 hover:text-red-200"><Trash2 className="h-4 w-4" /> Remove</button>
                      </div>
                    </td>
                  </tr>
                )})}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {removing && <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setRemoving(null); }}>
        <section role="dialog" aria-modal="true" aria-labelledby="remove-title" className="w-full max-w-lg border border-slate-700 bg-slate-900 p-6 shadow-2xl">
          <p className="text-xs font-semibold uppercase tracking-widest text-red-300">Website management</p>
          <h2 id="remove-title" className="mt-2 text-xl font-semibold text-white">Remove {removing.domain}?</h2>
          <p className="mt-3 text-sm leading-6 text-slate-300">You are about to remove {removing.domain} from WebIntelX AI. Monitoring will stop, future telemetry will no longer be accepted, and active ingestion credentials will be revoked. Existing historical data follows the backend retention policy and is not physically deleted by this action. This action cannot be casually undone.</p>
          <div className="mt-4 grid gap-1 border-y border-slate-800 py-3 text-sm sm:grid-cols-[90px_1fr]"><span className="text-slate-500">Website</span><span className="text-white">{removing.domain}</span><span className="text-slate-500">Status</span><span className="text-white">{removing.status}</span></div>
          <div className="mt-6 flex justify-end gap-3"><button type="button" onClick={() => setRemoving(null)} disabled={isRemoving} className="rounded-lg border border-slate-700 px-4 py-2.5 text-sm text-slate-200">Cancel</button><button type="button" onClick={removeWebsite} disabled={isRemoving} className="inline-flex items-center gap-2 rounded-lg bg-red-500 px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-60">{isRemoving ? "Removing..." : "Remove Website"}<ArrowUpRight className="h-4 w-4" /></button></div>
        </section>
      </div>}
    </AppShell>
  );
}

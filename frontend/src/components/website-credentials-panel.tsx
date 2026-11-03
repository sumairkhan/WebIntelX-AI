"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Copy, KeyRound, RotateCw, ShieldOff } from "lucide-react";
import { toast } from "sonner";
import { CredentialMetadata, credentialsApi, INGESTION_ENDPOINT, Website, WEBINTELX_SDK_URL } from "@/lib/api";

function installationCode(credential: string) {
  return `<script src="${WEBINTELX_SDK_URL}"></script>\n<script>\nWebIntelX.init({\n    credential: "${credential}",\n    endpoint: "${INGESTION_ENDPOINT}"\n});\n</script>`;
}

export function WebsiteCredentialsPanel({ website }: { website: Website }) {
  const queryClient = useQueryClient();
  const [newCredential, setNewCredential] = useState<string | null>(null);
  const [rotateConfirm, setRotateConfirm] = useState(false);
  const [revokeTarget, setRevokeTarget] = useState<CredentialMetadata | null>(null);
  const [working, setWorking] = useState(false);
  const queryKey = ["credentials", website.id];

  const { data: credentials = [], isLoading, isError } = useQuery({
    queryKey,
    queryFn: () => credentialsApi.list(website.id),
  });
  const active = credentials.find((credential) => credential.status === "active");

  const refresh = async () => {
    await queryClient.invalidateQueries({ queryKey });
  };

  const rotate = async () => {
    if (!active || website.status !== "active") return;
    setWorking(true);
    try {
      const created = await credentialsApi.rotate(website.id, active.id);
      setNewCredential(created.credential);
      setRotateConfirm(false);
      await refresh();
      toast.success("Connection key rotated. The old key is no longer valid.");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Key rotation failed.");
    } finally {
      setWorking(false);
    }
  };

  const revoke = async () => {
    if (!revokeTarget) return;
    setWorking(true);
    try {
      await credentialsApi.revoke(website.id, revokeTarget.id);
      setRevokeTarget(null);
      setNewCredential(null);
      await refresh();
      toast.success("Connection key revoked.");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Key revocation failed.");
    } finally {
      setWorking(false);
    }
  };

  const copy = async (value: string, message: string) => {
    try {
      await navigator.clipboard.writeText(value);
      toast.success(message);
    } catch {
      toast.error("Clipboard access was blocked by the browser.");
    }
  };

  return (
    <section className="border-t border-slate-800 py-6">
      <div className="flex items-center gap-3">
        <div className="rounded-lg bg-cyan-400/10 p-2 text-cyan-300"><KeyRound className="h-5 w-5" /></div>
        <div><h2 className="font-semibold text-white">Connection key</h2><p className="text-sm text-slate-400">Raw key values are never retrieved from the backend.</p></div>
      </div>
      {isLoading ? <p className="mt-4 text-sm text-slate-400">Loading key status...</p> : isError ? <p role="alert" className="mt-4 text-sm text-red-200">Credential status could not be loaded.</p> : <div className="mt-4 flex flex-wrap items-center gap-3 text-sm">
        <span className={active ? "text-emerald-300" : "text-slate-400"}>Key status: {active ? "Active" : "No active key"}</span>
        <span className="text-slate-600">·</span><span className="text-slate-400">{credentials.length} credential record{credentials.length === 1 ? "" : "s"}</span>
      </div>}
      <div className="mt-4 flex flex-wrap gap-3">
        <button type="button" onClick={() => setRotateConfirm(true)} disabled={!active || website.status !== "active" || working} className="inline-flex items-center gap-2 rounded-lg border border-slate-700 px-3.5 py-2 text-sm text-slate-200 hover:border-cyan-500/50 disabled:opacity-50"><RotateCw className="h-4 w-4" /> Rotate Key</button>
        <button type="button" onClick={() => active && setRevokeTarget(active)} disabled={!active || working} className="inline-flex items-center gap-2 rounded-lg border border-slate-700 px-3.5 py-2 text-sm text-red-200 hover:border-red-500/50 disabled:opacity-50"><ShieldOff className="h-4 w-4" /> Revoke Key</button>
      </div>
      {newCredential && <div className="mt-5 border border-amber-500/30 bg-amber-500/5 p-4">
        <p className="font-semibold text-amber-100">New key shown once. Update your website with the new snippet.</p>
        <p className="mt-1 text-sm text-slate-300">The old key is no longer valid.</p>
        <code className="mt-3 block overflow-x-auto bg-slate-950 p-3 text-sm text-cyan-200">{newCredential}</code>
        <button type="button" onClick={() => copy(newCredential, "New key copied")} className="mt-3 inline-flex items-center gap-2 rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-200"><Copy className="h-4 w-4" /> Copy Key</button>
        <pre className="mt-4 overflow-x-auto border border-slate-800 bg-slate-950 p-4 text-xs leading-6 text-cyan-100">{installationCode(newCredential)}</pre>
        <button type="button" onClick={() => copy(installationCode(newCredential), "Updated installation snippet copied")} className="mt-3 inline-flex items-center gap-2 rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-200"><Copy className="h-4 w-4" /> Copy Updated Snippet</button>
      </div>}
      <ul className="mt-5 space-y-2">
        {credentials.map((credential) => <li key={credential.id} className="flex items-center justify-between gap-3 border-t border-slate-800 py-3 text-sm"><span className="text-slate-300">Created {new Date(credential.created_at).toLocaleString()}</span><span className={credential.status === "active" ? "text-emerald-300" : "text-slate-500"}>{credential.status}</span></li>)}
      </ul>

      {rotateConfirm && <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"><section role="dialog" aria-modal="true" aria-labelledby="rotate-title" className="w-full max-w-md border border-slate-700 bg-slate-900 p-6"><h3 id="rotate-title" className="text-lg font-semibold text-white">Rotate connection key?</h3><p className="mt-3 text-sm leading-6 text-slate-300">Your current connection key will stop working immediately. You must update the SDK snippet on {website.domain}.</p><div className="mt-6 flex justify-end gap-3"><button type="button" onClick={() => setRotateConfirm(false)} className="rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-200">Cancel</button><button type="button" onClick={rotate} disabled={working} className="inline-flex items-center gap-2 rounded-lg bg-cyan-400 px-4 py-2 text-sm font-semibold text-slate-950 disabled:opacity-60">{working ? "Rotating..." : "Rotate Key"}</button></div></section></div>}
      {revokeTarget && <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"><section role="dialog" aria-modal="true" aria-labelledby="revoke-title" className="w-full max-w-md border border-slate-700 bg-slate-900 p-6"><h3 id="revoke-title" className="text-lg font-semibold text-white">Revoke connection key?</h3><p className="mt-3 text-sm leading-6 text-slate-300">The key will stop accepting telemetry from {website.domain}. Existing telemetry remains under the backend retention policy.</p><div className="mt-6 flex justify-end gap-3"><button type="button" onClick={() => setRevokeTarget(null)} className="rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-200">Cancel</button><button type="button" onClick={revoke} disabled={working} className="rounded-lg bg-red-500 px-4 py-2 text-sm font-semibold text-white disabled:opacity-60">{working ? "Revoking..." : "Revoke Key"}</button></div></section></div>}
    </section>
  );
}

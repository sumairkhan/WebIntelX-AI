"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { ArrowRight, Globe2, ShieldCheck } from "lucide-react";
import { AppShell } from "@/components/app-shell";
import { websitesApi } from "@/lib/api";

export default function OnboardingPage() {
  const router = useRouter();
  const { data: websites, isLoading, isError } = useQuery({ queryKey: ["websites"], queryFn: websitesApi.list, retry: false });

  useEffect(() => {
    if (websites?.length) router.replace("/dashboard");
  }, [router, websites?.length]);

  return <AppShell>
    <div className="mx-auto max-w-3xl border-t border-slate-800 py-9">
      <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-cyan-400/10 text-cyan-200"><ShieldCheck className="h-6 w-6" /></div>
      <p className="mt-7 text-xs font-semibold uppercase tracking-[0.18em] text-cyan-300">Welcome to WebIntelX AI</p>
      <h1 className="mt-2 text-3xl font-semibold text-white">Connect your first website</h1>
      <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-300">Add the customer website you want to monitor. WebIntelX will guide you through creating a limited-scope connection key, installing the JavaScript SDK, and verifying real telemetry.</p>
      <div className="mt-7 grid gap-4 border-y border-slate-800 py-5 sm:grid-cols-2">
        <div className="flex gap-3"><Globe2 className="mt-0.5 h-5 w-5 shrink-0 text-cyan-300" /><div><p className="font-medium text-white">Customer Website</p><p className="mt-1 text-sm text-slate-400">Where the WebIntelX SDK is installed.</p></div></div>
        <div className="flex gap-3"><ShieldCheck className="mt-0.5 h-5 w-5 shrink-0 text-emerald-300" /><div><p className="font-medium text-white">WebIntelX Portal</p><p className="mt-1 text-sm text-slate-400">Where you manage sites and review security activity.</p></div></div>
      </div>
      {isLoading ? <p className="mt-5 text-sm text-slate-400">Checking your website inventory...</p> : isError ? <p role="alert" className="mt-5 text-sm text-red-200">Could not load your website inventory. Check your API connection and sign-in status, then refresh this page.</p> : !websites?.length ? <Link href="/websites/new" className="mt-7 inline-flex items-center gap-2 rounded-lg bg-cyan-400 px-4 py-3 text-sm font-semibold text-slate-950 hover:bg-cyan-300">Add Website <ArrowRight className="h-4 w-4" /></Link> : <p className="mt-5 text-sm text-slate-400">Opening your dashboard...</p>}
    </div>
  </AppShell>;
}

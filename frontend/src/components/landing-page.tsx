import Link from "next/link";
import { ArrowRight, ShieldCheck, Sparkles } from "lucide-react";

export function LandingPage() {
  return (
    <div className="min-h-screen bg-[#060d18] text-slate-100">
      <div className="mx-auto max-w-7xl px-6 py-8">
        <header className="flex items-center justify-between py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-cyan-500/15 text-cyan-300 ring-1 ring-cyan-500/30">
              <ShieldCheck className="h-5 w-5" />
            </div>
            <div>
              <p className="text-lg font-semibold">WebIntelX AI</p>
              <p className="text-xs text-slate-400">Security Intelligence</p>
            </div>
          </div>
          <Link href="/login" className="rounded-xl border border-slate-700 bg-slate-900 px-4 py-2 text-sm text-slate-200 transition hover:border-cyan-500/40 hover:text-cyan-200">
            Sign In
          </Link>
        </header>

        <main className="grid items-center gap-12 py-16 lg:grid-cols-[1.15fr_0.85fr] lg:py-24">
          <div>
            <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-cyan-500/20 bg-cyan-500/10 px-3 py-1 text-xs uppercase tracking-[0.22em] text-cyan-200">
              <Sparkles className="h-3.5 w-3.5" />
              AI-Powered Web Security Intelligence
            </div>
            <h1 className="max-w-xl text-5xl font-semibold tracking-tight text-white md:text-6xl">
              Detect suspicious behavior.
              <span className="block text-cyan-300">Investigate attack chains.</span>
            </h1>
            <p className="mt-6 max-w-xl text-lg text-slate-300">
              Detect suspicious behavior, investigate attack chains, correlate security signals, and understand web threats with AI across your digital footprint.
            </p>
            <div className="mt-8 flex flex-wrap gap-4">
              <Link href="/register" className="inline-flex items-center gap-2 rounded-xl bg-cyan-500 px-5 py-3 font-medium text-slate-950 transition hover:bg-cyan-400">
                Get Started
                <ArrowRight className="h-4 w-4" />
              </Link>
              <Link href="/login" className="rounded-xl border border-slate-700 bg-slate-900 px-5 py-3 font-medium text-slate-100 transition hover:border-slate-500 hover:bg-slate-800">
                Sign In
              </Link>
            </div>
          </div>

          <div className="rounded-3xl border border-slate-800 bg-slate-900/70 p-6 shadow-2xl shadow-cyan-950/20 ring-1 ring-slate-700">
            <div className="rounded-2xl border border-slate-800 bg-slate-950 p-5">
              <div className="mb-4 flex items-center justify-between">
                <div>
                  <p className="text-sm text-slate-400">Threat posture</p>
                  <p className="text-2xl font-semibold text-white">Elevated</p>
                </div>
                <div className="rounded-full bg-amber-500/15 px-2.5 py-1 text-xs font-medium text-amber-300">
                  Watchlist
                </div>
              </div>

              <div className="space-y-4">
                {[
                  { label: "Websites monitored", value: "08" },
                  { label: "Active investigations", value: "03" },
                  { label: "Anomalies detected", value: "24" },
                ].map((item) => (
                  <div key={item.label} className="flex items-center justify-between rounded-xl border border-slate-800 bg-slate-900 px-3 py-2.5">
                    <span className="text-sm text-slate-300">{item.label}</span>
                    <span className="text-base font-semibold text-white">{item.value}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}

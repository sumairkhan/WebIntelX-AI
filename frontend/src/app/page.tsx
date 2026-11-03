import Link from "next/link";
import { ArrowRight, BarChart3, CheckCircle2, Lock, Radar, ShieldCheck, Sparkles } from "lucide-react";

const features = [
  {
    icon: Radar,
    title: "Continuous telemetry",
    text: "Ingest website activity, event streams, and suspicious behavior in near real time.",
  },
  {
    icon: ShieldCheck,
    title: "AI-assisted investigations",
    text: "Correlate anomalies into human-readable findings that separate fact from inference.",
  },
  {
    icon: BarChart3,
    title: "Executive visibility",
    text: "Track detections, incidents, and trends with a modern security command-center dashboard.",
  },
];

const proofPoints = [
  "SOC-ready workflows",
  "Website attribution and ownership",
  "Explainable security intelligence",
  "Operational resilience tracking",
];

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-50">
      <header className="mx-auto flex max-w-7xl items-center justify-between px-6 py-6">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-cyan-500/15 text-cyan-300 ring-1 ring-cyan-400/30">
            <Lock className="h-5 w-5" />
          </div>
          <div>
            <p className="text-base font-semibold">WebIntelX AI</p>
            <p className="text-[10px] uppercase tracking-[0.2em] text-slate-400">Security Intelligence</p>
          </div>
        </div>

        <nav className="hidden items-center gap-8 text-sm text-slate-300 md:flex">
          <a href="#features" className="hover:text-white">Platform</a>
          <a href="#proof" className="hover:text-white">Trust</a>
          <a href="#security" className="hover:text-white">Security</a>
        </nav>

        <div className="flex items-center gap-3">
          <Link href="/login" className="rounded-xl border border-slate-700 bg-slate-900 px-4 py-2 text-sm text-slate-200 hover:border-cyan-500/40">
            Login
          </Link>
          <Link href="/register" className="rounded-xl bg-cyan-500 px-4 py-2 text-sm font-medium text-slate-950 hover:bg-cyan-400">
            Get started
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-6 pb-20 pt-8 md:pt-14">
        <section className="grid items-center gap-10 lg:grid-cols-[1.1fr_0.9fr]">
          <div>
            <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-cyan-500/25 bg-cyan-500/10 px-3 py-1.5 text-xs uppercase tracking-[0.2em] text-cyan-200">
              <Sparkles className="h-3.5 w-3.5" />
              Modern cyber defense
            </div>
            <h1 className="max-w-xl text-4xl font-semibold tracking-tight text-white md:text-6xl">
              Defend every website with AI-powered visibility.
            </h1>
            <p className="mt-6 max-w-xl text-lg text-slate-300">
              Monitor endpoints, detect anomalies, correlate related activity, and keep your security team focused on what matters most.
            </p>

            <div className="mt-8 flex flex-wrap gap-4">
              <Link href="/register" className="inline-flex items-center gap-2 rounded-xl bg-cyan-500 px-5 py-3 text-sm font-medium text-slate-950 hover:bg-cyan-400">
                Start free trial
                <ArrowRight className="h-4 w-4" />
              </Link>
              <Link href="/login" className="rounded-xl border border-slate-700 bg-slate-900 px-5 py-3 text-sm text-slate-200 hover:border-cyan-500/40">
                Sign in
              </Link>
            </div>

            <div className="mt-8 flex flex-wrap gap-5 text-sm text-slate-300">
              {proofPoints.map((item) => (
                <div key={item} className="inline-flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-emerald-300" />
                  {item}
                </div>
              ))}
            </div>
          </div>

          <div className="border border-slate-800 bg-slate-900 p-5 shadow-2xl shadow-cyan-950/20">
            <div className="border border-slate-800 bg-slate-950 p-5">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-cyan-300">Platform workflow</p>
              <h2 className="mt-2 text-xl font-semibold text-white">One path from signal to investigation</h2>
              <div className="mt-6 space-y-2">
                {["Customer Website", "WebIntelX JavaScript SDK", "FastAPI Ingestion", "Detection · ML · Correlation", "Investigation · WebIntelX Portal"].map((item, index) => (
                  <div key={item} className="flex items-center gap-3">
                    <span className="flex h-7 w-7 items-center justify-center rounded-full border border-cyan-500/30 text-xs text-cyan-200">{index + 1}</span>
                    <span className="flex-1 border-b border-slate-800 py-2.5 text-sm text-slate-200">{item}</span>
                  </div>
                ))}
              </div>
              <p className="mt-5 text-xs text-slate-500">All telemetry and investigation results are served by the WebIntelX backend.</p>
            </div>
          </div>
        </section>

        <section id="features" className="mt-24">
          <div className="mb-8 max-w-2xl">
            <p className="text-sm uppercase tracking-[0.2em] text-cyan-300">Platform capabilities</p>
            <h2 className="mt-3 text-3xl font-semibold text-white">Built for modern security teams.</h2>
          </div>

          <div className="grid gap-6 md:grid-cols-3">
            {features.map(({ icon: Icon, title, text }) => (
              <div key={title} className="rounded-3xl border border-slate-800 bg-slate-900 p-6">
                <div className="mb-4 inline-flex rounded-xl bg-cyan-500/10 p-3 text-cyan-300 ring-1 ring-cyan-400/20">
                  <Icon className="h-5 w-5" />
                </div>
                <h3 className="text-xl font-semibold text-white">{title}</h3>
                <p className="mt-3 text-sm leading-6 text-slate-300">{text}</p>
              </div>
            ))}
          </div>
        </section>

        <section id="security" className="mt-24 rounded-3xl border border-slate-800 bg-slate-900 p-8 md:p-10">
          <div className="flex flex-col gap-8 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <p className="text-sm uppercase tracking-[0.2em] text-cyan-300">Security first</p>
              <h2 className="mt-3 text-3xl font-semibold text-white">Explainable, accountable AI for security operations.</h2>
            </div>
            <Link href="/register" className="inline-flex items-center gap-2 rounded-xl bg-cyan-500 px-5 py-3 text-sm font-medium text-slate-950 hover:bg-cyan-400">
              Create account
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </section>
      </main>
    </div>
  );
}

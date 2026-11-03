"use client";

import { useState } from "react";
import { CheckCircle2, ArrowRight } from "lucide-react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { AppShell } from "@/components/app-shell";
import { Website, WebsiteType, websitesApi } from "@/lib/api";

const types: { value: WebsiteType; label: string }[] = [
  { value: "custom", label: "Custom Website" },
  { value: "wordpress", label: "WordPress" },
  { value: "shopify", label: "Shopify" },
  { value: "woocommerce", label: "WooCommerce" },
  { value: "other", label: "Other" },
];

export default function NewWebsitePage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [domain, setDomain] = useState("");
  const [websiteType, setWebsiteType] = useState<WebsiteType>("custom");
  const [created, setCreated] = useState<Website | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const onSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const websiteAddress = domain.trim();
    if (name.trim().length < 2 || websiteAddress.length < 3) {
      toast.error("Enter a website name and URL or domain.");
      return;
    }
    setIsSubmitting(true);
    try {
      const website = await websitesApi.create({
        name: name.trim(),
        domain: websiteAddress,
        status: "active",
      });
      window.localStorage.setItem(`webintelx-website-${website.id}-type`, websiteType);
      window.localStorage.setItem(`webintelx-website-${website.id}-step`, "0");
      setCreated(website);
      toast.success("Website added");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Website creation failed");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <AppShell>
      <div className="mx-auto max-w-3xl">
        <div className="mb-7 flex items-center gap-2 text-sm text-slate-400">
          <span className="rounded-full bg-cyan-400 px-2.5 py-1 font-semibold text-slate-950">1</span>
          <span className="text-white">Add Website</span><span className="mx-1">/</span><span>Connect</span><span className="mx-1">/</span><span>Verify</span>
        </div>

        {created ? (
          <section className="border-t border-slate-800 py-9">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-emerald-400/10 text-emerald-300">
              <CheckCircle2 className="h-6 w-6" />
            </div>
            <h1 className="mt-5 text-3xl font-semibold text-white">Website added</h1>
            <p className="mt-2 text-slate-400">Your website is ready for its connection key.</p>
            <div className="mt-7 grid gap-1 border-y border-slate-800 py-4 text-sm sm:grid-cols-[150px_1fr]">
              <span className="text-slate-400">Website</span><span className="font-medium text-white">{created.name}</span>
              <span className="text-slate-400">Website URL</span><span className="font-medium text-white">{created.origin ?? created.domain}</span>
            </div>
            <button type="button" onClick={() => router.push(`/websites/${created.id}/setup`)} className="mt-7 inline-flex items-center gap-2 rounded-lg bg-cyan-400 px-4 py-3 font-semibold text-slate-950 hover:bg-cyan-300">
              Continue <ArrowRight className="h-4 w-4" />
            </button>
          </section>
        ) : (
          <section className="max-w-2xl border-t border-slate-800 py-8">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-cyan-300">Website integration · Step 1</p>
            <h1 className="mt-3 text-3xl font-semibold text-white">Add your website</h1>
            <p className="mt-2 text-slate-400">Tell us which customer website you want WebIntelX to monitor.</p>
            <form onSubmit={onSubmit} className="mt-8 space-y-5">
              <div>
                <label htmlFor="website-name" className="mb-2 block text-sm font-medium text-slate-200">Website Name</label>
                <input id="website-name" value={name} onChange={(event) => setName(event.target.value)} required minLength={2} className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3.5 py-3 text-white outline-none focus:border-cyan-400" placeholder="Acme Store" />
              </div>
              <div>
                <label htmlFor="website-domain" className="mb-2 block text-sm font-medium text-slate-200">Website URL / Domain</label>
                <input id="website-domain" value={domain} onChange={(event) => setDomain(event.target.value)} required minLength={3} className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3.5 py-3 text-white outline-none focus:border-cyan-400" placeholder="https://example.com or http://localhost:5500" />
                <p className="mt-1.5 text-xs text-slate-500">Enter your exact website URL or domain, including a local development port when applicable. Path and query are not used for origin matching.</p>
              </div>
              <div>
                <label htmlFor="website-type" className="mb-2 block text-sm font-medium text-slate-200">Website Type</label>
                <select id="website-type" value={websiteType} onChange={(event) => setWebsiteType(event.target.value as WebsiteType)} className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3.5 py-3 text-white outline-none focus:border-cyan-400">
                  {types.map((type) => <option key={type.value} value={type.value}>{type.label}</option>)}
                </select>
              </div>
              <button type="submit" disabled={isSubmitting} className="rounded-lg bg-cyan-400 px-4 py-3 font-semibold text-slate-950 hover:bg-cyan-300 disabled:opacity-60">
                {isSubmitting ? "Adding website..." : "Add Website"}
              </button>
            </form>
          </section>
        )}
      </div>
    </AppShell>
  );
}

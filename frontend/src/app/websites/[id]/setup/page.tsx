"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { ArrowLeft, ArrowRight, Check, CheckCircle2, Copy, KeyRound, LoaderCircle, ShieldCheck } from "lucide-react";
import { toast } from "sonner";
import { AppShell } from "@/components/app-shell";
import { useBrowserStoredValue } from "@/lib/browser-storage";
import { CredentialMetadata, credentialsApi, eventsApi, INGESTION_ENDPOINT, isWebsiteConnected, WebsiteType, websitesApi, WEBINTELX_SDK_URL } from "@/lib/api";

const steps = ["Connection key", "Platform", "Install SDK", "Verify telemetry"];
const platforms: { value: WebsiteType; label: string; help: string }[] = [
  { value: "custom", label: "Custom Website", help: "For websites where you can edit HTML or JavaScript." },
  { value: "wordpress", label: "WordPress", help: "Use your site's custom code or header integration area." },
  { value: "shopify", label: "Shopify", help: "Install the snippet in your theme's global head section." },
  { value: "woocommerce", label: "WooCommerce", help: "WooCommerce runs on WordPress; use the WordPress method." },
  { value: "other", label: "Other", help: "For any platform that allows custom JavaScript." },
];
const platformInstructions: Record<WebsiteType, string[]> = {
  custom: ["Open your website source or tag manager.", "Find the global <head> section.", "Paste the generated WebIntelX code before </head>.", "Publish the website changes.", "Open your website in a separate tab.", "Return here and verify connection."],
  wordpress: ["Open WordPress Admin.", "Open the site's custom code or header integration area.", "Paste the WebIntelX installation code into the global head area.", "Save the code changes.", "Publish the changes if your tool requires publishing.", "Open the website in a separate tab.", "Return to WebIntelX.", "Click Verify Connection."],
  shopify: ["Open Shopify Admin.", "Open Online Store, then Themes.", "Choose the active theme and open its code editor.", "Open the global theme layout file and locate the head section.", "Paste the generated code before the closing head tag.", "Save and publish the theme changes.", "Open the store, return here, and verify connection."],
  woocommerce: ["Open WordPress Admin for your WooCommerce site.", "Open the site's custom code or header integration area.", "Paste the WebIntelX code into the global head area.", "Save and publish the changes.", "Open your store in a separate tab.", "Return to WebIntelX and verify connection."],
  other: ["Copy the generated WebIntelX code.", "Add it to the site's global <head> section.", "Publish the website changes.", "Open the website in a separate tab.", "Return here.", "Click Verify Connection."],
};

const boxClass = "border border-slate-800 bg-slate-900 p-5";
const buttonClass = "inline-flex items-center justify-center gap-2 rounded-lg bg-cyan-400 px-4 py-2.5 text-sm font-semibold text-slate-950 hover:bg-cyan-300 disabled:cursor-not-allowed disabled:opacity-60";
const secondaryClass = "inline-flex items-center justify-center gap-2 rounded-lg border border-slate-700 bg-slate-950 px-4 py-2.5 text-sm font-medium text-slate-200 hover:border-cyan-500/50";

function makeInstallCode(credential: string) {
  return `<script src="${WEBINTELX_SDK_URL}"></script>\n<script>\nWebIntelX.init({\n    credential: "${credential}",\n    endpoint: "${INGESTION_ENDPOINT}"\n});\n</script>`;
}

export default function WebsiteSetupPage() {
  const params = useParams<{ id: string }>();
  const websiteId = Number(params.id);
  const [credential, setCredential] = useState<string | null>(null);
  const [working, setWorking] = useState(false);

  const storageKey = `webintelx-website-${websiteId}`;
  const [activeStep, setActiveStep] = useBrowserStoredValue(`${storageKey}-step`, 0, (value) => {
    const parsed = Number(value);
    return Number.isInteger(parsed) && parsed >= 0 && parsed < steps.length ? parsed : 0;
  });
  const [platform, setPlatform] = useBrowserStoredValue<WebsiteType>(`${storageKey}-type`, "custom", (value) =>
    platforms.some((item) => item.value === value) ? value as WebsiteType : "custom",
  );

  const { data: website, isLoading: websiteLoading } = useQuery({
    queryKey: ["website", websiteId],
    enabled: Number.isSafeInteger(websiteId) && websiteId > 0,
    queryFn: () => websitesApi.get(websiteId),
  });

  const { data: credentials = [], refetch } = useQuery({
    queryKey: ["credentials", websiteId],
    enabled: Number.isSafeInteger(websiteId) && websiteId > 0,
    queryFn: () => credentialsApi.list(websiteId),
  });

  const telemetryQuery = useQuery({
    queryKey: ["website-telemetry", websiteId],
    enabled: false,
    queryFn: () => eventsApi.telemetry(websiteId),
    retry: false,
  });

  const activeCredential = credentials.find((item: CredentialMetadata) => item.status === "active");
  const telemetry = telemetryQuery.data;
  const connected = !telemetryQuery.isError && isWebsiteConnected(website, telemetry);

  const persistStep = (nextStep: number) => {
    setActiveStep(nextStep);
  };

  const persistPlatform = (nextPlatform: WebsiteType) => {
    setPlatform(nextPlatform);
  };

  const handleGenerate = async () => {
    if (!website || website.status !== "active") {
      toast.error("Activate this website before creating a connection key.");
      return;
    }
    setWorking(true);
    try {
      const created = activeCredential
        ? await credentialsApi.rotate(websiteId, activeCredential.id)
        : await credentialsApi.create(websiteId);
      setCredential(created.credential);
      await refetch();
      toast.success(activeCredential ? "Connection key rotated" : "Connection key created");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Key generation failed");
    } finally {
      setWorking(false);
    }
  };

  const copyText = async (text: string, message: string) => {
    try {
      await navigator.clipboard.writeText(text);
      toast.success(message);
    } catch {
      toast.error("Clipboard access was blocked by the browser.");
    }
  };

  const verify = async () => {
    const result = await telemetryQuery.refetch();
    if (result.error) {
      toast.error("Could not reach the telemetry service. Check the API and network settings.");
    } else if (result.data?.connected) {
      toast.success("Telemetry received from your website");
    } else if (result.data) {
      toast.info("No recent telemetry has been received yet.");
    }
  };

  const installCode = credential ? makeInstallCode(credential) : null;
  const platformLabel = platforms.find((item) => item.value === platform)?.label ?? "Custom Website";

  if (websiteLoading) {
    return <AppShell><p className="text-sm text-slate-400">Loading website setup...</p></AppShell>;
  }

  if (!website) {
    return <AppShell><div className="border border-red-900/50 bg-red-950/30 p-5 text-sm text-red-200">Website could not be loaded. Check that you are signed in and that this website belongs to your account.</div></AppShell>;
  }

  return (
    <AppShell>
      <div className="mx-auto max-w-5xl">
        <Link href="/websites" className="inline-flex items-center gap-2 text-sm text-slate-400 hover:text-white"><ArrowLeft className="h-4 w-4" /> Websites</Link>
        <div className="mt-6 flex flex-col justify-between gap-4 border-b border-slate-800 pb-6 md:flex-row md:items-end">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-cyan-300">Website integration</p>
            <h1 className="mt-2 text-3xl font-semibold text-white">Connect {website.origin ?? website.domain}</h1>
            <p className="mt-1 text-sm text-slate-400">Customer Website: {website.origin ?? website.domain} · WebIntelX Portal: this dashboard</p>
          </div>
          <Link href={`/websites/${websiteId}/integration`} className={secondaryClass}>Integration details</Link>
        </div>

        <ol className="my-7 grid grid-cols-2 gap-2 md:grid-cols-4">
          {steps.map((label, index) => (
            <li key={label} className={`flex items-center gap-2 border-b-2 px-2 py-3 text-xs ${index === activeStep ? "border-cyan-300 text-white" : index < activeStep ? "border-emerald-400 text-emerald-300" : "border-slate-800 text-slate-500"}`}>
              <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-current">{index < activeStep ? <Check className="h-3.5 w-3.5" /> : index + 1}</span>
              {label}
            </li>
          ))}
        </ol>

        {activeStep === 0 && <section className="max-w-3xl border-t border-slate-800 py-7">
          <div className="flex items-center gap-3"><div className="rounded-lg bg-cyan-400/10 p-2.5 text-cyan-300"><KeyRound className="h-5 w-5" /></div><div><p className="text-xs uppercase tracking-widest text-cyan-300">Step 2</p><h2 className="text-xl font-semibold text-white">Create your connection key</h2></div></div>
          <p className="mt-5 max-w-2xl text-sm leading-6 text-slate-300">This key lets the WebIntelX JavaScript SDK installed on <strong className="text-white">{website.domain}</strong> send telemetry to WebIntelX. It is limited to telemetry ingestion. It is not your login password, JWT, Groq API key, or a database credential.</p>
          {website.status !== "active" && <p className="mt-4 border border-amber-700/40 bg-amber-950/20 p-3 text-sm text-amber-200">This website is inactive. Activate it from Settings before creating a key.</p>}
          {credential ? <div className="mt-6 border border-amber-500/30 bg-amber-500/5 p-4">
            <p className="font-medium text-amber-200">Copy this key now. It is displayed only once.</p>
            <code className="mt-3 block overflow-x-auto bg-slate-950 p-3 text-sm text-cyan-200">{credential}</code>
            <button type="button" onClick={() => copyText(credential, "Connection key copied")} className={`${secondaryClass} mt-3`}><Copy className="h-4 w-4" /> Copy Key</button>
            <p className="mt-5 text-sm font-medium text-white">Where does this key go?</p>
            <p className="mt-1 text-sm text-slate-300">Use it inside the WebIntelX JavaScript SDK installed on the customer website you want to monitor.</p>
            <div className="mt-4 grid gap-2 text-center text-xs text-slate-300 sm:grid-cols-5">
              {["Customer Website", "WebIntelX SDK", "Connection Key", "Ingestion API", "Security Dashboard"].map((item, index) => <div key={item} className="flex items-center justify-center gap-2 rounded-md border border-slate-800 bg-slate-950 p-3">{item}{index < 4 && <span className="hidden text-cyan-300 sm:inline">↓</span>}</div>)}
            </div>
            <button type="button" onClick={() => persistStep(1)} className={`${buttonClass} mt-6`}>Continue <ArrowRight className="h-4 w-4" /></button>
          </div> : <div className="mt-6">
            {!activeCredential && <p className="mb-4 text-sm text-slate-400">A raw key cannot be retrieved later. If this setup was interrupted after key creation, generate a fresh key; the prior active key will be revoked.</p>}
            {activeCredential && <p className="mb-4 text-sm text-amber-200">An active key already exists. A fresh key will revoke it, and your installed website snippet must then be updated.</p>}
            <button type="button" onClick={handleGenerate} disabled={working || website.status !== "active"} className={buttonClass}>{working && <LoaderCircle className="h-4 w-4 animate-spin" />}{activeCredential ? "Generate New Connection Key" : "Generate Connection Key"}</button>
          </div>}
        </section>}

        {activeStep === 1 && <section className="border-t border-slate-800 py-7">
          <p className="text-xs uppercase tracking-widest text-cyan-300">Step 3</p><h2 className="mt-2 text-2xl font-semibold text-white">Choose an integration method</h2>
          <p className="mt-2 text-sm text-slate-400">Choose the platform used by {website.domain}. WebIntelX currently connects through the JavaScript SDK.</p>
          <div className="mt-6 grid gap-3 md:grid-cols-2">
            {platforms.map((item) => <button key={item.value} type="button" onClick={() => persistPlatform(item.value)} className={`border p-4 text-left transition ${platform === item.value ? "border-cyan-400 bg-cyan-400/5" : "border-slate-800 bg-slate-900 hover:border-slate-600"}`}>
              <span className="font-semibold text-white">{item.label}</span><span className="mt-1 block text-sm text-slate-400">{item.help}</span>
            </button>)}
          </div>
          <p className="mt-5 border-l-2 border-cyan-400 pl-3 text-sm text-slate-300">Your Customer Website is <strong className="text-white">{website.domain}</strong>. Install the SDK there. The WebIntelX Portal is where you manage websites, review visitors and events, investigate activity, view incidents and reports.</p>
          <div className="mt-6 flex gap-3"><button type="button" onClick={() => persistStep(0)} className={secondaryClass}><ArrowLeft className="h-4 w-4" /> Back</button><button type="button" onClick={() => persistStep(2)} className={buttonClass}>Continue <ArrowRight className="h-4 w-4" /></button></div>
        </section>}

        {activeStep === 2 && <section className="border-t border-slate-800 py-7">
          <p className="text-xs uppercase tracking-widest text-cyan-300">Step 4 · {platformLabel}</p><h2 className="mt-2 text-2xl font-semibold text-white">Install WebIntelX</h2>
          {platform === "wordpress" && <p className="mt-4 border border-amber-700/40 bg-amber-950/20 p-4 text-sm text-amber-100">WebIntelX currently uses JavaScript integration for WordPress. No official WebIntelX plugin is included.</p>}
          {platform === "shopify" && <p className="mt-4 border border-amber-700/40 bg-amber-950/20 p-4 text-sm text-amber-100">Native Shopify App integration is not currently available. Use the JavaScript integration method below.</p>}
          {platform === "woocommerce" && <p className="mt-4 border border-cyan-700/40 bg-cyan-950/20 p-4 text-sm text-cyan-100">WooCommerce runs on WordPress, so use the WordPress JavaScript installation method.</p>}
          {platform === "other" && <p className="mt-4 text-sm text-slate-300">If your platform allows custom JavaScript, add this snippet to the global <code className="text-cyan-200">&lt;head&gt;</code> section, publish, and open your website.</p>}
          <p className="mt-4 text-sm text-slate-300">{platform === "wordpress" ? "WebIntelX currently uses JavaScript integration for WordPress." : platform === "shopify" ? "Install the snippet through your Shopify theme. Native Shopify App integration is not currently available." : platform === "woocommerce" ? "Because WooCommerce runs on WordPress, use the WordPress JavaScript installation method." : "Add this code to the <head> section of your website."}</p>
          <ol className="mt-4 space-y-2">
            {platformInstructions[platform].map((instruction, index) => <li key={`${platform}-${index}`} className="flex items-start gap-3 text-sm text-slate-300"><span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-slate-700 text-xs text-cyan-200">{index + 1}</span><span className="pt-0.5">{instruction}</span></li>)}
          </ol>
          {!installCode ? <div className="mt-5 border border-amber-500/30 bg-amber-500/5 p-4 text-sm text-amber-100">The raw connection key is no longer available in this browser session. For security it cannot be loaded again. Return to Connection Key and generate a fresh key to create a new snippet.</div> : <>
            <pre className="mt-5 overflow-x-auto border border-slate-800 bg-slate-950 p-4 text-xs leading-6 text-cyan-100">{installCode}</pre>
            <button type="button" onClick={() => copyText(installCode, "Installation code copied")} className={`${secondaryClass} mt-3`}><Copy className="h-4 w-4" /> Copy Code</button>
            <div className="mt-7 grid gap-4 md:grid-cols-2">
              <div className={boxClass}><p className="text-xs font-semibold uppercase tracking-widest text-slate-400">Before</p><pre className="mt-3 overflow-x-auto text-xs leading-6 text-slate-300">{"<head>\n    <title>My Website</title>\n</head>"}</pre></div>
              <div className={boxClass}><p className="text-xs font-semibold uppercase tracking-widest text-emerald-300">After</p><pre className="mt-3 overflow-x-auto text-xs leading-6 text-slate-300">{"<head>\n    <title>My Website</title>\n\n    <!-- WebIntelX -->\n    "}{installCode.replaceAll("\n", "\n    ")}{"\n</head>"}</pre></div>
            </div>
          </>}
          <div className="mt-6 border-t border-slate-800 pt-5">
            <h3 className="font-semibold text-white">I do not manage my website</h3><p className="mt-1 text-sm text-slate-400">Send this request to your website developer.</p>
            <div className="mt-3 flex flex-col gap-3 sm:flex-row"><p className="flex-1 border border-slate-800 bg-slate-950 p-3 text-sm text-slate-300">Please add the WebIntelX SDK snippet to the global &lt;head&gt; section of the website and publish the changes.</p><button type="button" onClick={() => copyText("Please add the WebIntelX SDK snippet to the global <head> section of the website and publish the changes.", "Developer message copied")} className={secondaryClass}><Copy className="h-4 w-4" /> Copy message</button></div>
          </div>
          <p className="mt-5 text-xs text-slate-500">Customer Website → SDK → WebIntelX Backend → WebIntelX Portal</p>
          <div className="mt-6 flex gap-3"><button type="button" onClick={() => persistStep(1)} className={secondaryClass}><ArrowLeft className="h-4 w-4" /> Back</button><button type="button" disabled={!installCode} onClick={() => persistStep(3)} className={buttonClass}>Continue to verification <ArrowRight className="h-4 w-4" /></button></div>
        </section>}

        {activeStep === 3 && <section className="max-w-3xl border-t border-slate-800 py-7">
          <p className="text-xs uppercase tracking-widest text-cyan-300">Step 5</p><h2 className="mt-2 text-2xl font-semibold text-white">Verify your website</h2>
          <p className="mt-3 text-sm text-slate-300">Install the SDK on your registered website, open it in another browser tab, and browse for a few seconds. Then return here and check for real telemetry.</p>
          <p className="mt-3 text-sm text-slate-300">Registered website: <a href={website.origin ?? undefined} target="_blank" rel="noopener noreferrer" className="text-cyan-300 underline">{website.origin ?? website.domain}</a></p>
          <div className="mt-6 space-y-2">
            {["Checking SDK...", "Checking telemetry...", "Checking ingestion..."].map((item) => <div key={item} className="flex items-center gap-3 border border-slate-800 bg-slate-950 px-4 py-3 text-sm text-slate-300">{telemetryQuery.isFetching ? <LoaderCircle className="h-4 w-4 animate-spin text-cyan-300" /> : connected ? <CheckCircle2 className="h-4 w-4 text-emerald-300" /> : <span className="h-4 w-4 rounded-full border border-slate-700" />}{item}</div>)}
          </div>
          {telemetryQuery.error ? <div role="alert" className="mt-5 border border-red-800/60 bg-red-950/30 p-4 text-sm text-red-200"><p className="font-semibold">Connection could not be verified.</p><p className="mt-1">{telemetryQuery.error.message}</p><p className="mt-3">Check the SDK installation, connection key, API endpoint, registered website origin, backend availability, and browser console errors.</p></div> : connected && telemetry?.last_event ? <div className="mt-5 border border-emerald-700/50 bg-emerald-950/20 p-5">
            <h3 className="flex items-center gap-2 font-semibold text-emerald-200"><ShieldCheck className="h-5 w-5" /> Website connected</h3>
            <p className="mt-3 text-sm text-slate-300">Events received: <strong className="text-white">{telemetry.event_count}</strong></p>
            <p className="mt-1 text-sm text-slate-300">Last event: <strong className="text-white">{telemetry.last_event?.event_type}</strong></p>
            <p className="mt-1 text-sm text-slate-300">Last received: <strong className="text-white">{new Date(telemetry.last_event.created_at).toLocaleString()}</strong></p>
            <p className="mt-1 text-sm text-slate-300">Connection key: <strong className="text-white">{activeCredential?.status === "active" ? "Active" : "Not active"}</strong></p>
          </div> : <div className="mt-5 border border-amber-700/50 bg-amber-950/20 p-4 text-sm text-amber-100"><p className="font-medium">We have not received telemetry yet.</p><p className="mt-1">Make sure the SDK is installed on this registered website, then open it and click Check Again.</p></div>}
          <div className="mt-6 flex flex-wrap gap-3"><button type="button" onClick={() => persistStep(2)} className={secondaryClass}><ArrowLeft className="h-4 w-4" /> Back to install</button><button type="button" onClick={verify} disabled={telemetryQuery.isFetching} className={buttonClass}>{telemetryQuery.isFetching && <LoaderCircle className="h-4 w-4 animate-spin" />}{telemetryQuery.isFetching ? "Checking..." : "Check Again"}</button>{website.origin && <a href={`${website.origin}/`} target="_blank" rel="noopener noreferrer" className={secondaryClass}>Open Website</a>}{connected && <Link href="/dashboard" className={buttonClass}>Open Security Dashboard <ArrowRight className="h-4 w-4" /></Link>}</div>
          {connected && <div className="mt-7 border-t border-slate-800 pt-5"><h3 className="text-lg font-semibold text-white">Your website is connected</h3><ul className="mt-3 grid gap-2 text-sm text-emerald-200 sm:grid-cols-2">{["✓ SDK detected", "✓ Telemetry received", "✓ Ingestion working"].map((item) => <li key={item}>{item}</li>)}</ul><p className="mt-4 text-sm text-slate-300">Website: <strong className="text-white">{website.origin ?? website.domain}</strong></p></div>}
        </section>}
      </div>
    </AppShell>
  );
}

"use client";

import { useEffect, useState, useRef } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  Github, RefreshCw, ExternalLink, CheckCircle,
  Clock, AlertCircle, Zap, LogOut, FileText,
} from "lucide-react";
import axios from "axios";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type BuildStatus = "idle" | "pending" | "running" | "completed" | "failed";

interface User {
  id: string;
  github_id: number | null;
  github_username: string;
  name: string;
  avatar_url: string;
  plan: string;
}

interface Portfolio {
  site_url: string;
  is_published: boolean;
  theme: string;
  last_built_at: string;
  portfolio_data: Record<string, unknown>;
}

interface Repo {
  full_name: string;
  name: string;
  description: string;
  language: string;
  stars: number;
}

interface Subscription {
  tier: string;
  status: string | null;
  renewal_date: string | null;
  next_invoice_date: string | null;
  cancel_at_period_end?: boolean;
}

const THEMES = [
  { id: "minimal", label: "Minimal", desc: "Clean & professional" },
  { id: "dark", label: "Dark", desc: "Dark mode first" },
  { id: "creative", label: "Creative", desc: "Bold & expressive" },
];

export default function DashboardPage() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [repos, setRepos] = useState<Repo[]>([]);
  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [selectedRepos, setSelectedRepos] = useState<string[]>([]);
  const [selectedTheme, setSelectedTheme] = useState("minimal");
  const [resumeFile, setResumeFile] = useState<File | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [buildStatus, setBuildStatus] = useState<BuildStatus>("idle");
  const [buildSteps, setBuildSteps] = useState<string[]>([]);
  const [buildError, setBuildError] = useState<string | null>(null);
  const [siteUrl, setSiteUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [showCancelConfirm, setShowCancelConfirm] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    const paramToken = searchParams.get("token");
    const stored = localStorage.getItem("portfolioai_token");
    const activeToken = paramToken || stored;

    if (!activeToken) { router.push("/"); return; }

    if (paramToken) {
      localStorage.setItem("portfolioai_token", decodeURIComponent(paramToken));
      router.replace("/dashboard");
    }
    setToken(activeToken);
  }, [router, searchParams]);

  useEffect(() => {
    if (!token) return;
    const headers = { Authorization: `Bearer ${token}` };

    Promise.all([
      axios.get(`${API}/api/auth/me`, { headers }).catch(e => ({ data: null })),
      axios.get(`${API}/api/billing/subscription`, { headers }).catch(e => ({ data: { tier: "free", status: "active" } })),
    ])
      .then(([userRes, subRes]) => {
        setUser(userRes.data || {});
        setSubscription(subRes.data || { tier: "free", status: "active" });
        setRepos([]);  // Repos fetching is optional
      })
      .catch(() => { localStorage.removeItem("portfolioai_token"); router.push("/"); })
      .finally(() => setLoading(false));
  }, [token]);

  const triggerBuild = async () => {
    if (!token) return;
    setBuildStatus("pending");
    setBuildSteps([]);
    setBuildError(null);
    setSiteUrl(null);

    const formData = new FormData();
    formData.append("theme", selectedTheme);
    if (selectedRepos.length > 0) {
      formData.append("selected_repos", JSON.stringify(selectedRepos));
    }
    if (resumeFile) formData.append("resume", resumeFile);

    try {
      const res = await axios.post(`${API}/api/portfolio/build`, formData, {
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "multipart/form-data" },
      });
      const newJobId = res.data.job_id;
      setJobId(newJobId);
      startSSEStream(newJobId);
    } catch (err: any) {
      setBuildStatus("failed");
      setBuildError(err?.response?.data?.detail || "Failed to start build. Please try again.");
    }
  };

  const startSSEStream = (id: string) => {
    if (eventSourceRef.current) eventSourceRef.current.close();

    const es = new EventSource(`${API}/api/portfolio/build/${id}/stream`);
    eventSourceRef.current = es;

    es.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setBuildStatus(data.status);
      if (data.steps) setBuildSteps(data.steps);
      if (data.result?.site_url) setSiteUrl(data.result.site_url);
      if (data.error) setBuildError(data.error);
      if (data.status === "completed" || data.status === "failed") es.close();
    };

    es.onerror = () => {
      setBuildStatus("failed");
      setBuildError("Connection lost. Check job status manually.");
      es.close();
    };
  };

  const toggleRepo = (fullName: string) => {
    setSelectedRepos((prev) =>
      prev.includes(fullName) ? prev.filter((r) => r !== fullName) : [...prev, fullName]
    );
  };

  const handleCancelSubscription = async () => {
    if (!token) return;
    try {
      await axios.post(
        `${API}/api/billing/cancel?at_period_end=true`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      const res = await axios.get(`${API}/api/billing/subscription`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setSubscription(res.data);
      setShowCancelConfirm(false);
    } catch {
      window.alert("Failed to cancel subscription. Please try again.");
    }
  };

  const logout = () => {
    localStorage.removeItem("portfolioai_token");
    router.push("/");
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
          <p className="text-sm text-gray-500">Loading your dashboard…</p>
        </div>
      </div>
    );
  }

  const isBuilding = buildStatus === "pending" || buildStatus === "running";

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-100 sticky top-0 z-40">
        <div className="max-w-5xl mx-auto px-6 h-14 flex items-center justify-between">
          <span className="font-bold text-gray-900">
            Portfolio<span className="text-blue-600">AI</span>
          </span>
          <div className="flex items-center gap-4">
            <span className="text-xs bg-blue-50 text-blue-700 px-2.5 py-1 rounded-full font-medium capitalize">
              {subscription?.tier || user?.plan} plan
            </span>
            {user?.avatar_url && (
              <img src={user.avatar_url} alt="" className="w-8 h-8 rounded-full" />
            )}
            <button onClick={logout} className="text-gray-400 hover:text-gray-600 transition-colors">
              <LogOut size={16} />
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-10">
        <div className="mb-10">
          <h1 className="text-2xl font-bold text-gray-900 mb-1">
            Hey, {user?.name?.split(" ")[0] || user?.github_username} 👋
          </h1>
          <p className="text-gray-500 text-sm">
            {portfolio
              ? "Your portfolio is live. Rebuild anytime."
              : "Let's build your portfolio in the next 2 minutes."}
          </p>
        </div>

        {/* GitHub Connection Status */}
        {user && !user.github_id && (
          <div className="mb-8 bg-blue-50 border border-blue-200 rounded-2xl p-4 flex items-start gap-3">
            <Github size={20} className="text-blue-600 mt-0.5 flex-shrink-0" />
            <div className="flex-1 min-w-0">
              <h3 className="font-semibold text-blue-900">Connect GitHub to build your portfolio</h3>
              <p className="text-sm text-blue-800 mt-1">
                Link your GitHub account to fetch your repos and build an amazing portfolio automatically.
              </p>
              <a
                href={`https://github.com/login/oauth/authorize?client_id=${process.env.NEXT_PUBLIC_GITHUB_CLIENT_ID}&scope=user:email,read:user&redirect_uri=${encodeURIComponent(`${typeof window !== "undefined" ? window.location.origin : process.env.NEXT_PUBLIC_APP_URL}/api/auth/callback`)}`}
                className="inline-flex items-center gap-2 mt-3 bg-blue-600 text-white font-medium py-2 px-4 rounded-lg hover:bg-blue-700 transition-colors text-sm"
              >
                <Github size={16} />
                Connect GitHub
              </a>
            </div>
          </div>
        )}

        <div className="grid lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2 space-y-6">
            <div className="bg-white rounded-2xl border border-gray-100 p-6">
              <h2 className="font-semibold text-gray-900 mb-4">Choose a theme</h2>
              <div className="grid grid-cols-3 gap-3">
                {THEMES.map((t) => (
                  <button
                    key={t.id}
                    onClick={() => setSelectedTheme(t.id)}
                    className={`p-4 rounded-xl border-2 text-left transition-all ${
                      selectedTheme === t.id
                        ? "border-blue-500 bg-blue-50"
                        : "border-gray-100 hover:border-gray-200"
                    }`}
                  >
                    <p className="font-medium text-sm text-gray-900">{t.label}</p>
                    <p className="text-xs text-gray-500 mt-0.5">{t.desc}</p>
                  </button>
                ))}
              </div>
            </div>

            <div className="bg-white rounded-2xl border border-gray-100 p-6">
              <h2 className="font-semibold text-gray-900 mb-1">Upload resume</h2>
              <p className="text-xs text-gray-400 mb-4">PDF, JSON, or TXT · Helps AI write a better bio</p>
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.json,.txt"
                className="hidden"
                onChange={(e) => setResumeFile(e.target.files?.[0] || null)}
              />
              <button
                onClick={() => fileInputRef.current?.click()}
                className="flex items-center gap-2 border-2 border-dashed border-gray-200 rounded-xl px-4 py-3 text-sm text-gray-500 hover:border-blue-300 hover:text-blue-600 transition-all w-full justify-center"
              >
                <FileText size={16} />
                {resumeFile ? resumeFile.name : "Click to upload resume"}
              </button>
            </div>

            <div className="bg-white rounded-2xl border border-gray-100 p-6">
              <h2 className="font-semibold text-gray-900 mb-1">Pin specific repos</h2>
              <p className="text-xs text-gray-400 mb-4">Optional — AI picks the best ones by default</p>
              <div className="space-y-2 max-h-64 overflow-y-auto pr-1">
                {repos.map((repo) => (
                  <label
                    key={repo.full_name}
                    className="flex items-center gap-3 p-3 rounded-lg hover:bg-gray-50 cursor-pointer"
                  >
                    <input
                      type="checkbox"
                      checked={selectedRepos.includes(repo.full_name)}
                      onChange={() => toggleRepo(repo.full_name)}
                      className="rounded accent-blue-600"
                    />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 truncate">{repo.name}</p>
                      {repo.description && (
                        <p className="text-xs text-gray-400 truncate">{repo.description}</p>
                      )}
                    </div>
                    <div className="flex items-center gap-2 flex-shrink-0">
                      {repo.language && (
                        <span className="text-xs text-gray-400">{repo.language}</span>
                      )}
                      {repo.stars > 0 && (
                        <span className="text-xs text-yellow-500">★ {repo.stars}</span>
                      )}
                    </div>
                  </label>
                ))}
              </div>
            </div>

            <button
              onClick={triggerBuild}
              disabled={isBuilding}
              className="w-full flex items-center justify-center gap-2.5 bg-gray-900 text-white font-semibold py-4 rounded-xl hover:bg-gray-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed hover:-translate-y-0.5 active:translate-y-0"
            >
              {isBuilding ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  Building your portfolio…
                </>
              ) : portfolio ? (
                <>
                  <RefreshCw size={18} />
                  Rebuild portfolio
                </>
              ) : (
                <>
                  <Zap size={18} />
                  Build my portfolio
                </>
              )}
            </button>
          </div>

          <div className="space-y-6">
            {(isBuilding || buildStatus === "completed" || buildStatus === "failed") && (
              <div className="bg-white rounded-2xl border border-gray-100 p-6">
                <h2 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
                  {isBuilding && <div className="w-3 h-3 bg-blue-500 rounded-full animate-pulse" />}
                  {buildStatus === "completed" && <CheckCircle size={16} className="text-green-500" />}
                  {buildStatus === "failed" && <AlertCircle size={16} className="text-red-500" />}
                  Build progress
                </h2>
                <div className="space-y-1.5">
                  {buildSteps.map((step, i) => (
                    <div key={i} className="progress-step done">
                      <CheckCircle size={14} className="flex-shrink-0" />
                      {step}
                    </div>
                  ))}
                  {isBuilding && (
                    <div className="progress-step active">
                      <div className="w-3.5 h-3.5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin flex-shrink-0" />
                      Working…
                    </div>
                  )}
                  {buildError && (
                    <div className="progress-step" style={{ background: "#fef2f2", color: "#dc2626" }}>
                      <AlertCircle size={14} />
                      {buildError}
                    </div>
                  )}
                </div>
              </div>
            )}

            {(siteUrl || portfolio?.site_url) && (
              <div className="bg-gradient-to-br from-blue-600 to-blue-700 rounded-2xl p-6 text-white">
                <div className="flex items-center gap-2 mb-1">
                  <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
                  <p className="text-sm font-medium text-blue-100">Live</p>
                </div>
                <p className="font-semibold text-lg mb-4 break-all">
                  {(siteUrl || portfolio?.site_url)?.replace("https://", "")}
                </p>
                <a
                  href={siteUrl || portfolio?.site_url || "#"}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2 bg-white/20 hover:bg-white/30 transition-colors text-white text-sm font-medium px-4 py-2 rounded-lg w-fit"
                >
                  <ExternalLink size={14} />
                  View portfolio
                </a>
              </div>
            )}

            {subscription && (
              <div className={`rounded-2xl border p-6 ${
                subscription.tier === "free"
                  ? "bg-white border-gray-100"
                  : subscription.cancel_at_period_end
                  ? "bg-orange-50 border-orange-200"
                  : "bg-blue-50 border-blue-200"
              }`}>
                <h2 className="font-semibold text-gray-900 mb-3">Billing</h2>
                <p className="text-sm text-gray-600 mb-2">
                  Current plan: <span className="font-semibold capitalize">{subscription.tier}</span>
                </p>
                <p className="text-sm text-gray-600 mb-4">
                  Status: <span className="font-medium capitalize">{subscription.status || "free"}</span>
                </p>
                {subscription.renewal_date && (
                  <p className="text-sm text-gray-600 mb-4">
                    Renews on {new Date(subscription.renewal_date).toLocaleDateString()}
                  </p>
                )}
                {subscription.cancel_at_period_end && (
                  <div className="rounded-lg bg-orange-100 px-3 py-2 text-xs text-orange-700 mb-4">
                    Subscription will cancel at the end of the current billing period.
                  </div>
                )}
                <div className="space-y-2">
                  {subscription.tier === "free" ? (
                    <button
                      onClick={() => router.push("/pricing")}
                      className="w-full bg-blue-600 text-white font-semibold py-2 rounded-lg hover:bg-blue-500 transition-colors text-sm"
                    >
                      Upgrade plan
                    </button>
                  ) : (
                    <>
                      {!subscription.cancel_at_period_end && (
                        <button
                          onClick={() => router.push("/pricing")}
                          className="w-full bg-gray-900 text-white font-semibold py-2 rounded-lg hover:bg-gray-700 transition-colors text-sm"
                        >
                          Change plan
                        </button>
                      )}
                      {!subscription.cancel_at_period_end && (
                        <button
                          onClick={() => setShowCancelConfirm(true)}
                          className="w-full border border-gray-300 text-gray-700 font-semibold py-2 rounded-lg hover:bg-gray-50 transition-colors text-sm"
                        >
                          Cancel subscription
                        </button>
                      )}
                    </>
                  )}
                </div>
              </div>
            )}

            {user && (
              <div className="bg-white rounded-2xl border border-gray-100 p-6">
                <h2 className="font-semibold text-gray-900 mb-2 flex items-center gap-2">
                  <Github size={15} />
                  Auto-update webhook
                </h2>
                <p className="text-xs text-gray-500 mb-3">
                  Add this URL to your GitHub repo webhooks to enable auto-rebuild on push.
                </p>
                <code className="block text-xs bg-gray-50 border border-gray-100 rounded-lg p-3 break-all text-gray-700 select-all">
                  {API}/api/webhooks/github/{user.id}
                </code>
                <p className="text-xs text-gray-400 mt-2">
                  Settings → Webhooks → Add webhook · Content type: application/json
                </p>
              </div>
            )}

            {portfolio?.portfolio_data && (
              <div className="bg-white rounded-2xl border border-gray-100 p-6">
                <h2 className="font-semibold text-gray-900 mb-4">Portfolio stats</h2>
                <div className="grid grid-cols-2 gap-3">
                  <div className="bg-gray-50 rounded-xl p-3">
                    <p className="text-2xl font-bold text-gray-900">
                      {(portfolio.portfolio_data as any).projects_count || 0}
                    </p>
                    <p className="text-xs text-gray-500 mt-0.5">Projects</p>
                  </div>
                  <div className="bg-gray-50 rounded-xl p-3">
                    <p className="text-2xl font-bold text-gray-900">
                      {((portfolio.portfolio_data as any).skills?.languages?.length || 0) +
                        ((portfolio.portfolio_data as any).skills?.frameworks?.length || 0)}
                    </p>
                    <p className="text-xs text-gray-500 mt-0.5">Skills</p>
                  </div>
                </div>
                {portfolio.last_built_at && (
                  <p className="text-xs text-gray-400 mt-3 flex items-center gap-1">
                    <Clock size={11} />
                    Last built {new Date(portfolio.last_built_at).toLocaleDateString()}
                  </p>
                )}
              </div>
            )}
          </div>
        </div>
      </main>

      {showCancelConfirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 px-4">
          <div className="bg-white rounded-2xl p-6 max-w-sm w-full">
            <h3 className="text-xl font-bold text-gray-900 mb-2">Cancel subscription?</h3>
            <p className="text-gray-600 mb-4 text-sm">
              Your access will continue until the end of your billing period. You can resubscribe anytime.
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => setShowCancelConfirm(false)}
                className="flex-1 border border-gray-300 text-gray-700 font-semibold py-2 rounded-lg hover:bg-gray-50 transition-colors text-sm"
              >
                Keep subscription
              </button>
              <button
                onClick={handleCancelSubscription}
                className="flex-1 bg-red-600 text-white font-semibold py-2 rounded-lg hover:bg-red-500 transition-colors text-sm"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

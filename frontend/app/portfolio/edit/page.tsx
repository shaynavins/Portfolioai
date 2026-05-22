"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  ArrowLeft, Save, Eye, EyeOff, Sparkles, AlertCircle, CheckCircle,
} from "lucide-react";
import axios from "axios";
import { buildApiUrl } from "@/lib/config";

const API = buildApiUrl("");

interface Portfolio {
  id: string;
  site_url: string;
  is_published: boolean;
  theme: string;
  portfolio_data: Record<string, unknown>;
}

interface Subscription {
  tier: string;
}

export default function EditPortfolioPage() {
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [showPreview, setShowPreview] = useState(true);
  const [editPrompt, setEditPrompt] = useState("");
  const [successMessage, setSuccessMessage] = useState("");
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    const storedToken = localStorage.getItem("portfolioai_token");
    if (!storedToken) {
      router.push("/");
      return;
    }
    setToken(storedToken);
  }, [router]);

  useEffect(() => {
    if (!token) return;

    const headers = { Authorization: `Bearer ${token}` };

    Promise.all([
      axios.get(`${API}/api/portfolio/me`, { headers }).catch(() => ({ data: null })),
      axios.get(`${API}/api/billing/subscription`, { headers }).catch(() => ({ data: { tier: "free" } })),
    ])
      .then(([portfolioRes, subRes]) => {
        if (!portfolioRes.data?.portfolio) {
          router.push("/dashboard");
          return;
        }
        setPortfolio(portfolioRes.data.portfolio);
        setSubscription(subRes.data || { tier: "free" });
      })
      .catch(() => router.push("/dashboard"))
      .finally(() => setLoading(false));
  }, [token, router]);

  const handleSaveChanges = async () => {
    if (!token || !portfolio || !editPrompt.trim()) return;

    setSaving(true);
    setErrorMessage("");
    setSuccessMessage("");

    try {
      const formData = new FormData();
      formData.append("theme", portfolio.theme || "minimal");
      formData.append("user_prompt", editPrompt.trim());

      const res = await axios.post(`${API}/api/portfolio/build`, formData, {
        headers: { Authorization: `Bearer ${token}` },
      });

      setSuccessMessage("Portfolio updated successfully! Regenerating...");
      setEditPrompt("");
      
      // Reload portfolio data
      const portfolioRes = await axios.get(`${API}/api/portfolio/me`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setPortfolio(portfolioRes.data.portfolio);
    } catch (err: any) {
      setErrorMessage(
        err?.response?.data?.detail || 
        err?.response?.data?.message || 
        "Failed to update portfolio"
      );
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
          <p className="text-sm text-gray-500">Loading portfolio…</p>
        </div>
      </div>
    );
  }

  if (subscription?.tier === "free") {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl p-8 max-w-md w-full text-center">
          <AlertCircle size={48} className="mx-auto text-orange-500 mb-4" />
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Upgrade Required</h1>
          <p className="text-gray-600 mb-6">
            Editing and modifying portfolios is a premium feature. Upgrade to unlock unlimited edits.
          </p>
          <div className="space-y-2">
            <button
              onClick={() => router.push("/pricing")}
              className="w-full bg-blue-600 text-white font-semibold py-3 rounded-lg hover:bg-blue-700 transition-colors"
            >
              Upgrade to Pro
            </button>
            <button
              onClick={() => router.push("/dashboard")}
              className="w-full border border-gray-300 text-gray-700 font-semibold py-3 rounded-lg hover:bg-gray-50 transition-colors"
            >
              Back to Dashboard
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-100">
        <div className="max-w-7xl mx-auto px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={() => router.push("/dashboard")}
              className="text-gray-400 hover:text-gray-600 transition-colors"
            >
              <ArrowLeft size={20} />
            </button>
            <h1 className="text-xl font-bold text-gray-900">Edit Portfolio</h1>
          </div>
          <button
            onClick={() => setShowPreview(!showPreview)}
            className="flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900 transition-colors"
          >
            {showPreview ? (
              <>
                <EyeOff size={16} />
                Hide preview
              </>
            ) : (
              <>
                <Eye size={16} />
                Show preview
              </>
            )}
          </button>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-12">
        <div className="grid lg:grid-cols-2 gap-8">
          {/* Edit Section */}
          <div className="space-y-6">
            <div className="bg-white rounded-2xl border border-gray-100 p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                <Sparkles size={20} className="text-blue-500" />
                How should we change it?
              </h2>
              <p className="text-sm text-gray-500 mb-4">
                Describe the changes you'd like to see. Be specific about what to modify, remove, or add.
              </p>
              <textarea
                value={editPrompt}
                onChange={(e) => setEditPrompt(e.target.value)}
                placeholder="E.g., 'Make the design darker with a purple accent. Highlight my AI/ML projects more. Add a testimonials section. Remove the blog section.'"
                rows={6}
                className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm text-gray-700 placeholder-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
              />
            </div>

            {/* Suggestions */}
            <div className="bg-blue-50 border border-blue-200 rounded-2xl p-6">
              <h3 className="font-semibold text-blue-900 mb-3">💡 AI Suggestions</h3>
              <ul className="space-y-2 text-sm text-blue-800">
                <li className="flex items-start gap-2">
                  <span className="text-blue-600 font-bold">•</span>
                  Highlight your most impactful projects
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-blue-600 font-bold">•</span>
                  Add a call-to-action button (Contact me, Hire me, etc)
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-blue-600 font-bold">•</span>
                  Include social media links and contact information
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-blue-600 font-bold">•</span>
                  Reorganize sections to match your brand
                </li>
              </ul>
            </div>

            {/* Status Messages */}
            {successMessage && (
              <div className="bg-green-50 border border-green-200 rounded-xl p-4 flex items-start gap-3">
                <CheckCircle size={20} className="text-green-600 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="font-semibold text-green-900 text-sm">{successMessage}</p>
                </div>
              </div>
            )}

            {errorMessage && (
              <div className="bg-red-50 border border-red-200 rounded-xl p-4 flex items-start gap-3">
                <AlertCircle size={20} className="text-red-600 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="font-semibold text-red-900 text-sm">{errorMessage}</p>
                </div>
              </div>
            )}

            {/* Action Buttons */}
            <div className="flex gap-3">
              <button
                onClick={() => router.push("/dashboard")}
                className="flex-1 border border-gray-300 text-gray-700 font-semibold py-3 rounded-lg hover:bg-gray-50 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveChanges}
                disabled={!editPrompt.trim() || saving}
                className="flex-1 bg-blue-600 text-white font-semibold py-3 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
              >
                {saving ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    Updating…
                  </>
                ) : (
                  <>
                    <Save size={18} />
                    Apply Changes
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Preview Section */}
          {showPreview && portfolio && (
            <div className="sticky top-6 h-fit">
              <div className="bg-white rounded-2xl border border-gray-100 p-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">Live Preview</h2>
                <div className="bg-gray-100 rounded-xl overflow-hidden border border-gray-200">
                  {portfolio.site_url ? (
                    <iframe
                      src={portfolio.site_url}
                      title="Portfolio Preview"
                      className="w-full h-96 border-none"
                    />
                  ) : (
                    <div className="w-full h-96 flex items-center justify-center bg-gray-100">
                      <p className="text-gray-500 text-sm">Portfolio not published yet</p>
                    </div>
                  )}
                </div>
                {portfolio.site_url && (
                  <a
                    href={portfolio.site_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="mt-4 block w-full text-center bg-gray-900 text-white font-semibold py-2 rounded-lg hover:bg-gray-700 transition-colors text-sm"
                  >
                    Open in new tab
                  </a>
                )}
              </div>

              {/* Portfolio Info */}
              <div className="mt-6 bg-white rounded-2xl border border-gray-100 p-6">
                <h3 className="font-semibold text-gray-900 mb-4">Portfolio Details</h3>
                <div className="space-y-3">
                  <div>
                    <p className="text-xs text-gray-500 mb-1">Theme</p>
                    <p className="text-sm font-medium text-gray-900 capitalize">{portfolio.theme || "minimal"}</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500 mb-1">Status</p>
                    <div className="flex items-center gap-2">
                      <div
                        className={`w-2 h-2 rounded-full ${
                          portfolio.is_published ? "bg-green-500" : "bg-amber-500"
                        }`}
                      />
                      <p className="text-sm font-medium text-gray-900">
                        {portfolio.is_published ? "Published" : "Draft"}
                      </p>
                    </div>
                  </div>
                  {portfolio.site_url && (
                    <div>
                      <p className="text-xs text-gray-500 mb-1">Live URL</p>
                      <p className="text-sm font-medium text-blue-600 break-all truncate">
                        {portfolio.site_url}
                      </p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

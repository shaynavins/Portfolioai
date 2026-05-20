"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

const PLAN_DETAILS: Record<"pro" | "team", { name: string; price: number; features: string[] }> = {
  pro: {
    name: "Pro",
    price: 9,
    features: [
      "Unlimited portfolios",
      "Custom domain",
      "50 builds per month",
      "All themes",
      "Priority support",
    ],
  },
  team: {
    name: "Team",
    price: 29,
    features: [
      "Everything in Pro",
      "Team member portfolios",
      "API access",
      "Unlimited builds",
      "Advanced analytics",
    ],
  },
};

export default function CheckoutPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tier, setTier] = useState<"pro" | "team" | null>(null);

  useEffect(() => {
    const tierparam = searchParams.get("tier");
    if (!tierparam || !["pro", "team"].includes(tierparam)) {
      setError("Invalid plan selected");
      setLoading(false);
      return;
    }

    setTier(tierparam as "pro" | "team");
    initializeCheckout(tierparam as "pro" | "team");
  }, [searchParams]);

  const initializeCheckout = async (selectedTier: "pro" | "team") => {
    try {
      const token = localStorage.getItem("portfolioai_token");
      if (!token) {
        setError("Not authenticated. Please log in first.");
        setLoading(false);
        setTimeout(() => router.push("/"), 2000);
        return;
      }

      const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const res = await fetch(`${API}/api/billing/checkout?tier=${selectedTier}`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "Failed to create checkout session");
      }

      const data = await res.json();
      if (data.checkout_url) {
        window.location.href = data.checkout_url;
      } else {
        throw new Error("No checkout URL returned");
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "An error occurred";
      setError(message);
      setLoading(false);
    }
  };

  if (error) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center px-6">
        <div className="max-w-md text-center">
          <h1 className="text-2xl font-bold text-gray-900 mb-4">Something went wrong</h1>
          <p className="text-gray-500 mb-6">{error}</p>
          <div className="space-y-3">
            <button
              onClick={() => router.push("/pricing")}
              className="w-full bg-gray-900 text-white font-semibold py-3 rounded-xl hover:bg-gray-700 transition-colors"
            >
              Back to pricing
            </button>
            <button
              onClick={() => router.push("/dashboard")}
              className="w-full bg-gray-100 text-gray-900 font-semibold py-3 rounded-xl hover:bg-gray-200 transition-colors"
            >
              Go to dashboard
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-white flex flex-col items-center justify-center px-6">
      <div className="max-w-md text-center">
        <div className="mb-6 flex justify-center">
          <div className="w-12 h-12 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
        </div>
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          Upgrading to {tier?.charAt(0).toUpperCase() + tier?.slice(1)}
        </h1>
        <p className="text-gray-500 mb-8">
          Setting up your secure payment. You'll be redirected to Stripe Checkout in a moment.
        </p>

        {tier && PLAN_DETAILS[tier] && (
          <div className="bg-gray-50 rounded-xl p-6 text-left mb-6">
            <p className="text-sm text-gray-500 mb-2">Order Summary</p>
            <div className="flex justify-between items-baseline mb-4">
              <span className="text-xl font-bold text-gray-900">
                {PLAN_DETAILS[tier].name} Plan
              </span>
              <span className="text-2xl font-bold text-gray-900">
                ${PLAN_DETAILS[tier].price}<span className="text-sm text-gray-500">/mo</span>
              </span>
            </div>
            <ul className="space-y-2 text-sm text-gray-600 border-t pt-4">
              {PLAN_DETAILS[tier].features.map((f) => (
                <li key={f}>✓ {f}</li>
              ))}
            </ul>
          </div>
        )}

        <p className="text-xs text-gray-400 mb-6">
          Your payment information is secure and processed by Stripe
        </p>

        <button
          onClick={() => router.push("/pricing")}
          className="text-gray-500 hover:text-gray-700 text-sm font-medium transition-colors"
        >
          ← Back to pricing
        </button>
      </div>
    </div>
  );
}

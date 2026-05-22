"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import RazorpayCheckout from "@/components/RazorpayCheckout";

const PLAN_DETAILS: Record<"pro", { name: string; price: number; features: string[] }> = {
  pro: {
    name: "Pro",
    price: 199,
    features: [
      "Unlimited portfolios",
      "Custom domain",
      "50 builds per month",
      "All themes",
      "Priority support",
    ],
  },
};

function CheckoutPageInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [error, setError] = useState<string | null>(null);
  const [plan, setPlan] = useState<"pro" | null>(null);

  useEffect(() => {
    const planParam = searchParams.get("plan");
    if (!planParam || planParam !== "pro") {
      setError("Invalid plan selected");
      return;
    }

    const token = localStorage.getItem("portfolioai_token");
    if (!token) {
      setError("Not authenticated. Please log in first.");
      return;
    }

    setPlan("pro");
  }, [searchParams]);

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
      {plan && (
        <RazorpayCheckout
          plan={plan}
          onSuccess={() => router.push("/dashboard?upgraded=1")}
          onClose={() => router.push("/pricing")}
        />
      )}
      <div className="max-w-md text-center">
        <div className="mb-6 flex justify-center">
          <div className="w-12 h-12 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
        </div>
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          Completing your upgrade
        </h1>
        <p className="text-gray-500 mb-8">
          Setting up your secure Razorpay payment window.
        </p>

        {plan && PLAN_DETAILS[plan] && (
          <div className="bg-gray-50 rounded-xl p-6 text-left mb-6">
            <p className="text-sm text-gray-500 mb-2">Order Summary</p>
            <div className="flex justify-between items-baseline mb-4">
              <span className="text-xl font-bold text-gray-900">
                {PLAN_DETAILS[plan].name} Plan
              </span>
              <span className="text-2xl font-bold text-gray-900">
                ₹199<span className="text-sm text-gray-500"> one-time</span>
              </span>
            </div>
            <ul className="space-y-2 text-sm text-gray-600 border-t pt-4">
              {PLAN_DETAILS[plan].features.map((f) => (
                <li key={f}>✓ {f}</li>
              ))}
            </ul>
          </div>
        )}

        <p className="text-xs text-gray-400 mb-6">
          Your payment information is secure and processed by Razorpay.
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

export default function CheckoutPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-white flex flex-col items-center justify-center px-6">
          <div className="max-w-md text-center">
            <div className="mb-6 flex justify-center">
              <div className="w-12 h-12 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
            </div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">Loading checkout</h1>
            <p className="text-gray-500">Preparing your payment flow.</p>
          </div>
        </div>
      }
    >
      <CheckoutPageInner />
    </Suspense>
  );
}

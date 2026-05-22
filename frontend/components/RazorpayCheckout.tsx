"use client";

import { useState, useEffect } from "react";
import { getAuthToken } from "@/lib/auth";
import { buildApiUrl } from "@/lib/config";
import { Loader2 } from "lucide-react";

interface RazorpayCheckoutProps {
  plan: "pro" | "team";
  onSuccess: () => void;
  onClose: () => void;
}

declare global {
  interface Window {
    Razorpay: any;
  }
}

const PLAN_DETAILS = {
  pro: {
    name: "Pro Unlimited",
    amount: 19900, // 199 INR in paise
    currency: "INR",
    description: "Lifetime access to unlimited portfolios, editing, and publishing",
  },
};

export default function RazorpayCheckout({
  plan,
  onSuccess,
  onClose,
}: RazorpayCheckoutProps) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    initializeCheckout();
  }, []);

  const initializeCheckout = async () => {
    try {
      const token = getAuthToken();
      if (!token) {
        setError("Authentication required");
        return;
      }

      // Load Razorpay script
      if (!window.Razorpay) {
        const script = document.createElement("script");
        script.src = "https://checkout.razorpay.com/v1/checkout.js";
        script.async = true;
        script.onload = () => createOrder(token);
        script.onerror = () => setError("Failed to load Razorpay");
        document.body.appendChild(script);
      } else {
        createOrder(token);
      }
    } catch (err) {
      setError("Failed to initialize checkout");
      console.error(err);
    }
  };

  const createOrder = async (token: string) => {
    try {
      const res = await fetch(buildApiUrl("/api/billing/checkout"), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ plan }),
      });

      if (!res.ok) {
        throw new Error("Failed to create order");
      }

      const data = await res.json();
      openRazorpayCheckout(data, token);
    } catch (err) {
      setError("Failed to create payment order");
      console.error(err);
    }
  };

  const openRazorpayCheckout = async (
    orderData: any,
    token: string
  ) => {
    const options = {
      key: orderData.key_id,
      amount: orderData.amount,
      currency: orderData.currency,
      name: "PortfolioAI",
      description: PLAN_DETAILS[plan].description,
      order_id: orderData.order_id,
      prefill: {
        email: orderData.user_email,
        name: orderData.user_name,
      },
      handler: async (response: any) => {
        // Verify payment on backend
        await verifyPayment(
          response.razorpay_order_id,
          response.razorpay_payment_id,
          response.razorpay_signature,
          token
        );
      },
      modal: {
        ondismiss: () => {
          onClose();
        },
      },
    };

    const rzp = new window.Razorpay(options);
    setLoading(false);
    rzp.open();
  };

  const verifyPayment = async (
    orderId: string,
    paymentId: string,
    signature: string,
    token: string
  ) => {
    try {
      const res = await fetch(buildApiUrl("/api/billing/verify-payment"), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          razorpay_order_id: orderId,
          razorpay_payment_id: paymentId,
          razorpay_signature: signature,
          plan,
        }),
      });

      if (res.ok) {
        alert("Payment successful! Your subscription is now active.");
        onSuccess();
        onClose();
      } else {
        setError("Payment verification failed");
      }
    } catch (err) {
      setError("Failed to verify payment");
      console.error(err);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-slate-800 border border-slate-700 rounded-xl max-w-md w-full p-6">
        {loading ? (
          <div className="flex flex-col items-center justify-center py-8">
            <Loader2 className="animate-spin text-blue-400 mb-4" size={32} />
            <p className="text-slate-300">Loading checkout...</p>
          </div>
        ) : error ? (
          <div className="space-y-4">
            <div className="bg-red-900/20 border border-red-700 rounded-lg p-4">
              <p className="text-red-300">{error}</p>
            </div>
            <button
              onClick={onClose}
              className="w-full px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg font-semibold"
            >
              Close
            </button>
          </div>
        ) : (
          <div className="text-center text-slate-300">
            <p>Razorpay checkout is loading...</p>
          </div>
        )}
      </div>
    </div>
  );
}

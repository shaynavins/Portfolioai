"use client";

import { useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function GitHubCallbackPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const code = searchParams.get("code");
  const error = searchParams.get("error");

  useEffect(() => {
    if (error) {
      console.error("GitHub OAuth error:", error);
      router.push(`/auth?error=${encodeURIComponent(error)}`);
      return;
    }

    if (!code) {
      console.error("No authorization code received");
      router.push("/auth?error=no_code");
      return;
    }

    const exchangeCode = async () => {
      try {
        const res = await fetch(`${API}/api/auth/github/callback?code=${encodeURIComponent(code)}`, {
          method: "GET",
        });

        if (!res.ok) {
          const err = await res.json();
          throw new Error(err.detail || "Failed to authenticate with GitHub");
        }

        const data = await res.json();
        localStorage.setItem("portfolioai_token", data.access_token);
        // Use the redirect_to URL from the backend response
        window.location.href = data.redirect_to || "/dashboard";
      } catch (err) {
        console.error("Error exchanging code:", err);
        window.location.href = `/auth?error=${encodeURIComponent(err instanceof Error ? err.message : "Unknown error")}`;
      }
    };

    exchangeCode();
  }, [code, error, router]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-600 to-cyan-600 flex items-center justify-center">
      <div className="bg-white rounded-2xl shadow-2xl p-8 max-w-sm w-full mx-6">
        <div className="flex flex-col items-center gap-4">
          <div className="w-10 h-10 border-3 border-blue-600 border-t-transparent rounded-full animate-spin" />
          <h2 className="text-lg font-semibold text-gray-900">Connecting to GitHub...</h2>
          <p className="text-sm text-gray-500 text-center">Please wait while we authenticate your account.</p>
        </div>
      </div>
    </div>
  );
}

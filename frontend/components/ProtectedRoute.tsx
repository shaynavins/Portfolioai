"use client";

import { useEffect, ReactNode } from "react";
import { useRouter } from "next/navigation";
import { getAuthToken } from "@/lib/auth";
import { buildApiUrl } from "@/lib/config";

interface ProtectedRouteProps {
  children: ReactNode;
  requiredTier?: "free" | "pro" | "team";
}

export default function ProtectedRoute({
  children,
  requiredTier,
}: ProtectedRouteProps) {
  const router = useRouter();

  useEffect(() => {
    const token = getAuthToken();
    if (!token) {
      router.push("/login");
      return;
    }

    // If tier is required, verify subscription
    if (requiredTier && requiredTier !== "free") {
      checkSubscription();
    }
  }, []);

  const checkSubscription = async () => {
    try {
      const token = getAuthToken();
      const res = await fetch(buildApiUrl("/api/billing/subscription"), {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!res.ok) {
        router.push("/dashboard");
        return;
      }

      const data = await res.json();

      // Check if user has required tier
      if (
        requiredTier === "pro" &&
        data.tier !== "pro" &&
        data.tier !== "team"
      ) {
        router.push("/dashboard");
      } else if (requiredTier === "team" && data.tier !== "team") {
        router.push("/dashboard");
      }
    } catch (err) {
      console.error("Failed to check subscription:", err);
      router.push("/dashboard");
    }
  };

  return <>{children}</>;
}

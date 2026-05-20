"use client";

import { Check, ArrowRight, Zap } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState, useEffect } from "react";

export default function PricingPage() {
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    setIsMounted(true);
    setToken(localStorage.getItem("portfolioai_token"));
  }, []);

  const handleStartTrial = () => {
    if (!token) {
      router.push("/");
      return;
    }
    router.push("/checkout?tier=pro");
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-blue-50">
      {/* Navigation */}
      <nav className="fixed top-0 inset-x-0 z-50 bg-white/80 backdrop-blur-lg border-b border-slate-200">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <button
            onClick={() => router.push("/")}
            className="font-bold text-xl tracking-tight hover:opacity-70 transition"
          >
            Portfolio<span className="text-blue-600">AI</span>
          </button>
          <div className="flex items-center gap-4">
            {token ? (
              <button
                onClick={() => router.push("/dashboard")}
                className="text-sm text-slate-600 hover:text-slate-900 font-medium"
              >
                Dashboard
              </button>
            ) : (
              <button
                onClick={() => router.push("/")}
                className="text-sm text-slate-600 hover:text-slate-900 font-medium"
              >
                Sign In
              </button>
            )}
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="pt-32 pb-20 px-6">
        <div className="max-w-4xl mx-auto text-center">
          <div className="inline-block mb-6">
            <span className="bg-gradient-to-r from-blue-100 to-cyan-100 text-blue-700 px-4 py-2 rounded-full text-sm font-semibold">
              ✨ Now available in India
            </span>
          </div>

          <h1 className="text-5xl sm:text-6xl font-bold bg-gradient-to-r from-slate-900 via-slate-800 to-slate-900 bg-clip-text text-transparent mb-6">
            Build Your Perfect Portfolio
          </h1>

          <p className="text-xl text-slate-600 mb-2">
            One simple plan. Everything included. No surprises.
          </p>
          <p className="text-slate-500">
            Start free for 14 days — no credit card required
          </p>
        </div>
      </section>

      {/* Main Pricing Card */}
      <section className="px-6 py-20">
        <div className="max-w-2xl mx-auto">
          <div className="relative">
            {/* Glow effect */}
            <div className="absolute inset-0 bg-gradient-to-r from-blue-600/20 to-cyan-600/20 rounded-3xl blur-2xl -z-10"></div>

            {/* Card */}
            <div className="bg-white rounded-3xl border-2 border-blue-200 shadow-2xl overflow-hidden">
              <div className="p-12">
                {/* Badge */}
                <div className="flex items-center justify-center mb-6">
                  <div className="bg-gradient-to-r from-blue-600 to-cyan-600 text-white px-4 py-2 rounded-full text-sm font-bold flex items-center gap-2">
                    <Zap size={16} /> Most Powerful Plan
                  </div>
                </div>

                {/* Pricing */}
                <div className="text-center mb-8">
                  <div className="mb-2">
                    <span className="text-6xl font-bold text-slate-900">₹200</span>
                    <span className="text-xl text-slate-500 ml-2">/month</span>
                  </div>
                  <p className="text-slate-600 mb-4">
                    Everything you need to showcase your work
                  </p>
                  <div className="bg-green-50 border border-green-200 rounded-lg px-4 py-3 mb-6">
                    <p className="text-green-800 font-semibold text-sm">
                      🎉 14-day free trial — no credit card required
                    </p>
                    <p className="text-green-700 text-xs mt-1">
                      After trial, cancel anytime
                    </p>
                  </div>
                </div>

                {/* CTA Button */}
                {isMounted && (
                  <button
                    onClick={handleStartTrial}
                    className="w-full bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-700 hover:to-cyan-700 text-white font-bold py-4 px-6 rounded-xl mb-8 flex items-center justify-center gap-2 transition-all active:scale-95 shadow-lg"
                  >
                    Start Your Free Trial
                    <ArrowRight size={20} />
                  </button>
                )}

                {/* Features Grid */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {[
                    "Unlimited AI-generated portfolios",
                    "Custom domains",
                    "Real-time GitHub sync",
                    "All premium themes",
                    "Instant deployment",
                    "Advanced analytics",
                    "Email support",
                    "SEO optimization",
                    "Portfolio versioning",
                    "Custom CSS",
                    "Responsive design",
                    "Mobile-optimized",
                  ].map((feature, i) => (
                    <div key={i} className="flex items-start gap-3">
                      <div className="flex-shrink-0 mt-1">
                        <Check size={20} className="text-green-500" />
                      </div>
                      <span className="text-slate-700 font-medium">{feature}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Footer CTA */}
              <div className="bg-gradient-to-r from-blue-50 to-cyan-50 px-12 py-8 border-t border-blue-100">
                <p className="text-slate-600 text-center text-sm">
                  <span className="font-semibold">No credit card required.</span> Start building for free, upgrade anytime.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* FAQ Section */}
      <section className="px-6 py-20 bg-white/50 backdrop-blur-sm">
        <div className="max-w-3xl mx-auto">
          <h2 className="text-3xl font-bold text-center text-slate-900 mb-12">
            Questions?
          </h2>

          <div className="grid md:grid-cols-2 gap-8">
            {[
              {
                q: "Can I use it for free?",
                a: "Yes! You get a full 14-day free trial. No credit card required. After the trial, it's ₹200/month.",
              },
              {
                q: "Can I cancel anytime?",
                a: "Absolutely. Cancel your subscription anytime from your dashboard. No cancellation fees or contracts.",
              },
              {
                q: "What payment methods do you accept?",
                a: "We accept all major credit cards through Razorpay (UPI coming soon!).",
              },
              {
                q: "Do I own my portfolio?",
                a: "Yes! Your portfolio is yours. You can export it anytime or connect a custom domain.",
              },
              {
                q: "How many portfolios can I create?",
                a: "Unlimited! Create as many as you want. Perfect for showing different projects.",
              },
              {
                q: "Is there support?",
                a: "Yes! Email support is included. We respond within 24 hours.",
              },
            ].map((faq, i) => (
              <div key={i} className="bg-white rounded-xl p-6 border border-slate-200">
                <h3 className="font-bold text-slate-900 mb-2">{faq.q}</h3>
                <p className="text-slate-600 text-sm leading-relaxed">{faq.a}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Trust Section */}
      <section className="px-6 py-16 bg-slate-900 text-white text-center">
        <div className="max-w-2xl mx-auto">
          <h2 className="text-3xl font-bold mb-4">
            Trusted by developers worldwide
          </h2>
          <p className="text-slate-300 mb-8">
            Join thousands of developers building amazing portfolios with PortfolioAI
          </p>
          {isMounted && (
            <button
              onClick={handleStartTrial}
              className="inline-flex items-center gap-2 bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-700 hover:to-cyan-700 text-white font-bold px-8 py-3 rounded-xl transition-all active:scale-95"
            >
              Get Started Free
              <ArrowRight size={18} />
            </button>
          )}
        </div>
      </section>

      {/* Footer */}
      <footer className="px-6 py-8 border-t border-slate-200 text-center">
        <p className="text-sm text-slate-500">
          © 2025 PortfolioAI · Built for developers, by developers · 24/7 Support
        </p>
      </footer>
    </div>
  );
}

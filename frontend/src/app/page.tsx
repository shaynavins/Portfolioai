"use client";

import { useRouter } from "next/navigation";
import { Github, Zap, RefreshCw, Globe, ArrowRight, Star, Check } from "lucide-react";

const FEATURES = [
  {
    icon: Github,
    title: "Connect GitHub",
    desc: "OAuth in one click. We read your repos, READMEs, and commit history to understand your work.",
  },
  {
    icon: Zap,
    title: "AI Builds Your Site",
    desc: "A LangGraph agent analyzes your projects, writes your bio, selects the best work, and generates a stunning portfolio.",
  },
  {
    icon: RefreshCw,
    title: "Auto-Maintained",
    desc: "Push to GitHub and your portfolio updates automatically. Your site always reflects your latest work.",
  },
  {
    icon: Globe,
    title: "Instantly Deployed",
    desc: "Live at username.portfolioai.app in under 2 minutes. Custom domain on Pro.",
  },
];

const PLANS = [
  {
    name: "Free",
    price: "$0",
    period: "forever",
    features: [
      "1 portfolio site",
      "username.portfolioai.app",
      "Auto-update every 24h",
      "3 themes",
      "GitHub integration",
    ],
    cta: "Get started free",
    href: "/api/auth/github",
    accent: false,
  },
  {
    name: "Pro",
    price: "$9",
    period: "per month",
    features: [
      "Unlimited portfolios",
      "Custom domain",
      "Instant auto-updates",
      "All themes",
      "Resume upload",
      "Priority queue",
      "Analytics dashboard",
    ],
    cta: "Start Pro",
    href: "/pricing",
    accent: true,
  },
  {
    name: "Team",
    price: "$29",
    period: "per month",
    features: [
      "Everything in Pro",
      "White-label branding",
      "Team member portfolios",
      "Company domain",
      "API access",
      "Priority support",
    ],
    cta: "View Team",
    href: "/pricing",
    accent: false,
  },
];

export default function HomePage() {
  const router = useRouter();

  const handleGitHubLogin = () => {
    // Redirect to backend OAuth handler which will handle the full flow
    const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    window.location.href = `${API_URL}/api/auth/github`;
  };

  return (
    <div className="min-h-screen bg-white font-sans">
      {/* Nav */}
      <nav className="fixed top-0 inset-x-0 z-50 bg-white/90 backdrop-blur border-b border-gray-100">
        <div className="max-w-5xl mx-auto px-6 h-14 flex items-center justify-between">
          <span className="font-bold text-gray-900 text-lg tracking-tight">
            Portfolio<span className="text-blue-600">AI</span>
          </span>
          <div className="flex items-center gap-6">
            <a href="#features" className="text-sm text-gray-500 hover:text-gray-900 transition-colors hidden sm:block">
              Features
            </a>
            <a href="#pricing" className="text-sm text-gray-500 hover:text-gray-900 transition-colors hidden sm:block">
              Pricing
            </a>
            <button
              onClick={handleGitHubLogin}
              className="flex items-center gap-2 bg-gray-900 text-white text-sm font-medium px-4 py-2 rounded-lg hover:bg-gray-700 transition-colors"
            >
              <Github size={15} />
              Connect GitHub
            </button>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="pt-32 pb-24 px-6 text-center">
        <div className="max-w-3xl mx-auto stagger-children">
          <div className="inline-flex items-center gap-2 bg-blue-50 text-blue-700 text-sm font-medium px-3 py-1.5 rounded-full mb-6">
            <Zap size={13} />
            <span>AI-powered · Auto-updating · Free to start</span>
          </div>
          <h1 className="text-5xl sm:text-6xl font-bold text-gray-900 leading-[1.1] tracking-tight mb-6">
            Your portfolio,
            <br />
            <span className="text-blue-600">built by AI</span>
          </h1>
          <p className="text-xl text-gray-500 leading-relaxed mb-10 max-w-xl mx-auto">
            Connect GitHub, upload your resume. An AI agent builds your portfolio site,
            writes your bio, and keeps it updated automatically.
          </p>
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <button
              onClick={handleGitHubLogin}
              className="flex items-center justify-center gap-2 bg-gray-900 text-white font-semibold px-6 py-3.5 rounded-xl hover:bg-gray-700 transition-all hover:-translate-y-0.5"
            >
              <Github size={18} />
              Build my portfolio free
            </button>
            <a
              href="#features"
              className="flex items-center justify-center gap-2 border border-gray-200 text-gray-700 font-medium px-6 py-3.5 rounded-xl hover:bg-gray-50 transition-colors"
            >
              See how it works
              <ArrowRight size={16} />
            </a>
          </div>
          <p className="mt-4 text-sm text-gray-400">No credit card. Live in 2 minutes.</p>
        </div>

        {/* Mock browser preview */}
        <div className="mt-16 max-w-3xl mx-auto">
          <div className="bg-gray-50 rounded-2xl border border-gray-100 overflow-hidden shadow-xl shadow-gray-100/50">
            <div className="bg-white border-b border-gray-100 px-4 py-3 flex items-center gap-2">
              <div className="flex gap-1.5">
                <div className="w-3 h-3 rounded-full bg-red-300" />
                <div className="w-3 h-3 rounded-full bg-yellow-300" />
                <div className="w-3 h-3 rounded-full bg-green-300" />
              </div>
              <div className="flex-1 bg-gray-100 rounded-lg px-3 py-1 text-xs text-gray-400 max-w-xs mx-auto text-center">
                alexchen.portfolioai.app
              </div>
            </div>
            <div className="p-8 bg-gradient-to-br from-gray-50 to-white min-h-48 flex items-center justify-center">
              <div className="text-center">
                <p className="text-xs font-medium text-blue-600 uppercase tracking-widest mb-3">✦ Open to opportunities</p>
                <h2 className="text-3xl font-bold text-gray-900 mb-2">Full-Stack Engineer</h2>
                <p className="text-gray-500 text-sm max-w-xs mx-auto">
                  Building scalable systems at the intersection of AI and developer tooling.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="py-24 px-6 bg-gray-50">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-16">
            <p className="text-sm font-semibold text-blue-600 uppercase tracking-widest mb-3">How it works</p>
            <h2 className="text-4xl font-bold text-gray-900">From GitHub to live site in minutes</h2>
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6 stagger-children">
            {FEATURES.map((f, i) => (
              <div key={i} className="bg-white rounded-2xl p-6 border border-gray-100">
                <div className="w-10 h-10 bg-blue-50 rounded-xl flex items-center justify-center mb-4">
                  <f.icon size={20} className="text-blue-600" />
                </div>
                <h3 className="font-semibold text-gray-900 mb-2">{f.title}</h3>
                <p className="text-sm text-gray-500 leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="py-24 px-6">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-16">
            <p className="text-sm font-semibold text-blue-600 uppercase tracking-widest mb-3">Pricing</p>
            <h2 className="text-4xl font-bold text-gray-900">Simple, transparent pricing</h2>
          </div>
          <div className="grid md:grid-cols-3 gap-6">
            {PLANS.map((plan) => (
              <div
                key={plan.name}
                className={`rounded-2xl p-8 border flex flex-col ${
                  plan.accent
                    ? "bg-gray-900 border-gray-900 text-white"
                    : "bg-white border-gray-100"
                }`}
              >
                {plan.accent && (
                  <div className="inline-flex items-center gap-1 bg-blue-600 text-white text-xs font-semibold px-2.5 py-1 rounded-full mb-4 w-fit">
                    <Star size={10} /> Most popular
                  </div>
                )}
                <p className={`text-sm font-semibold mb-2 ${plan.accent ? "text-gray-400" : "text-gray-500"}`}>
                  {plan.name}
                </p>
                <div className="flex items-baseline gap-1 mb-1">
                  <span className="text-4xl font-bold">{plan.price}</span>
                  <span className={`text-sm ${plan.accent ? "text-gray-400" : "text-gray-400"}`}>/{plan.period}</span>
                </div>
                <ul className="mt-6 mb-8 flex-1 space-y-3">
                  {plan.features.map((feat) => (
                    <li key={feat} className="flex items-center gap-2.5 text-sm">
                      <Check size={15} className={plan.accent ? "text-blue-400" : "text-green-500"} />
                      <span className={plan.accent ? "text-gray-300" : "text-gray-600"}>{feat}</span>
                    </li>
                  ))}
                </ul>
                <button
                  onClick={() => plan.href === "/pricing" ? router.push("/pricing") : handleGitHubLogin()}
                  className={`w-full text-center py-3 rounded-xl font-semibold text-sm transition-all ${
                    plan.accent
                      ? "bg-blue-600 text-white hover:bg-blue-500"
                      : "bg-gray-900 text-white hover:bg-gray-700"
                  }`}
                >
                  {plan.cta}
                </button>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-24 px-6 bg-gray-900 text-white text-center">
        <div className="max-w-xl mx-auto">
          <h2 className="text-4xl font-bold mb-4">Ready to stand out?</h2>
          <p className="text-gray-400 mb-8">
            Join developers who let AI do the portfolio work so they can focus on building.
          </p>
          <button
            onClick={handleGitHubLogin}
            className="inline-flex items-center gap-2 bg-white text-gray-900 font-semibold px-8 py-4 rounded-xl hover:bg-gray-100 transition-all hover:-translate-y-0.5"
          >
            <Github size={18} />
            Build my portfolio free
          </button>
        </div>
      </section>

      <footer className="py-8 px-6 border-t border-gray-100 text-center">
        <p className="text-sm text-gray-400">
          © 2025 PortfolioAI · Built with{" "}
          <span className="text-red-400">♥</span> and Gemini
        </p>
      </footer>
    </div>
  );
}

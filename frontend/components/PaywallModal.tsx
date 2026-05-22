"use client";

import { X, Lock } from "lucide-react";

interface PaywallModalProps {
  type: "build" | "publish" | "edit" | null;
  onClose: () => void;
  onUpgrade: () => void;
}

const messages = {
  build: {
    title: "Upgrade to Build More",
    description: "Free users can only build 1 portfolio. Upgrade to Pro to create unlimited portfolios.",
    cta: "Upgrade to Pro",
  },
  publish: {
    title: "Publishing Requires Pro",
    description: "Publishing your portfolio to a live URL is a Pro feature. Upgrade now to go live!",
    cta: "Upgrade to Pro",
  },
  edit: {
    title: "Editing Requires Pro",
    description: "Modify and iterate on your portfolio with Pro. Unlimited edits and regenerations.",
    cta: "Upgrade to Pro",
  },
};

export default function PaywallModal({
  type,
  onClose,
  onUpgrade,
}: PaywallModalProps) {
  if (!type) return null;

  const message = messages[type];

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-slate-800 border border-slate-700 rounded-xl max-w-md w-full p-6 relative">
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-slate-400 hover:text-white transition-colors"
        >
          <X size={24} />
        </button>

        {/* Icon */}
        <div className="flex justify-center mb-4">
          <div className="w-12 h-12 bg-amber-900/30 border border-amber-700 rounded-lg flex items-center justify-center">
            <Lock className="text-amber-400" size={24} />
          </div>
        </div>

        {/* Content */}
        <h2 className="text-xl font-bold text-white text-center mb-2">{message.title}</h2>
        <p className="text-slate-300 text-center mb-6">{message.description}</p>

        {/* Features */}
        <div className="bg-slate-700/50 rounded-lg p-4 mb-6 space-y-2">
          <p className="text-sm font-semibold text-white mb-3">Pro includes:</p>
          {["Unlimited portfolios", "Publish & host online", "Edit & modify anytime", "Custom domain support"].map(
            (feature) => (
              <div key={feature} className="flex items-center gap-2 text-sm text-slate-300">
                <span className="text-green-400">✓</span>
                {feature}
              </div>
            )
          )}
        </div>

        {/* Buttons */}
        <div className="flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg font-semibold transition-colors"
          >
            Not Now
          </button>
          <button
            onClick={onUpgrade}
            className="flex-1 px-4 py-2 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white rounded-lg font-semibold transition-all"
          >
            {message.cta}
          </button>
        </div>
      </div>
    </div>
  );
}

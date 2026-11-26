"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowRight, Lock, Mail, User } from "lucide-react";
import { BrandMark } from "@/components/ui/Primitives";
import { useBreatheWise } from "@/hooks/useBreatheWise";
import { api } from "@/lib/api";

export default function AuthPage() {
  const router = useRouter();
  const { setSession, location } = useBreatheWise();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [city, setCity] = useState(location.name || "Pune");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      if (mode === "register") {
        const res = await api.register({
          name,
          email,
          password,
          city,
          latitude: location.latitude,
          longitude: location.longitude,
        });
        setSession(res.access_token, res.user);
      } else {
        const res = await api.login({ email, password });
        setSession(res.access_token, res.user);
      }
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-bw-bg text-bw-text bw-ambient-grid flex flex-col items-center justify-center p-4">
      <Link href="/" className="flex items-center gap-2.5 mb-8">
        <BrandMark className="h-9 w-9" />
        <div>
          <span className="font-semibold text-base block">BreatheWise</span>
          <span className="text-[11px] text-bw-muted">
            Breathe Smarter. Live Better.
          </span>
        </div>
      </Link>

      <div className="w-full max-w-md bw-surface rounded-2xl p-6 sm:p-8 shadow-glass space-y-6">
        <div className="flex rounded-xl bg-bw-secondary border border-white/10 p-1 text-xs">
          <button
            onClick={() => setMode("login")}
            className={`flex-1 py-2 rounded-lg font-medium transition-colors ${
              mode === "login"
                ? "bg-bw-accent text-bw-bg font-semibold"
                : "text-bw-muted hover:text-bw-text"
            }`}
          >
            Sign In
          </button>
          <button
            onClick={() => setMode("register")}
            className={`flex-1 py-2 rounded-lg font-medium transition-colors ${
              mode === "register"
                ? "bg-bw-accent text-bw-bg font-semibold"
                : "text-bw-muted hover:text-bw-text"
            }`}
          >
            Create Account
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {mode === "register" && (
            <>
              <div>
                <label className="text-xs text-bw-muted block mb-1">
                  Full Name
                </label>
                <div className="relative">
                  <User className="h-4 w-4 text-bw-muted absolute left-3 top-1/2 -translate-y-1/2" />
                  <input
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    required
                    minLength={2}
                    placeholder="Ananya Deshmukh"
                    className="w-full rounded-xl bg-bw-bg border border-white/10 pl-9 pr-3 py-2.5 text-sm"
                  />
                </div>
              </div>

              <div>
                <label className="text-xs text-bw-muted block mb-1">
                  Primary City
                </label>
                <input
                  type="text"
                  value={city}
                  onChange={(e) => setCity(e.target.value)}
                  required
                  className="w-full rounded-xl bg-bw-bg border border-white/10 px-3 py-2.5 text-sm"
                />
              </div>
            </>
          )}

          <div>
            <label className="text-xs text-bw-muted block mb-1">Email</label>
            <div className="relative">
              <Mail className="h-4 w-4 text-bw-muted absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                placeholder="you@example.com"
                className="w-full rounded-xl bg-bw-bg border border-white/10 pl-9 pr-3 py-2.5 text-sm"
              />
            </div>
          </div>

          <div>
            <label className="text-xs text-bw-muted block mb-1">Password</label>
            <div className="relative">
              <Lock className="h-4 w-4 text-bw-muted absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={8}
                placeholder="At least 8 characters"
                className="w-full rounded-xl bg-bw-bg border border-white/10 pl-9 pr-3 py-2.5 text-sm"
              />
            </div>
          </div>

          {error && (
            <div className="rounded-lg border border-bw-danger/30 bg-bw-danger/10 px-3 py-2 text-xs text-bw-danger">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full inline-flex items-center justify-center gap-2 py-3 rounded-xl bg-bw-accent text-bw-bg text-sm font-semibold hover:opacity-90 disabled:opacity-50"
          >
            {loading
              ? "Please wait..."
              : mode === "login"
              ? "Sign In"
              : "Create BreatheWise Account"}
            <ArrowRight className="h-4 w-4" />
          </button>
        </form>

        <div className="text-center">
          <Link
            href="/dashboard"
            className="text-xs text-bw-muted hover:text-bw-text underline"
          >
            Continue to Dashboard as Guest
          </Link>
        </div>
      </div>
    </div>
  );
}

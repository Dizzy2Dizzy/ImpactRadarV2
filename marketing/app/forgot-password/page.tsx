"use client";

import { useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setMessage("");
    setLoading(true);

    try {
      const response = await fetch("/api/auth/forgot-password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });

      const data = await response.json();

      if (!response.ok) {
        setError(data.error || "Failed to send reset link");
        setLoading(false);
        return;
      }

      setMessage(data.message);
      setSubmitted(true);
      setLoading(false);
    } catch (err) {
      setError("An error occurred. Please try again.");
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-6 py-12">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-[--text] mb-2">
            Forgot your password?
          </h1>
          <p className="text-[--muted]">
            {submitted 
              ? "Check your email for a reset link" 
              : "Enter your email and we'll send you a reset link"}
          </p>
        </div>

        {submitted ? (
          <div className="bg-[--panel] border border-white/10 rounded-2xl p-8">
            <div className="bg-green-500/10 border border-green-500/20 rounded-lg p-4 mb-6">
              <p className="text-sm text-green-400">{message}</p>
            </div>
            <div className="space-y-4">
              <p className="text-sm text-[--muted]">
                If you don't receive an email within a few minutes, check your spam folder or try again.
              </p>
              <div className="flex gap-3">
                <Button
                  onClick={() => {
                    setSubmitted(false);
                    setEmail("");
                    setMessage("");
                  }}
                  variant="outline"
                  className="flex-1"
                >
                  Send another link
                </Button>
                <Button asChild className="flex-1">
                  <Link href="/login">Back to login</Link>
                </Button>
              </div>
            </div>
          </div>
        ) : (
          <div className="bg-[--panel] border border-white/10 rounded-2xl p-8">
            <form onSubmit={handleSubmit} className="space-y-6">
              {error && (
                <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-3 text-sm text-red-400">
                  {error}
                </div>
              )}

              <div>
                <label
                  htmlFor="email"
                  className="block text-sm font-medium text-[--text] mb-2"
                >
                  Email address
                </label>
                <input
                  id="email"
                  name="email"
                  type="email"
                  autoComplete="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full px-4 py-3 bg-[--bg] border border-white/10 rounded-lg text-[--text] placeholder:text-[--muted] focus:outline-none focus:ring-2 focus:ring-[--primary] focus:border-transparent transition-all"
                  placeholder="you@example.com"
                />
              </div>

              <Button type="submit" className="w-full" size="lg" disabled={loading}>
                {loading ? "Sending..." : "Send reset link"}
              </Button>
            </form>

            <div className="mt-6 text-center">
              <p className="text-sm text-[--muted]">
                Remember your password?{" "}
                <Link
                  href="/login"
                  className="font-medium text-[--primary] hover:text-[--accent] transition-colors"
                >
                  Back to login
                </Link>
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

"use client";

import { useState, useEffect, Suspense } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Button } from "@/components/ui/button";

function ResetPasswordForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [token, setToken] = useState("");
  const [email, setEmail] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    const tokenParam = searchParams.get("token");
    const emailParam = searchParams.get("email");
    
    if (tokenParam) setToken(tokenParam);
    if (emailParam) setEmail(emailParam);
    
    if (!tokenParam || !emailParam) {
      setError("Invalid password reset link. Please request a new reset link.");
    }
  }, [searchParams]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setMessage("");

    if (newPassword !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }

    if (newPassword.length < 8) {
      setError("Password must be at least 8 characters long");
      return;
    }

    setLoading(true);

    try {
      const response = await fetch("/api/auth/reset-password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, token, newPassword }),
      });

      const data = await response.json();

      if (!response.ok) {
        setError(data.error || "Failed to reset password");
        setLoading(false);
        return;
      }

      setMessage(data.message);
      setSuccess(true);
      setLoading(false);

      setTimeout(() => {
        router.push("/login");
      }, 3000);
    } catch (err) {
      setError("An error occurred. Please try again.");
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div className="min-h-screen flex items-center justify-center px-6 py-12">
        <div className="w-full max-w-md">
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold text-[--text] mb-2">
              Password reset successful
            </h1>
            <p className="text-[--muted]">
              Redirecting you to login...
            </p>
          </div>

          <div className="bg-[--panel] border border-white/10 rounded-2xl p-8">
            <div className="bg-green-500/10 border border-green-500/20 rounded-lg p-4 mb-6">
              <p className="text-sm text-green-400">{message}</p>
            </div>
            <Button asChild className="w-full">
              <Link href="/login">Go to login</Link>
            </Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-6 py-12">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-[--text] mb-2">
            Set new password
          </h1>
          <p className="text-[--muted]">
            Enter your new password below
          </p>
        </div>

        <div className="bg-[--panel] border border-white/10 rounded-2xl p-8">
          <form onSubmit={handleSubmit} className="space-y-6">
            {error && (
              <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-3 text-sm text-red-400">
                {error}
              </div>
            )}

            <div>
              <label
                htmlFor="newPassword"
                className="block text-sm font-medium text-[--text] mb-2"
              >
                New password
              </label>
              <input
                id="newPassword"
                name="newPassword"
                type="password"
                required
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                className="w-full px-4 py-3 bg-[--bg] border border-white/10 rounded-lg text-[--text] placeholder:text-[--muted] focus:outline-none focus:ring-2 focus:ring-[--primary] focus:border-transparent transition-all"
                placeholder="At least 8 characters"
                disabled={!token || !email}
              />
            </div>

            <div>
              <label
                htmlFor="confirmPassword"
                className="block text-sm font-medium text-[--text] mb-2"
              >
                Confirm new password
              </label>
              <input
                id="confirmPassword"
                name="confirmPassword"
                type="password"
                required
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="w-full px-4 py-3 bg-[--bg] border border-white/10 rounded-lg text-[--text] placeholder:text-[--muted] focus:outline-none focus:ring-2 focus:ring-[--primary] focus:border-transparent transition-all"
                placeholder="Re-enter your password"
                disabled={!token || !email}
              />
            </div>

            <Button 
              type="submit" 
              className="w-full" 
              size="lg" 
              disabled={loading || !token || !email}
            >
              {loading ? "Resetting..." : "Reset password"}
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
      </div>
    </div>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-[--muted]">Loading...</p>
      </div>
    }>
      <ResetPasswordForm />
    </Suspense>
  );
}

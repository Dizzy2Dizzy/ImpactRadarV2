"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";

export default function VerifyEmailPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(true);
  const [code, setCode] = useState(["", "", "", "", "", ""]);
  const [verifying, setVerifying] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const [resendCooldown, setResendCooldown] = useState(0);
  const [resending, setResending] = useState(false);
  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);

  useEffect(() => {
    const fetchUserInfo = async () => {
      try {
        const response = await fetch("/api/auth/me");
        const data = await response.json();
        
        if (!data.isLoggedIn) {
          router.push("/login");
          return;
        }
        
        if (data.isVerified) {
          router.push("/dashboard");
          return;
        }
        
        setEmail(data.email || "your email");
        setLoading(false);
      } catch (err) {
        setLoading(false);
      }
    };

    fetchUserInfo();
  }, [router]);

  useEffect(() => {
    if (resendCooldown > 0) {
      const timer = setTimeout(() => setResendCooldown(resendCooldown - 1), 1000);
      return () => clearTimeout(timer);
    }
  }, [resendCooldown]);

  const handleCodeChange = (index: number, value: string) => {
    if (!/^\d*$/.test(value)) return;

    const newCode = [...code];
    newCode[index] = value.slice(-1);
    setCode(newCode);
    setError("");

    if (value && index < 5) {
      inputRefs.current[index + 1]?.focus();
    }
  };

  const handleKeyDown = (index: number, e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Backspace" && !code[index] && index > 0) {
      inputRefs.current[index - 1]?.focus();
    }
  };

  const handlePaste = (e: React.ClipboardEvent) => {
    e.preventDefault();
    const pastedData = e.clipboardData.getData("text").replace(/\D/g, "").slice(0, 6);
    const newCode = [...code];
    
    for (let i = 0; i < pastedData.length; i++) {
      newCode[i] = pastedData[i];
    }
    
    setCode(newCode);
    setError("");
    
    const nextEmptyIndex = pastedData.length < 6 ? pastedData.length : 5;
    inputRefs.current[nextEmptyIndex]?.focus();
  };

  const handleVerify = async () => {
    const verificationCode = code.join("");
    
    if (verificationCode.length !== 6) {
      setError("Please enter all 6 digits");
      return;
    }

    setVerifying(true);
    setError("");

    try {
      const response = await fetch("/api/auth/verify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code: verificationCode }),
      });

      const data = await response.json();

      if (response.ok) {
        setSuccess(true);
        setTimeout(() => {
          router.push("/dashboard");
        }, 1500);
      } else {
        setError(data.error || "Verification failed");
        setCode(["", "", "", "", "", ""]);
        inputRefs.current[0]?.focus();
      }
    } catch (err) {
      setError("Failed to verify code. Please try again.");
    } finally {
      setVerifying(false);
    }
  };

  const handleResendCode = async () => {
    setResending(true);
    setError("");

    try {
      const response = await fetch("/api/auth/resend-code", {
        method: "POST",
      });

      const data = await response.json();

      if (response.ok) {
        setResendCooldown(60);
        setCode(["", "", "", "", "", ""]);
        inputRefs.current[0]?.focus();
      } else {
        if (data.remainingTime) {
          setResendCooldown(data.remainingTime);
        }
        setError(data.error || "Failed to resend code");
      }
    } catch (err) {
      setError("Failed to resend code. Please try again.");
    } finally {
      setResending(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-[--muted]">Loading...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-6 py-12">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-[--primary]/10 rounded-full mb-4">
            <svg
              className="w-8 h-8 text-[--primary]"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
              />
            </svg>
          </div>
          <h1 className="text-3xl font-bold text-[--text] mb-2">
            Verify your email
          </h1>
          <p className="text-[--muted]">
            We sent a 6-digit code to {email}
          </p>
        </div>

        <div className="bg-[--panel] border border-white/10 rounded-2xl p-8">
          <div className="space-y-6">
            {success ? (
              <div className="bg-green-500/10 border border-green-500/20 rounded-lg p-4">
                <div className="flex items-center gap-3">
                  <svg className="w-5 h-5 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  <p className="text-sm font-medium text-green-300">
                    Email verified successfully! Redirecting...
                  </p>
                </div>
              </div>
            ) : (
              <>
                <div>
                  <label className="block text-sm font-medium text-[--muted] mb-3">
                    Enter verification code
                  </label>
                  <div className="flex gap-2 justify-center" onPaste={handlePaste}>
                    {code.map((digit, index) => (
                      <input
                        key={index}
                        ref={(el) => {
                          if (el) inputRefs.current[index] = el;
                        }}
                        type="text"
                        inputMode="numeric"
                        maxLength={1}
                        value={digit}
                        onChange={(e) => handleCodeChange(index, e.target.value)}
                        onKeyDown={(e) => handleKeyDown(index, e)}
                        className="w-12 h-14 text-center text-2xl font-bold bg-[--bg] border border-white/10 rounded-lg focus:border-[--primary] focus:outline-none focus:ring-2 focus:ring-[--primary]/20 text-[--text] transition-all"
                        disabled={verifying || success}
                      />
                    ))}
                  </div>
                </div>

                {error && (
                  <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4">
                    <p className="text-sm text-red-300">{error}</p>
                  </div>
                )}

                <Button
                  onClick={handleVerify}
                  className="w-full"
                  size="lg"
                  disabled={verifying || code.join("").length !== 6}
                >
                  {verifying ? "Verifying..." : "Verify Email"}
                </Button>

                <div className="text-center">
                  <button
                    onClick={handleResendCode}
                    disabled={resending || resendCooldown > 0}
                    className="text-sm text-[--muted] hover:text-[--primary] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {resending
                      ? "Sending..."
                      : resendCooldown > 0
                      ? `Resend code in ${resendCooldown}s`
                      : "Resend verification code"}
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

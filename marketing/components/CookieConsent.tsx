"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { X } from "lucide-react";

export function CookieConsent() {
  const [showBanner, setShowBanner] = useState(false);
  const [preferences, setPreferences] = useState({
    necessary: true,
    analytics: false,
    marketing: false,
  });
  const [showPreferences, setShowPreferences] = useState(false);

  useEffect(() => {
    const consent = localStorage.getItem("cookie-consent");
    if (!consent) {
      setTimeout(() => setShowBanner(true), 1000);
    } else {
      const saved = JSON.parse(consent);
      setPreferences(saved);
    }
  }, []);

  const handleAcceptAll = () => {
    const allAccepted = {
      necessary: true,
      analytics: true,
      marketing: true,
    };
    localStorage.setItem("cookie-consent", JSON.stringify(allAccepted));
    localStorage.setItem("cookie-consent-date", new Date().toISOString());
    setPreferences(allAccepted);
    setShowBanner(false);
    
    if (allAccepted.analytics && typeof window !== "undefined") {
      window.dispatchEvent(new Event("cookies-accepted"));
    }
  };

  const handleRejectAll = () => {
    const necessary = {
      necessary: true,
      analytics: false,
      marketing: false,
    };
    localStorage.setItem("cookie-consent", JSON.stringify(necessary));
    localStorage.setItem("cookie-consent-date", new Date().toISOString());
    setPreferences(necessary);
    setShowBanner(false);
  };

  const handleSavePreferences = () => {
    localStorage.setItem("cookie-consent", JSON.stringify(preferences));
    localStorage.setItem("cookie-consent-date", new Date().toISOString());
    setShowBanner(false);
    setShowPreferences(false);
    
    if (preferences.analytics && typeof window !== "undefined") {
      window.dispatchEvent(new Event("cookies-accepted"));
    }
  };

  if (!showBanner) return null;

  return (
    <>
      <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-[100]" />
      
      <div className="fixed bottom-0 left-0 right-0 z-[101] p-4 md:p-6">
        <div className="mx-auto max-w-4xl">
          <div className="rounded-2xl border border-white/10 bg-[--panel] shadow-2xl">
            <div className="p-6 md:p-8">
              <div className="flex items-start justify-between mb-4">
                <div className="flex-1">
                  <h2 className="text-xl font-semibold text-[--text] mb-2">
                    Cookie Settings
                  </h2>
                  <p className="text-sm text-[--muted] mb-4">
                    We use cookies to enhance your browsing experience, provide personalized content, and analyze our traffic. By clicking "Accept All", you consent to our use of cookies.
                  </p>
                </div>
              </div>

              {!showPreferences ? (
                <div className="space-y-4">
                  <div className="flex flex-wrap gap-3">
                    <button
                      onClick={handleAcceptAll}
                      className="flex-1 min-w-[140px] rounded-lg bg-[--primary] px-6 py-3 text-sm font-semibold text-black hover:bg-[--primary-contrast] hover:text-white transition-colors"
                    >
                      Accept All
                    </button>
                    <button
                      onClick={handleRejectAll}
                      className="flex-1 min-w-[140px] rounded-lg border border-white/10 bg-transparent px-6 py-3 text-sm font-semibold text-[--text] hover:bg-white/5 transition-colors"
                    >
                      Reject All
                    </button>
                    <button
                      onClick={() => setShowPreferences(true)}
                      className="flex-1 min-w-[140px] rounded-lg border border-white/10 bg-transparent px-6 py-3 text-sm font-semibold text-[--text] hover:bg-white/5 transition-colors"
                    >
                      Customize
                    </button>
                  </div>
                  
                  <div className="text-xs text-[--muted]">
                    By continuing to use our site, you agree to our{" "}
                    <Link href="/privacy" className="text-[--primary] hover:underline">
                      Privacy Policy
                    </Link>
                    {" "}and{" "}
                    <Link href="/terms" className="text-[--primary] hover:underline">
                      Terms of Service
                    </Link>.
                  </div>
                </div>
              ) : (
                <div className="space-y-6">
                  <div className="space-y-4">
                    <div className="flex items-start gap-4 p-4 rounded-lg border border-white/5 bg-white/[0.02]">
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-2">
                          <h3 className="text-sm font-semibold text-[--text]">
                            Necessary Cookies
                          </h3>
                          <span className="text-xs px-2 py-1 rounded-full bg-blue-500/10 text-blue-400 font-medium">
                            Always Active
                          </span>
                        </div>
                        <p className="text-xs text-[--muted]">
                          Essential for the website to function properly. These cookies enable core functionality such as security, authentication, and session management. They cannot be disabled.
                        </p>
                      </div>
                      <div className="flex items-center">
                        <div className="w-10 h-6 bg-[--primary] rounded-full opacity-50 cursor-not-allowed"></div>
                      </div>
                    </div>

                    <div className="flex items-start gap-4 p-4 rounded-lg border border-white/5 bg-white/[0.02]">
                      <div className="flex-1">
                        <h3 className="text-sm font-semibold text-[--text] mb-2">
                          Analytics Cookies
                        </h3>
                        <p className="text-xs text-[--muted]">
                          Help us understand how visitors interact with our website, which pages are visited most often, and if users experience any errors. This helps us improve the user experience.
                        </p>
                      </div>
                      <button
                        onClick={() =>
                          setPreferences((prev) => ({
                            ...prev,
                            analytics: !prev.analytics,
                          }))
                        }
                        className="flex items-center"
                      >
                        <div
                          className={`w-10 h-6 rounded-full transition-colors ${
                            preferences.analytics
                              ? "bg-[--primary]"
                              : "bg-white/10"
                          }`}
                        >
                          <div
                            className={`w-4 h-4 rounded-full bg-white mt-1 transition-transform ${
                              preferences.analytics
                                ? "translate-x-5"
                                : "translate-x-1"
                            }`}
                          />
                        </div>
                      </button>
                    </div>

                    <div className="flex items-start gap-4 p-4 rounded-lg border border-white/5 bg-white/[0.02]">
                      <div className="flex-1">
                        <h3 className="text-sm font-semibold text-[--text] mb-2">
                          Marketing Cookies
                        </h3>
                        <p className="text-xs text-[--muted]">
                          Used to track visitors across websites to display relevant and engaging advertisements. May be set by third-party advertisers with our permission.
                        </p>
                      </div>
                      <button
                        onClick={() =>
                          setPreferences((prev) => ({
                            ...prev,
                            marketing: !prev.marketing,
                          }))
                        }
                        className="flex items-center"
                      >
                        <div
                          className={`w-10 h-6 rounded-full transition-colors ${
                            preferences.marketing
                              ? "bg-[--primary]"
                              : "bg-white/10"
                          }`}
                        >
                          <div
                            className={`w-4 h-4 rounded-full bg-white mt-1 transition-transform ${
                              preferences.marketing
                                ? "translate-x-5"
                                : "translate-x-1"
                            }`}
                          />
                        </div>
                      </button>
                    </div>
                  </div>

                  <div className="flex gap-3">
                    <button
                      onClick={handleSavePreferences}
                      className="flex-1 rounded-lg bg-[--primary] px-6 py-3 text-sm font-semibold text-black hover:bg-[--primary-contrast] hover:text-white transition-colors"
                    >
                      Save Preferences
                    </button>
                    <button
                      onClick={() => setShowPreferences(false)}
                      className="rounded-lg border border-white/10 bg-transparent px-6 py-3 text-sm font-semibold text-[--text] hover:bg-white/5 transition-colors"
                    >
                      Back
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

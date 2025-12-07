"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Logo } from "./Logo";

const footerLinks = {
  product: [
    { name: "Features", href: "/product" },
    { name: "Pricing", href: "/pricing" },
    { name: "Security", href: "/security" },
    { name: "Changelog", href: "/changelog" },
  ],
  company: [
    { name: "About", href: "/about" },
    { name: "Contact", href: "/contact" },
  ],
  resources: [
    { name: "Documentation", href: "/docs" },
    { name: "API Reference", href: "/docs/api" },
    { name: "Affiliate Program", href: "/affiliate" },
  ],
  legal: [
    { name: "Privacy", href: "/privacy" },
    { name: "Terms", href: "/terms" },
    { name: "Refund Policy", href: "/refund-policy" },
    { name: "DPA", href: "/dpa" },
  ],
};

export function Footer() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [isLoggingOut, setIsLoggingOut] = useState(false);
  const router = useRouter();

  useEffect(() => {
    async function checkAuthState() {
      try {
        const response = await fetch('/api/auth/me', {
          method: 'GET',
          credentials: 'include',
        });
        const data = await response.json();
        setIsLoggedIn(data.isLoggedIn ?? false);
      } catch (error) {
        console.error('Error checking auth state:', error);
        setIsLoggedIn(false);
      }
    }

    checkAuthState();
  }, []);

  const handleLogout = async () => {
    setIsLoggingOut(true);
    try {
      const response = await fetch('/api/auth/logout', {
        method: 'POST',
        credentials: 'include',
      });
      
      if (response.ok) {
        setIsLoggedIn(false);
        router.push('/');
        router.refresh();
      } else {
        console.error('Logout failed');
        setIsLoggingOut(false);
      }
    } catch (error) {
      console.error('Error during logout:', error);
      setIsLoggingOut(false);
    }
  };
  return (
    <footer className="border-t border-white/5 bg-[--panel]">
      <div className="mx-auto max-w-7xl px-6 py-12 lg:px-8 lg:py-16">
        <div className="xl:grid xl:grid-cols-3 xl:gap-8">
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <Logo className="h-8 w-8" />
              <span className="text-lg font-semibold text-[--text]">
                Impact Radar
              </span>
            </div>
            <p className="text-sm text-[--muted] max-w-xs">
              Market-moving events tracked to the second. Powered by
              deterministic impact scoring.
            </p>
            <form className="mt-6 sm:flex sm:max-w-md">
              <input
                type="email"
                placeholder="support@impactradar.co"
                className="w-full rounded-md border border-white/10 bg-[--bg] px-4 py-2 text-sm text-[--text] placeholder:text-[--muted] focus:border-[--primary] focus:outline-none focus:ring-1 focus:ring-[--primary]"
                aria-label="Email address"
              />
              <button
                type="submit"
                className="mt-3 sm:ml-3 sm:mt-0 rounded-md bg-[--primary] px-4 py-2 text-sm font-semibold text-black hover:bg-[--primary-contrast] hover:text-white transition-colors"
              >
                Subscribe
              </button>
            </form>
          </div>
          <div className="mt-16 grid grid-cols-2 gap-8 xl:col-span-2 xl:mt-0">
            <div className="md:grid md:grid-cols-2 md:gap-8">
              <div>
                <h3 className="text-sm font-semibold text-[--text]">Product</h3>
                <ul className="mt-4 space-y-3">
                  {footerLinks.product.map((item) => (
                    <li key={item.name}>
                      <Link
                        href={item.href}
                        className="text-sm text-[--muted] hover:text-[--text] transition-colors"
                      >
                        {item.name}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
              <div className="mt-10 md:mt-0">
                <h3 className="text-sm font-semibold text-[--text]">Company</h3>
                <ul className="mt-4 space-y-3">
                  {footerLinks.company.map((item) => (
                    <li key={item.name}>
                      <Link
                        href={item.href}
                        className="text-sm text-[--muted] hover:text-[--text] transition-colors"
                      >
                        {item.name}
                      </Link>
                    </li>
                  ))}
                  {isLoggedIn && (
                    <li>
                      <button
                        onClick={handleLogout}
                        disabled={isLoggingOut}
                        className="text-sm text-[--muted] hover:text-[--text] transition-colors disabled:opacity-50"
                      >
                        {isLoggingOut ? "Logging out..." : "Log Out"}
                      </button>
                    </li>
                  )}
                </ul>
              </div>
            </div>
            <div className="md:grid md:grid-cols-2 md:gap-8">
              <div>
                <h3 className="text-sm font-semibold text-[--text]">Resources</h3>
                <ul className="mt-4 space-y-3">
                  {footerLinks.resources.map((item) => (
                    <li key={item.name}>
                      <Link
                        href={item.href}
                        className="text-sm text-[--muted] hover:text-[--text] transition-colors"
                      >
                        {item.name}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
              <div className="mt-10 md:mt-0">
                <h3 className="text-sm font-semibold text-[--text]">Legal</h3>
                <ul className="mt-4 space-y-3">
                  {footerLinks.legal.map((item) => (
                    <li key={item.name}>
                      <Link
                        href={item.href}
                        className="text-sm text-[--muted] hover:text-[--text] transition-colors"
                      >
                        {item.name}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        </div>
        <div className="mt-12 border-t border-white/5 pt-8">
          <p className="text-xs text-[--muted]">
            &copy; {new Date().getFullYear()} Impact Radar. All rights reserved.
          </p>
        </div>
      </div>
    </footer>
  );
}

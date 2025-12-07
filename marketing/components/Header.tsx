"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { Logo } from "./Logo";
import { Button } from "./ui/button";
import { Menu, X, Sun, Moon } from "lucide-react";
import { usePathname } from "next/navigation";
import { useTheme } from "./ThemeProvider";
import { NotificationsButton } from "./NotificationsButton";

const navLinks = [
  { href: "/product", label: "Product" },
  { href: "/pricing", label: "Pricing" },
  { href: "/blog", label: "Blog" },
  { href: "/docs/api", label: "API Docs" },
  { href: "/guide", label: "Guide" },
  { href: "/market-echo", label: "Market Echo" },
  { href: "/backtesting", label: "Backtesting" },
  { href: "/security", label: "Security" },
];

interface HeaderProps {
  isLoggedIn?: boolean;
}

// Helper function to check if session cookie exists (optimistic auth check)
function hasSessionCookie(): boolean {
  if (typeof document === 'undefined') return false;
  return document.cookie.split(';').some(cookie => cookie.trim().startsWith('session='));
}

export function Header({ isLoggedIn: isLoggedInProp }: HeaderProps = {}) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  // Optimistically check for session cookie on mount
  const [isLoggedIn, setIsLoggedIn] = useState(isLoggedInProp ?? hasSessionCookie());
  const pathname = usePathname();
  const { theme, toggleTheme } = useTheme();

  useEffect(() => {
    if (isLoggedInProp !== undefined) {
      setIsLoggedIn(isLoggedInProp);
      return;
    }

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
  }, [isLoggedInProp]);

  return (
    <header className="sticky top-0 z-50 border-b border-white/5 bg-[--bg]/80 backdrop-blur-xl">
      <nav className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4 lg:px-8">
        <div className="flex lg:flex-1">
          <Link href="/" className="-m-1.5 p-1.5 flex items-center gap-3">
            <Logo className="h-8 w-8" />
            <span className="text-lg font-semibold text-[--text]">
              Impact Radar
            </span>
          </Link>
        </div>

        <div className="flex lg:hidden gap-2 items-center">
          <button
            onClick={toggleTheme}
            className="p-2 rounded-lg text-[--muted] hover:text-[--text] hover:bg-white/5 transition-colors"
            aria-label="Toggle theme"
          >
            {theme === "dark" ? (
              <Sun className="h-5 w-5" />
            ) : (
              <Moon className="h-5 w-5" />
            )}
          </button>
          <button
            type="button"
            className="-m-2.5 inline-flex items-center justify-center rounded-md p-2.5 text-[--text]"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            aria-label="Toggle menu"
          >
            {mobileMenuOpen ? (
              <X className="h-6 w-6" />
            ) : (
              <Menu className="h-6 w-6" />
            )}
          </button>
        </div>

        <div className="hidden lg:flex lg:gap-x-8">
          {navLinks.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="text-sm font-medium text-[--muted] transition-colors hover:text-[--text]"
            >
              {link.label}
            </Link>
          ))}
        </div>

        <div className="hidden lg:flex lg:flex-1 lg:justify-end lg:gap-4 lg:items-center">
          <button
            onClick={toggleTheme}
            className="p-2 rounded-lg text-[--muted] hover:text-[--text] hover:bg-white/5 transition-colors"
            aria-label="Toggle theme"
          >
            {theme === "dark" ? (
              <Sun className="h-5 w-5" />
            ) : (
              <Moon className="h-5 w-5" />
            )}
          </button>
          {isLoggedIn && <NotificationsButton />}
          {!isLoggedIn && (
            <Button asChild variant="outline">
              <Link href="/login">Sign In</Link>
            </Button>
          )}
          <Button asChild>
            <Link href={isLoggedIn ? "/dashboard" : "/app"}>{isLoggedIn ? "Dashboard" : "Open App"}</Link>
          </Button>
        </div>
      </nav>

      {mobileMenuOpen && (
        <div className="lg:hidden">
          <div className="space-y-2 px-6 pb-6 pt-2">
            {navLinks.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className="block rounded-lg px-3 py-2 text-base font-medium text-[--text] hover:bg-white/5"
                onClick={() => setMobileMenuOpen(false)}
              >
                {link.label}
              </Link>
            ))}
            <div className="pt-4 space-y-2">
              {!isLoggedIn && (
                <Button asChild variant="outline" className="w-full">
                  <Link href="/login">Sign In</Link>
                </Button>
              )}
              <Button asChild className="w-full">
                <Link href={isLoggedIn ? "/dashboard" : "/app"}>{isLoggedIn ? "Dashboard" : "Open App"}</Link>
              </Button>
            </div>
          </div>
        </div>
      )}
    </header>
  );
}

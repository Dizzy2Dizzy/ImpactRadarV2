import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import { Shield, Lock, Key, CheckCircle2, AlertCircle, Database, Zap, Users, FileCheck } from "lucide-react";

const securityFeatures = [
  {
    icon: <Key className="h-6 w-6" />,
    title: "Access Control",
    description:
      "User data is designed to be strictly isolated. User A cannot access User B's alerts, portfolios, or watchlists. Admin-only endpoints return 403 to unauthorized users.",
  },
  {
    icon: <Lock className="h-6 w-6" />,
    title: "Secrets Management",
    description:
      "Secrets are stored in environment variables; we avoid hard-coding API keys. All API keys, JWT secrets, and credentials are environment-based. We avoid logging sensitive fields and redact them in structured logs.",
  },
  {
    icon: <Shield className="h-6 w-6" />,
    title: "XSS Protection",
    description:
      "We render event data as plain text and do not use raw HTML rendering. React's automatic escaping prevents script injection attacks.",
  },
  {
    icon: <FileCheck className="h-6 w-6" />,
    title: "Webhook Security",
    description:
      "Stripe webhooks validate cryptographic signatures before processing. Fake payment events cannot change subscription plans or issue API keys.",
  },
  {
    icon: <Zap className="h-6 w-6" />,
    title: "DoS Protection",
    description:
      "Rate limiting on all endpoints: 5 registrations/min, 10 logins/min. WebSocket connections capped at 5 per user. API limits based on plan tier.",
  },
  {
    icon: <Database className="h-6 w-6" />,
    title: "Password Security",
    description:
      "bcrypt hashing with cost factor 12 and per-user salts. Minimum 8 characters with uppercase, lowercase, number, and special character requirements.",
  },
  {
    icon: <Users className="h-6 w-6" />,
    title: "Session Management",
    description:
      "JWT-based authentication with HTTP-only cookies. 24-hour session expiry with automatic logout. CSRF protection via session secrets.",
  },
  {
    icon: <CheckCircle2 className="h-6 w-6" />,
    title: "Data Sovereignty",
    description:
      "Your data is yours. We never sell or share user data with third parties. GDPR and CCPA compliant data handling.",
  },
];

const dataPractices = [
  "User data designed to be strictly isolated - verified by 12 access control tests",
  "Secrets stored in environment variables - automated detection scans repository",
  "PII redacted from logs where possible (email, phone, API keys, tokens)",
  "Event data rendered as plain text to prevent XSS attacks",
  "Stripe webhook signatures validated before processing payments",
  "Rate limiting: 5 registrations/min, 10 logins/min, plan-based API limits",
  "WebSocket connections: max 5 per user with 500-message buffer",
  "Event data sourced from official SEC, FDA, and company filings",
  "TLS encryption for all data in transit",
  "SQLAlchemy parameterized queries prevent SQL injection",
  "Regular security audits with 47+ comprehensive security tests",
];

const auditFindings = [
  {
    category: "Access Control",
    status: "PASSED",
    details: "User-scoped endpoints designed to enforce user_id isolation. Admin endpoints protected by require_admin dependency. No cross-user data leaks detected in testing.",
  },
  {
    category: "Secrets Management",
    status: "PASSED",
    details: "No hardcoded secrets found in repository scan. Secrets loaded from environment variables. API keys masked in responses (only last 4 chars shown).",
  },
  {
    category: "XSS Protection",
    status: "PASSED",
    details: "No instances of dangerouslySetInnerHTML found. React auto-escaping enforced. Malicious payloads rendered as plain text in testing.",
  },
  {
    category: "Webhook Security",
    status: "PASSED",
    details: "Stripe webhooks validate signatures before processing. Invalid signatures rejected with 400 error. Alert dispatch rate-limited to prevent spam.",
  },
  {
    category: "DoS Protection",
    status: "PASSED",
    details: "Comprehensive rate limits on all endpoints. Login: 10 attempts/min, Register: 5/min. Monthly API quotas: Pro (10k/month), Team (100k/month). WebSocket: max 5 connections per user.",
  },
];

export default function SecurityPage() {
  return (
    <div className="min-h-screen">
      <Header />
      <main className="py-16 lg:py-24">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <div className="mx-auto max-w-2xl text-center">
            <h1 className="text-4xl md:text-6xl font-semibold tracking-tight text-[--text]">
              Enterprise-Grade <span className="text-[--primary]">Security</span>
            </h1>
            <p className="mt-6 text-lg text-[--muted]">
              Production-ready security hardening across 5 critical risk areas. Comprehensive testing validates protection against unauthorized access, data leaks, XSS, webhook spoofing, and DoS attacks.
            </p>
            <p className="mt-2 text-sm text-[--muted]">
              Last updated: November 15, 2025 | Applies to the current Impact Radar backend and dashboard
            </p>
          </div>

          <div className="mt-8 max-w-4xl mx-auto">
            <div className="rounded-2xl border border-blue-500/20 bg-blue-500/5 p-6">
              <div className="flex gap-4">
                <AlertCircle className="h-6 w-6 text-blue-400 flex-shrink-0" />
                <div>
                  <h3 className="text-lg font-semibold text-[--text] mb-2">
                    Security Review Disclosure
                  </h3>
                  <p className="text-sm text-[--muted] mb-3">
                    Internal engineering security review – not an independent third-party audit.
                  </p>
                  <p className="text-sm text-[--muted]">
                    No critical issues identified during internal review; further external security testing is planned before GA.
                  </p>
                </div>
              </div>
            </div>
          </div>

          <div className="mt-16 grid gap-8 md:grid-cols-2 lg:grid-cols-4">
            {securityFeatures.map((feature) => (
              <div
                key={feature.title}
                className="rounded-2xl border border-white/10 bg-[--panel] p-6"
              >
                <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-[--primary]/10 text-[--primary] mb-4">
                  {feature.icon}
                </div>
                <h3 className="text-lg font-semibold text-[--text] mb-2">
                  {feature.title}
                </h3>
                <p className="text-sm text-[--muted]">{feature.description}</p>
              </div>
            ))}
          </div>

          <div className="mt-24 max-w-4xl mx-auto">
            <h2 className="text-3xl font-semibold text-[--text] mb-8">
              Security Practices
            </h2>
            <div className="rounded-3xl border border-white/10 bg-[--panel] p-8">
              <ul className="space-y-4">
                {dataPractices.map((practice) => (
                  <li key={practice} className="flex items-start gap-3">
                    <CheckCircle2 className="h-5 w-5 text-[--accent] mt-0.5 flex-shrink-0" />
                    <span className="text-[--text]">{practice}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>

          <div className="mt-24 max-w-4xl mx-auto">
            <h2 className="text-3xl font-semibold text-[--text] mb-8">
              Security Audit Results
            </h2>
            <div className="space-y-4">
              {auditFindings.map((finding) => (
                <div
                  key={finding.category}
                  className="rounded-2xl border border-white/10 bg-[--panel] p-6"
                >
                  <div className="flex items-start justify-between mb-3">
                    <h3 className="text-lg font-semibold text-[--text]">
                      {finding.category}
                    </h3>
                    <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-green-500/10 text-green-400 text-sm font-medium">
                      <CheckCircle2 className="h-4 w-4" />
                      {finding.status}
                    </span>
                  </div>
                  <p className="text-sm text-[--muted]">{finding.details}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="mt-16 max-w-4xl mx-auto">
            <div className="rounded-3xl border border-blue-500/20 bg-blue-500/5 p-8">
              <h3 className="text-xl font-semibold text-[--text] mb-4">
                OWASP Top 10 Compliance
              </h3>
              <p className="text-[--muted] mb-6">
                Impact Radar addresses key OWASP Top 10 security risks with documented evidence and comprehensive test coverage:
              </p>
              <div className="grid md:grid-cols-2 gap-4">
                <div className="flex items-start gap-2">
                  <CheckCircle2 className="h-5 w-5 text-blue-400 mt-0.5 flex-shrink-0" />
                  <span className="text-sm text-[--text]">A01: Broken Access Control</span>
                </div>
                <div className="flex items-start gap-2">
                  <CheckCircle2 className="h-5 w-5 text-blue-400 mt-0.5 flex-shrink-0" />
                  <span className="text-sm text-[--text]">A02: Cryptographic Failures</span>
                </div>
                <div className="flex items-start gap-2">
                  <CheckCircle2 className="h-5 w-5 text-blue-400 mt-0.5 flex-shrink-0" />
                  <span className="text-sm text-[--text]">A03: Injection Prevention</span>
                </div>
                <div className="flex items-start gap-2">
                  <CheckCircle2 className="h-5 w-5 text-blue-400 mt-0.5 flex-shrink-0" />
                  <span className="text-sm text-[--text]">A05: Security Misconfiguration</span>
                </div>
                <div className="flex items-start gap-2">
                  <CheckCircle2 className="h-5 w-5 text-blue-400 mt-0.5 flex-shrink-0" />
                  <span className="text-sm text-[--text]">A07: Authentication Failures</span>
                </div>
                <div className="flex items-start gap-2">
                  <CheckCircle2 className="h-5 w-5 text-blue-400 mt-0.5 flex-shrink-0" />
                  <span className="text-sm text-[--text]">A09: Security Logging</span>
                </div>
              </div>
            </div>
          </div>

          <div className="mt-16 max-w-4xl mx-auto">
            <div className="rounded-2xl border border-yellow-500/20 bg-yellow-500/5 p-6">
              <div className="flex gap-4">
                <AlertCircle className="h-6 w-6 text-yellow-400 flex-shrink-0" />
                <div>
                  <h3 className="text-lg font-semibold text-[--text] mb-2">
                    Important Disclaimer
                  </h3>
                  <p className="text-sm text-[--muted]">
                    Impact Radar provides informational data only. This is not
                    investment advice. No performance guarantees. Always verify
                    with original filings and consult licensed financial advisors.
                  </p>
                </div>
              </div>
            </div>
          </div>

          <div className="mt-12 max-w-4xl mx-auto text-center">
            <p className="text-sm text-[--muted]">
              Last security audit: November 2025 | Next review: February 2026
            </p>
          </div>
        </div>
      </main>
      <Footer />
    </div>
  );
}

import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";

export default function PrivacyPage() {
  return (
    <div className="min-h-screen">
      <Header />
      <main className="py-16 lg:py-24">
        <div className="mx-auto max-w-4xl px-6 lg:px-8">
          <h1 className="text-4xl md:text-6xl font-semibold tracking-tight text-[--text] mb-6">
            Privacy Policy
          </h1>
          <p className="text-sm text-[--muted] mb-12">
            Last updated: November 10, 2024
          </p>

          <div className="space-y-8">
            <section className="rounded-3xl border border-white/10 bg-[--panel] p-8">
              <h2 className="text-2xl font-semibold text-[--text] mb-4">
                Information We Collect
              </h2>
              <div className="space-y-3 text-[--muted]">
                <p>
                  We collect information you provide directly to us, including:
                </p>
                <ul className="list-disc list-inside space-y-2 ml-4">
                  <li>Account information (email, password)</li>
                  <li>Watchlist preferences and saved searches</li>
                  <li>Usage data and analytics</li>
                  <li>Communication preferences for alerts</li>
                </ul>
              </div>
            </section>

            <section className="rounded-3xl border border-white/10 bg-[--panel] p-8">
              <h2 className="text-2xl font-semibold text-[--text] mb-4">
                How We Use Your Information
              </h2>
              <div className="space-y-3 text-[--muted]">
                <p>We use the information we collect to:</p>
                <ul className="list-disc list-inside space-y-2 ml-4">
                  <li>Provide, maintain, and improve our services</li>
                  <li>Send you alerts and notifications you've requested</li>
                  <li>Respond to your comments and questions</li>
                  <li>Protect against fraud and abuse</li>
                </ul>
              </div>
            </section>

            <section className="rounded-3xl border border-white/10 bg-[--panel] p-8">
              <h2 className="text-2xl font-semibold text-[--text] mb-4">
                Data Security
              </h2>
              <p className="text-[--muted]">
                We implement industry-standard security measures including:
                bcrypt password hashing, encrypted sessions, 2-factor
                authentication, and PII data protection. All data is encrypted
                in transit using TLS 1.3.
              </p>
            </section>

            <section className="rounded-3xl border border-white/10 bg-[--panel] p-8">
              <h2 className="text-2xl font-semibold text-[--text] mb-4">
                Data Sharing
              </h2>
              <p className="text-[--muted]">
                We do not sell, trade, or rent your personal information to
                third parties. We may share aggregated, anonymized data for
                analytics purposes.
              </p>
            </section>

            <section className="rounded-3xl border border-white/10 bg-[--panel] p-8">
              <h2 className="text-2xl font-semibold text-[--text] mb-4">
                Your Rights
              </h2>
              <div className="space-y-3 text-[--muted]">
                <p>You have the right to:</p>
                <ul className="list-disc list-inside space-y-2 ml-4">
                  <li>Access your personal data</li>
                  <li>Request data deletion</li>
                  <li>Opt out of marketing communications</li>
                  <li>Export your data</li>
                </ul>
              </div>
            </section>

            <section className="rounded-3xl border border-white/10 bg-[--panel] p-8">
              <h2 className="text-2xl font-semibold text-[--text] mb-4">
                Contact Us
              </h2>
              <p className="text-[--muted]">
                For privacy-related questions, contact us at{" "}
                <a
                  href="mailto:privacy@impactradar.co"
                  className="text-[--primary] hover:text-[--accent]"
                >
                  privacy@impactradar.co
                </a>
              </p>
            </section>
          </div>
        </div>
      </main>
      <Footer />
    </div>
  );
}

import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";

export default function TermsPage() {
  return (
    <div className="min-h-screen">
      <Header />
      <main className="py-16 lg:py-24">
        <div className="mx-auto max-w-4xl px-6 lg:px-8">
          <h1 className="text-4xl md:text-6xl font-semibold tracking-tight text-[--text] mb-6">
            Terms of Service
          </h1>
          <p className="text-sm text-[--muted] mb-12">
            Last updated: November 10, 2024
          </p>

          <div className="space-y-8">
            <section className="rounded-3xl border border-white/10 bg-[--panel] p-8">
              <h2 className="text-2xl font-semibold text-[--text] mb-4">
                1. Acceptance of Terms
              </h2>
              <p className="text-[--muted]">
                By accessing and using Impact Radar, you accept and agree to be
                bound by the terms and provision of this agreement. If you do
                not agree to these terms, please do not use our service.
              </p>
            </section>

            <section className="rounded-3xl border border-white/10 bg-[--panel] p-8">
              <h2 className="text-2xl font-semibold text-[--text] mb-4">
                2. Service Description
              </h2>
              <p className="text-[--muted]">
                Impact Radar provides event tracking and impact scoring for
                publicly traded companies. All information is provided for
                informational purposes only and does not constitute investment
                advice.
              </p>
            </section>

            <section className="rounded-3xl border border-white/10 bg-[--panel] p-8">
              <h2 className="text-2xl font-semibold text-[--text] mb-4">
                3. Disclaimer
              </h2>
              <div className="space-y-3 text-[--muted]">
                <p className="font-semibold text-yellow-400">
                  IMPORTANT: Please read carefully.
                </p>
                <p>
                  Impact Radar is NOT investment advice. Past performance does
                  not guarantee future results. All events and impact scores are
                  provided for informational purposes only. Always verify
                  information with original filings and consult licensed
                  financial advisors before making investment decisions.
                </p>
                <p>
                  We make no warranties about the accuracy, completeness, or
                  timeliness of information. Market conditions change rapidly
                  and event impact may differ from our scoring.
                </p>
              </div>
            </section>

            <section className="rounded-3xl border border-white/10 bg-[--panel] p-8">
              <h2 className="text-2xl font-semibold text-[--text] mb-4">
                4. User Responsibilities
              </h2>
              <div className="space-y-3 text-[--muted]">
                <p>You agree to:</p>
                <ul className="list-disc list-inside space-y-2 ml-4">
                  <li>Provide accurate account information</li>
                  <li>Maintain the security of your account credentials</li>
                  <li>
                    Not use the service for illegal or unauthorized purposes
                  </li>
                  <li>
                    Not attempt to disrupt or compromise our infrastructure
                  </li>
                </ul>
              </div>
            </section>

            <section className="rounded-3xl border border-white/10 bg-[--panel] p-8">
              <h2 className="text-2xl font-semibold text-[--text] mb-4">
                5. API Usage
              </h2>
              <p className="text-[--muted]">
                API access is subject to rate limits as specified in your plan.
                Excessive usage may result in throttling or account suspension.
                You may not resell or redistribute API data without written
                permission.
              </p>
            </section>

            <section className="rounded-3xl border border-white/10 bg-[--panel] p-8">
              <h2 className="text-2xl font-semibold text-[--text] mb-4">
                6. Limitation of Liability
              </h2>
              <p className="text-[--muted]">
                Impact Radar and its affiliates shall not be liable for any
                direct, indirect, incidental, special, consequential or
                exemplary damages resulting from your use of the service or any
                trading decisions made based on our data.
              </p>
            </section>

            <section className="rounded-3xl border border-white/10 bg-[--panel] p-8">
              <h2 className="text-2xl font-semibold text-[--text] mb-4">
                7. Changes to Terms
              </h2>
              <p className="text-[--muted]">
                We reserve the right to modify these terms at any time. We will
                notify users of significant changes via email. Continued use of
                the service after changes constitutes acceptance of new terms.
              </p>
            </section>

            <section className="rounded-3xl border border-white/10 bg-[--panel] p-8">
              <h2 className="text-2xl font-semibold text-[--text] mb-4">
                8. Contact
              </h2>
              <p className="text-[--muted]">
                For questions about these terms, contact us at{" "}
                <a
                  href="mailto:legal@impactradar.co"
                  className="text-[--primary] hover:text-[--accent]"
                >
                  legal@impactradar.co
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

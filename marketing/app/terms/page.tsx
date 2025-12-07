import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";

export const metadata = {
  title: "Terms of Service | Impact Radar",
  description: "Terms of Service for Impact Radar - Event-driven signal engine for active traders",
};

export default function TermsPage() {
  return (
    <div className="min-h-screen bg-[--background]">
      <Header />
      <main className="py-16 lg:py-24">
        <div className="mx-auto max-w-4xl px-6 lg:px-8">
          <div className="text-center mb-12">
            <h1 className="text-4xl font-semibold tracking-tight text-[--text]">
              Terms of Service
            </h1>
            <p className="mt-4 text-[--muted]">
              Last updated: November 18, 2025
            </p>
          </div>

          <div className="prose prose-invert max-w-none">
            <div className="space-y-8 text-[--muted]">
              <section>
                <h2 className="text-2xl font-semibold text-[--text] mb-4">1. Acceptance of Terms</h2>
                <p>
                  By accessing and using Impact Radar ("Service"), you accept and agree to be bound by the terms and provisions of this agreement. If you do not agree to these Terms of Service, you may not access or use the Service.
                </p>
                <p className="mt-4">
                  These Terms of Service apply to all users of the Service, including without limitation users who are browsers, vendors, customers, merchants, and contributors of content.
                </p>
              </section>

              <section>
                <h2 className="text-2xl font-semibold text-[--text] mb-4">2. Description of Service</h2>
                <p>
                  Impact Radar is an event-driven signal engine that provides market event data, impact scoring, and analytical tools for active equity and biotech traders. The Service includes:
                </p>
                <ul className="list-disc pl-6 mt-4 space-y-2">
                  <li>Real-time and historical market event data from SEC filings, FDA announcements, and corporate events</li>
                  <li>Deterministic and probabilistic impact scoring with directional confidence metrics</li>
                  <li>Watchlist management and portfolio analysis tools</li>
                  <li>Alert systems for event notifications</li>
                  <li>API access for programmatic data retrieval (Pro and Enterprise plans)</li>
                  <li>Advanced analytics including backtesting, correlation analysis, and peer comparison (premium features)</li>
                </ul>
              </section>

              <section>
                <h2 className="text-2xl font-semibold text-[--text] mb-4">3. User Accounts</h2>
                <h3 className="text-xl font-semibold text-[--text] mt-6 mb-3">3.1 Account Creation</h3>
                <p>
                  To access certain features of the Service, you must register for an account. You agree to provide accurate, current, and complete information during the registration process and to update such information to keep it accurate, current, and complete.
                </p>

                <h3 className="text-xl font-semibold text-[--text] mt-6 mb-3">3.2 Account Security</h3>
                <p>
                  You are responsible for safeguarding the password that you use to access the Service and for any activities or actions under your password. You agree not to disclose your password to any third party. You must notify us immediately upon becoming aware of any breach of security or unauthorized use of your account.
                </p>

                <h3 className="text-xl font-semibold text-[--text] mt-6 mb-3">3.3 Account Termination</h3>
                <p>
                  We reserve the right to suspend or terminate your account and access to the Service at our sole discretion, without notice, for conduct that we believe violates these Terms of Service or is harmful to other users, us, or third parties, or for any other reason.
                </p>
              </section>

              <section>
                <h2 className="text-2xl font-semibold text-[--text] mb-4">4. Subscription Plans and Billing</h2>
                <h3 className="text-xl font-semibold text-[--text] mt-6 mb-3">4.1 Plan Tiers</h3>
                <p>
                  Impact Radar offers multiple subscription tiers (Free, Pro, Enterprise) with different features and pricing. Current pricing and features are available at impactradar.co/pricing.
                </p>

                <h3 className="text-xl font-semibold text-[--text] mt-6 mb-3">4.2 Billing</h3>
                <p>
                  Paid subscriptions are billed on a recurring basis (monthly or annually, depending on your selection). You will be charged at the beginning of each billing cycle. All fees are non-refundable except as expressly stated in our Refund Policy.
                </p>

                <h3 className="text-xl font-semibold text-[--text] mt-6 mb-3">4.3 Free Trial</h3>
                <p>
                  We may offer a free trial period for certain subscription plans. After the trial period ends, you will be automatically charged for the selected plan unless you cancel before the trial ends.
                </p>

                <h3 className="text-xl font-semibold text-[--text] mt-6 mb-3">4.4 Cancellation</h3>
                <p>
                  You may cancel your subscription at any time through your account settings. Cancellation will be effective at the end of your current billing period. You will continue to have access to paid features until the end of your billing period.
                </p>

                <h3 className="text-xl font-semibold text-[--text] mt-6 mb-3">4.5 Price Changes</h3>
                <p>
                  We reserve the right to modify our pricing at any time. Price changes will not affect your current billing cycle and will take effect at your next renewal. We will provide at least 30 days' notice of any price changes.
                </p>
              </section>

              <section>
                <h2 className="text-2xl font-semibold text-[--text] mb-4">5. Acceptable Use</h2>
                <p>You agree not to:</p>
                <ul className="list-disc pl-6 mt-4 space-y-2">
                  <li>Use the Service for any illegal purpose or in violation of any laws</li>
                  <li>Violate or infringe the rights of others, including intellectual property rights</li>
                  <li>Transmit any viruses, malware, or other malicious code</li>
                  <li>Attempt to gain unauthorized access to the Service or related systems</li>
                  <li>Interfere with or disrupt the Service or servers or networks connected to the Service</li>
                  <li>Use automated systems (bots, scrapers) to access the Service without explicit permission</li>
                  <li>Resell, redistribute, or make the Service available to third parties without authorization</li>
                  <li>Reverse engineer, decompile, or attempt to extract source code from the Service</li>
                  <li>Remove or obscure any proprietary notices on the Service</li>
                  <li>Use the Service to compete with us or create a similar service</li>
                </ul>
              </section>

              <section>
                <h2 className="text-2xl font-semibold text-[--text] mb-4">6. Data and Content</h2>
                <h3 className="text-xl font-semibold text-[--text] mt-6 mb-3">6.1 Data Sources</h3>
                <p>
                  Impact Radar aggregates data from public sources including SEC EDGAR filings, FDA announcements, and corporate press releases. We provide source links for verification purposes.
                </p>

                <h3 className="text-xl font-semibold text-[--text] mt-6 mb-3">6.2 Data Accuracy</h3>
                <p>
                  While we strive to provide accurate and up-to-date information, we make no warranties or representations regarding the accuracy, completeness, or timeliness of the data. All data is provided "as is" without warranty of any kind.
                </p>

                <h3 className="text-xl font-semibold text-[--text] mt-6 mb-3">6.3 Not Financial Advice</h3>
                <p className="font-semibold text-yellow-400">
                  IMPORTANT: Impact Radar provides data and analytical tools only. The Service does not provide investment advice, financial advice, trading advice, or any other sort of advice. All information is provided for informational purposes only. You should not construe any such information as legal, tax, investment, financial, or other advice. You are solely responsible for your investment decisions.
                </p>

                <h3 className="text-xl font-semibold text-[--text] mt-6 mb-3">6.4 User Content</h3>
                <p>
                  You retain ownership of any content you submit to the Service (watchlists, custom scoring preferences, etc.). By submitting content, you grant us a worldwide, non-exclusive, royalty-free license to use, reproduce, and display such content solely for the purpose of operating and improving the Service.
                </p>
              </section>

              <section>
                <h2 className="text-2xl font-semibold text-[--text] mb-4">7. Intellectual Property</h2>
                <p>
                  The Service and its original content, features, and functionality are owned by Impact Radar and are protected by international copyright, trademark, patent, trade secret, and other intellectual property laws.
                </p>
                <p className="mt-4">
                  Our trademarks and trade dress may not be used in connection with any product or service without prior written consent.
                </p>
              </section>

              <section>
                <h2 className="text-2xl font-semibold text-[--text] mb-4">8. API Usage</h2>
                <p>
                  If you use our API, you agree to comply with rate limits and usage restrictions specified in your subscription plan. Excessive API usage may result in temporary or permanent suspension of API access.
                </p>
                <p className="mt-4">
                  You must include proper attribution when displaying data obtained through our API. You may not cache API data for longer than 24 hours without explicit permission.
                </p>
              </section>

              <section>
                <h2 className="text-2xl font-semibold text-[--text] mb-4">9. Disclaimer of Warranties</h2>
                <p className="uppercase font-semibold">
                  THE SERVICE IS PROVIDED "AS IS" AND "AS AVAILABLE" WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO IMPLIED WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT.
                </p>
                <p className="mt-4">
                  We do not warrant that the Service will be uninterrupted, secure, or error-free. We do not warrant that defects will be corrected or that the Service is free of viruses or other harmful components.
                </p>
              </section>

              <section>
                <h2 className="text-2xl font-semibold text-[--text] mb-4">10. Limitation of Liability</h2>
                <p className="uppercase font-semibold">
                  TO THE MAXIMUM EXTENT PERMITTED BY LAW, IMPACT RADAR SHALL NOT BE LIABLE FOR ANY INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES, OR ANY LOSS OF PROFITS OR REVENUES, WHETHER INCURRED DIRECTLY OR INDIRECTLY, OR ANY LOSS OF DATA, USE, GOODWILL, OR OTHER INTANGIBLE LOSSES.
                </p>
                <p className="mt-4">
                  IN NO EVENT SHALL OUR AGGREGATE LIABILITY EXCEED THE GREATER OF ONE HUNDRED DOLLARS ($100) OR THE AMOUNT YOU PAID US IN THE TWELVE (12) MONTHS PRECEDING THE EVENT GIVING RISE TO LIABILITY.
                </p>
              </section>

              <section>
                <h2 className="text-2xl font-semibold text-[--text] mb-4">11. Indemnification</h2>
                <p>
                  You agree to indemnify, defend, and hold harmless Impact Radar and its officers, directors, employees, and agents from and against any claims, liabilities, damages, losses, and expenses arising out of or in any way connected with your access to or use of the Service, your violation of these Terms, or your violation of any rights of another.
                </p>
              </section>

              <section>
                <h2 className="text-2xl font-semibold text-[--text] mb-4">12. Third-Party Services</h2>
                <p>
                  The Service may contain links to third-party websites or services that are not owned or controlled by Impact Radar. We have no control over and assume no responsibility for the content, privacy policies, or practices of any third-party websites or services.
                </p>
              </section>

              <section>
                <h2 className="text-2xl font-semibold text-[--text] mb-4">13. Modifications to Service</h2>
                <p>
                  We reserve the right to modify or discontinue, temporarily or permanently, the Service (or any part thereof) with or without notice. We shall not be liable to you or any third party for any modification, suspension, or discontinuance of the Service.
                </p>
              </section>

              <section>
                <h2 className="text-2xl font-semibold text-[--text] mb-4">14. Changes to Terms</h2>
                <p>
                  We reserve the right to modify these Terms at any time. We will notify users of material changes by email or through the Service. Your continued use of the Service after such modifications constitutes your acceptance of the updated Terms.
                </p>
              </section>

              <section>
                <h2 className="text-2xl font-semibold text-[--text] mb-4">15. Governing Law and Jurisdiction</h2>
                <p>
                  These Terms shall be governed by and construed in accordance with the laws of the State of Delaware, United States, without regard to its conflict of law provisions.
                </p>
                <p className="mt-4">
                  You agree to submit to the personal and exclusive jurisdiction of the courts located within Delaware for the resolution of any disputes.
                </p>
              </section>

              <section>
                <h2 className="text-2xl font-semibold text-[--text] mb-4">16. Dispute Resolution</h2>
                <h3 className="text-xl font-semibold text-[--text] mt-6 mb-3">16.1 Informal Resolution</h3>
                <p>
                  Before filing a claim, you agree to attempt to resolve the dispute informally by contacting us at support@impactradar.co. We will attempt to resolve the dispute informally within 60 days.
                </p>

                <h3 className="text-xl font-semibold text-[--text] mt-6 mb-3">16.2 Arbitration</h3>
                <p>
                  Any disputes that cannot be resolved informally shall be resolved through binding arbitration in accordance with the American Arbitration Association's rules, except as modified by these Terms.
                </p>

                <h3 className="text-xl font-semibold text-[--text] mt-6 mb-3">16.3 Class Action Waiver</h3>
                <p>
                  You agree that any arbitration or proceeding shall be limited to the dispute between us and you individually. You waive any right to participate in a class action, collective action, or other consolidated proceeding.
                </p>
              </section>

              <section>
                <h2 className="text-2xl font-semibold text-[--text] mb-4">17. Severability</h2>
                <p>
                  If any provision of these Terms is found to be unenforceable or invalid, that provision shall be limited or eliminated to the minimum extent necessary so that these Terms shall otherwise remain in full force and effect.
                </p>
              </section>

              <section>
                <h2 className="text-2xl font-semibold text-[--text] mb-4">18. Entire Agreement</h2>
                <p>
                  These Terms, together with our Privacy Policy and any other legal notices published by us on the Service, shall constitute the entire agreement between you and Impact Radar concerning the Service.
                </p>
              </section>

              <section>
                <h2 className="text-2xl font-semibold text-[--text] mb-4">19. Contact Information</h2>
                <p>
                  If you have any questions about these Terms, please contact us at:
                </p>
                <div className="mt-4 p-4 bg-[--panel] rounded-lg border border-white/10">
                  <p className="font-semibold text-[--text]">Impact Radar</p>
                  <p>Email: support@impactradar.co</p>
                  <p>Website: https://impactradar.co</p>
                </div>
              </section>
            </div>
          </div>
        </div>
      </main>
      <Footer />
    </div>
  );
}

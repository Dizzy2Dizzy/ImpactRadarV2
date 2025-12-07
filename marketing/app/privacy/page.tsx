import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";

export const metadata = {
  title: "Privacy Policy | Impact Radar",
  description: "Privacy Policy for Impact Radar - How we collect, use, and protect your data",
};

export default function PrivacyPage() {
  return (
    <div className="min-h-screen bg-[--background]">
      <Header />
      <main className="py-16 lg:py-24">
        <div className="mx-auto max-w-4xl px-6 lg:px-8">
          <div className="text-center mb-12">
            <h1 className="text-4xl font-semibold tracking-tight text-[--text]">
              Privacy Policy
            </h1>
            <p className="mt-4 text-[--muted]">
              Last updated: November 18, 2025
            </p>
          </div>

          <div className="prose prose-invert max-w-none">
            <div className="space-y-8 text-[--muted]">
              <section>
                <h2 className="text-2xl font-semibold text-[--text] mb-4">1. Introduction</h2>
                <p>
                  Impact Radar ("we," "our," or "us") respects your privacy and is committed to protecting your personal data. This Privacy Policy explains how we collect, use, disclose, and safeguard your information when you use our service at impactradar.co ("Service").
                </p>
                <p className="mt-4">
                  By using the Service, you consent to the data practices described in this policy. If you do not agree with this policy, please do not use the Service.
                </p>
              </section>

              <section>
                <h2 className="text-2xl font-semibold text-[--text] mb-4">2. Information We Collect</h2>
                
                <h3 className="text-xl font-semibold text-[--text] mt-6 mb-3">2.1 Information You Provide</h3>
                <p>We collect information you provide directly when using our Service:</p>
                <ul className="list-disc pl-6 mt-4 space-y-2">
                  <li><strong>Account Information:</strong> Email address, password (hashed), name, and profile information</li>
                  <li><strong>Payment Information:</strong> Billing details processed through Stripe (we do not store credit card numbers)</li>
                  <li><strong>Watchlist Data:</strong> Companies and tickers you track</li>
                  <li><strong>Custom Preferences:</strong> Alert criteria, scoring weights, and custom configurations</li>
                  <li><strong>Communications:</strong> Messages you send to our support team</li>
                  <li><strong>Portfolio Data:</strong> Holdings data you upload for risk analysis (if using portfolio features)</li>
                </ul>

                <h3 className="text-xl font-semibold text-[--text] mt-6 mb-3">2.2 Information Collected Automatically</h3>
                <p>When you access the Service, we automatically collect certain information:</p>
                <ul className="list-disc pl-6 mt-4 space-y-2">
                  <li><strong>Usage Data:</strong> Pages viewed, features used, time spent, and interaction patterns</li>
                  <li><strong>Device Information:</strong> Browser type, operating system, device type, and screen resolution</li>
                  <li><strong>Log Data:</strong> IP address, access times, and error logs</li>
                  <li><strong>Cookies and Tracking:</strong> Session cookies, preference cookies, and analytics cookies</li>
                  <li><strong>API Usage:</strong> API endpoints called, request frequency, and response times (for Pro/Enterprise users)</li>
                </ul>

                <h3 className="text-xl font-semibold text-[--text] mt-6 mb-3">2.3 Information from Third Parties</h3>
                <ul className="list-disc pl-6 mt-4 space-y-2">
                  <li><strong>Payment Processors:</strong> Transaction information from Stripe</li>
                  <li><strong>Authentication Providers:</strong> Information from social login providers (if enabled)</li>
                  <li><strong>Analytics Services:</strong> Aggregated usage data from analytics tools</li>
                </ul>
              </section>

              <section>
                <h2 className="text-2xl font-semibold text-[--text] mb-4">3. How We Use Your Information</h2>
                <p>We use the collected information for the following purposes:</p>
                
                <h3 className="text-xl font-semibold text-[--text] mt-6 mb-3">3.1 Service Delivery</h3>
                <ul className="list-disc pl-6 mt-4 space-y-2">
                  <li>Provide, operate, and maintain the Service</li>
                  <li>Process your transactions and send transaction notifications</li>
                  <li>Deliver personalized event alerts based on your watchlist</li>
                  <li>Generate impact scores and analytics based on your preferences</li>
                  <li>Provide customer support and respond to inquiries</li>
                </ul>

                <h3 className="text-xl font-semibold text-[--text] mt-6 mb-3">3.2 Service Improvement</h3>
                <ul className="list-disc pl-6 mt-4 space-y-2">
                  <li>Understand and analyze usage patterns</li>
                  <li>Develop new features and functionality</li>
                  <li>Improve our machine learning models and impact scoring algorithms</li>
                  <li>Debug and fix technical issues</li>
                  <li>Conduct research and analytics</li>
                </ul>

                <h3 className="text-xl font-semibold text-[--text] mt-6 mb-3">3.3 Communication</h3>
                <ul className="list-disc pl-6 mt-4 space-y-2">
                  <li>Send account-related emails (verification, password reset, billing)</li>
                  <li>Send event alerts and notifications you've configured</li>
                  <li>Send service updates and announcements</li>
                  <li>Send marketing communications (with your consent, you can opt out)</li>
                  <li>Respond to your comments and questions</li>
                </ul>

                <h3 className="text-xl font-semibold text-[--text] mt-6 mb-3">3.4 Security and Compliance</h3>
                <ul className="list-disc pl-6 mt-4 space-y-2">
                  <li>Detect, prevent, and address fraud and security issues</li>
                  <li>Enforce our Terms of Service</li>
                  <li>Comply with legal obligations</li>
                  <li>Protect our rights and property</li>
                </ul>
              </section>

              <section>
                <h2 className="text-2xl font-semibold text-[--text] mb-4">4. Data Sharing and Disclosure</h2>
                <p>We do not sell your personal information. We may share your information in the following circumstances:</p>

                <h3 className="text-xl font-semibold text-[--text] mt-6 mb-3">4.1 Service Providers</h3>
                <p>We share data with third-party vendors who perform services on our behalf:</p>
                <ul className="list-disc pl-6 mt-4 space-y-2">
                  <li><strong>Payment Processing:</strong> Stripe (for billing and payment processing)</li>
                  <li><strong>Email Services:</strong> Resend (for transactional and alert emails)</li>
                  <li><strong>Cloud Hosting:</strong> Replit and database providers (for data storage and hosting)</li>
                  <li><strong>Analytics:</strong> Analytics platforms (for usage tracking and insights)</li>
                  <li><strong>Error Tracking:</strong> Sentry (for monitoring and debugging)</li>
                </ul>

                <h3 className="text-xl font-semibold text-[--text] mt-6 mb-3">4.2 Legal Requirements</h3>
                <p>We may disclose your information if required to do so by law or in response to:</p>
                <ul className="list-disc pl-6 mt-4 space-y-2">
                  <li>Valid legal processes (subpoenas, court orders)</li>
                  <li>Government or regulatory requests</li>
                  <li>Protection of our rights, property, or safety</li>
                  <li>Prevention of fraud or security issues</li>
                </ul>

                <h3 className="text-xl font-semibold text-[--text] mt-6 mb-3">4.3 Business Transfers</h3>
                <p>
                  In the event of a merger, acquisition, sale, or other business transaction, your information may be transferred to the acquiring entity. We will notify you of such transfer and any choices you may have.
                </p>

                <h3 className="text-xl font-semibold text-[--text] mt-6 mb-3">4.4 Aggregated Data</h3>
                <p>
                  We may share aggregated, anonymized data that does not identify you personally. For example, we might share statistics about overall platform usage or popular watchlist tickers.
                </p>
              </section>

              <section>
                <h2 className="text-2xl font-semibold text-[--text] mb-4">5. Data Security</h2>
                <p>We implement appropriate technical and organizational measures to protect your personal information:</p>
                <ul className="list-disc pl-6 mt-4 space-y-2">
                  <li><strong>Encryption:</strong> Data in transit is encrypted using TLS/SSL. Sensitive data at rest is encrypted.</li>
                  <li><strong>Access Controls:</strong> Strict access controls limit who can access your data</li>
                  <li><strong>Password Security:</strong> Passwords are hashed using bcrypt</li>
                  <li><strong>Regular Audits:</strong> Security reviews and vulnerability assessments</li>
                  <li><strong>Monitoring:</strong> Continuous monitoring for suspicious activity</li>
                </ul>
                <p className="mt-4">
                  However, no method of transmission over the Internet or electronic storage is 100% secure. We cannot guarantee absolute security of your data.
                </p>
              </section>

              <section>
                <h2 className="text-2xl font-semibold text-[--text] mb-4">6. Data Retention</h2>
                <p>We retain your personal information for as long as necessary to:</p>
                <ul className="list-disc pl-6 mt-4 space-y-2">
                  <li>Provide the Service to you</li>
                  <li>Comply with legal obligations</li>
                  <li>Resolve disputes and enforce agreements</li>
                  <li>Maintain business records</li>
                </ul>
                <p className="mt-4">
                  When you delete your account, we will delete or anonymize your personal information within 90 days, except for data we are required to retain for legal, tax, or regulatory purposes.
                </p>
              </section>

              <section>
                <h2 className="text-2xl font-semibold text-[--text] mb-4">7. Your Rights and Choices</h2>
                
                <h3 className="text-xl font-semibold text-[--text] mt-6 mb-3">7.1 Access and Portability</h3>
                <p>
                  You have the right to access your personal data and request a copy in a structured, machine-readable format. You can export your data from your account settings or contact us at privacy@impactradar.co.
                </p>

                <h3 className="text-xl font-semibold text-[--text] mt-6 mb-3">7.2 Correction</h3>
                <p>
                  You can update your account information at any time through your account settings. If you need assistance, contact us at support@impactradar.co.
                </p>

                <h3 className="text-xl font-semibold text-[--text] mt-6 mb-3">7.3 Deletion</h3>
                <p>
                  You can delete your account at any time through your account settings. This will permanently delete your personal information, subject to legal retention requirements.
                </p>

                <h3 className="text-xl font-semibold text-[--text] mt-6 mb-3">7.4 Opt-Out of Marketing</h3>
                <p>
                  You can opt out of marketing emails by clicking "unsubscribe" in any marketing email or updating your preferences in account settings. Note that you will still receive transactional emails (alerts, billing notifications).
                </p>

                <h3 className="text-xl font-semibold text-[--text] mt-6 mb-3">7.5 Cookie Preferences</h3>
                <p>
                  You can control cookies through your browser settings. Note that disabling cookies may affect Service functionality.
                </p>

                <h3 className="text-xl font-semibold text-[--text] mt-6 mb-3">7.6 Do Not Track</h3>
                <p>
                  Our Service does not respond to Do Not Track (DNT) signals. You can manage tracking preferences through cookie settings.
                </p>
              </section>

              <section>
                <h2 className="text-2xl font-semibold text-[--text] mb-4">8. GDPR Rights (European Users)</h2>
                <p>If you are in the European Economic Area (EEA), you have additional rights under GDPR:</p>
                <ul className="list-disc pl-6 mt-4 space-y-2">
                  <li><strong>Right to Access:</strong> Request a copy of your personal data</li>
                  <li><strong>Right to Rectification:</strong> Correct inaccurate data</li>
                  <li><strong>Right to Erasure:</strong> Request deletion of your data</li>
                  <li><strong>Right to Restrict Processing:</strong> Limit how we use your data</li>
                  <li><strong>Right to Data Portability:</strong> Receive your data in a portable format</li>
                  <li><strong>Right to Object:</strong> Object to certain processing activities</li>
                  <li><strong>Right to Withdraw Consent:</strong> Withdraw consent for data processing</li>
                  <li><strong>Right to Lodge a Complaint:</strong> File a complaint with your local data protection authority</li>
                </ul>
                <p className="mt-4">
                  To exercise these rights, contact us at privacy@impactradar.co. We will respond within 30 days.
                </p>
              </section>

              <section>
                <h2 className="text-2xl font-semibold text-[--text] mb-4">9. CCPA Rights (California Users)</h2>
                <p>If you are a California resident, you have rights under the California Consumer Privacy Act (CCPA):</p>
                <ul className="list-disc pl-6 mt-4 space-y-2">
                  <li><strong>Right to Know:</strong> Request disclosure of data collected and how it's used</li>
                  <li><strong>Right to Delete:</strong> Request deletion of your personal information</li>
                  <li><strong>Right to Opt-Out:</strong> Opt out of sale of personal information (note: we do not sell your data)</li>
                  <li><strong>Right to Non-Discrimination:</strong> Not be discriminated against for exercising CCPA rights</li>
                </ul>
                <p className="mt-4">
                  To exercise these rights, contact us at privacy@impactradar.co or call 1-800-XXX-XXXX (toll-free).
                </p>
              </section>

              <section>
                <h2 className="text-2xl font-semibold text-[--text] mb-4">10. Cookies and Tracking Technologies</h2>
                <p>We use cookies and similar technologies to provide and improve the Service:</p>
                
                <h3 className="text-xl font-semibold text-[--text] mt-6 mb-3">10.1 Essential Cookies</h3>
                <p>Required for the Service to function (authentication, security, preferences)</p>

                <h3 className="text-xl font-semibold text-[--text] mt-6 mb-3">10.2 Analytics Cookies</h3>
                <p>Help us understand how users interact with the Service</p>

                <h3 className="text-xl font-semibold text-[--text] mt-6 mb-3">10.3 Preference Cookies</h3>
                <p>Remember your settings and preferences</p>

                <p className="mt-4">
                  You can manage cookie preferences through our cookie consent banner or your browser settings.
                </p>
              </section>

              <section>
                <h2 className="text-2xl font-semibold text-[--text] mb-4">11. Children's Privacy</h2>
                <p>
                  The Service is not intended for users under the age of 18. We do not knowingly collect personal information from children under 18. If we discover that we have collected information from a child under 18, we will delete it immediately.
                </p>
                <p className="mt-4">
                  If you believe we have collected information from a child, please contact us at privacy@impactradar.co.
                </p>
              </section>

              <section>
                <h2 className="text-2xl font-semibold text-[--text] mb-4">12. International Data Transfers</h2>
                <p>
                  Your information may be transferred to and processed in countries other than your country of residence. These countries may have different data protection laws.
                </p>
                <p className="mt-4">
                  We ensure appropriate safeguards are in place for international transfers, including Standard Contractual Clauses approved by the European Commission.
                </p>
              </section>

              <section>
                <h2 className="text-2xl font-semibold text-[--text] mb-4">13. Third-Party Links</h2>
                <p>
                  The Service may contain links to third-party websites (source links to SEC, FDA, etc.). We are not responsible for the privacy practices of these websites. We encourage you to review their privacy policies.
                </p>
              </section>

              <section>
                <h2 className="text-2xl font-semibold text-[--text] mb-4">14. Changes to This Privacy Policy</h2>
                <p>
                  We may update this Privacy Policy from time to time. We will notify you of material changes by:
                </p>
                <ul className="list-disc pl-6 mt-4 space-y-2">
                  <li>Posting the updated policy on this page</li>
                  <li>Updating the "Last updated" date</li>
                  <li>Sending an email notification for material changes</li>
                </ul>
                <p className="mt-4">
                  Your continued use of the Service after changes constitutes acceptance of the updated policy.
                </p>
              </section>

              <section>
                <h2 className="text-2xl font-semibold text-[--text] mb-4">15. Contact Us</h2>
                <p>
                  If you have questions about this Privacy Policy or our data practices, please contact us:
                </p>
                <div className="mt-4 p-4 bg-[--panel] rounded-lg border border-white/10">
                  <p className="font-semibold text-[--text]">Impact Radar - Privacy Team</p>
                  <p>Email: privacy@impactradar.co</p>
                  <p>Support: support@impactradar.co</p>
                  <p>Website: https://impactradar.co</p>
                </div>
              </section>

              <section className="mt-12 p-6 bg-blue-500/10 border border-blue-500/20 rounded-lg">
                <h2 className="text-xl font-semibold text-[--text] mb-4">Your Privacy Matters</h2>
                <p>
                  We are committed to transparency and protecting your privacy. If you have any concerns or questions about how we handle your data, please don't hesitate to reach out to our privacy team at privacy@impactradar.co.
                </p>
              </section>
            </div>
          </div>
        </div>
      </main>
      <Footer />
    </div>
  );
}

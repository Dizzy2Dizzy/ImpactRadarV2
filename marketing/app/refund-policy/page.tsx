import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";

export const metadata = {
  title: "Refund & Cancellation Policy | Impact Radar",
  description: "Refund and cancellation policy for Impact Radar subscriptions",
};

export default function RefundPolicyPage() {
  return (
    <div className="min-h-screen bg-[--background]">
      <Header />
      <main className="py-16 lg:py-24">
        <div className="mx-auto max-w-4xl px-6 lg:px-8">
          <div className="text-center mb-12">
            <h1 className="text-4xl font-semibold tracking-tight text-[--text]">
              Refund & Cancellation Policy
            </h1>
            <p className="mt-4 text-[--muted]">
              Last updated: November 18, 2025
            </p>
          </div>

          <div className="prose prose-invert max-w-none">
            <div className="space-y-8 text-[--muted]">
              <section>
                <h2 className="text-2xl font-semibold text-[--text] mb-4">1. Cancellation Policy</h2>
                
                <h3 className="text-xl font-semibold text-[--text] mt-6 mb-3">1.1 How to Cancel</h3>
                <p>
                  You may cancel your Impact Radar subscription at any time through your account settings:
                </p>
                <ul className="list-disc pl-6 mt-4 space-y-2">
                  <li>Log in to your account at impactradar.co</li>
                  <li>Navigate to Account Settings → Subscription</li>
                  <li>Click "Cancel Subscription"</li>
                  <li>Confirm your cancellation</li>
                </ul>
                <p className="mt-4">
                  Alternatively, you can email support@impactradar.co to request cancellation.
                </p>

                <h3 className="text-xl font-semibold text-[--text] mt-6 mb-3">1.2 When Cancellation Takes Effect</h3>
                <p>
                  When you cancel your subscription:
                </p>
                <ul className="list-disc pl-6 mt-4 space-y-2">
                  <li>Your cancellation is effective at the end of your current billing period</li>
                  <li>You will retain access to paid features until the end of your billing period</li>
                  <li>You will not be charged for subsequent billing periods</li>
                  <li>Your account will automatically downgrade to the Free plan</li>
                </ul>

                <h3 className="text-xl font-semibold text-[--text] mt-6 mb-3">1.3 After Cancellation</h3>
                <p>
                  After your subscription ends:
                </p>
                <ul className="list-disc pl-6 mt-4 space-y-2">
                  <li>Your watchlist data will be preserved (limited to Free plan limits)</li>
                  <li>Premium features (backtesting, correlation, API access, etc.) will be locked</li>
                  <li>Alert configurations will be preserved but may be disabled if they exceed Free plan limits</li>
                  <li>You can resubscribe at any time to regain access to premium features</li>
                </ul>
              </section>

              <section>
                <h2 className="text-2xl font-semibold text-[--text] mb-4">2. Free Trial Cancellation</h2>
                <p>
                  If you cancel during your free trial period:
                </p>
                <ul className="list-disc pl-6 mt-4 space-y-2">
                  <li>You will not be charged when the trial ends</li>
                  <li>Your account will automatically convert to a Free plan</li>
                  <li>You must cancel before the trial ends to avoid being charged</li>
                  <li>Trial cancellation is effective immediately</li>
                </ul>
              </section>

              <section>
                <h2 className="text-2xl font-semibold text-[--text] mb-4">3. Refund Policy</h2>
                
                <h3 className="text-xl font-semibold text-[--text] mt-6 mb-3">3.1 General Refund Policy</h3>
                <p>
                  All subscription fees are generally non-refundable, except as described in the specific circumstances below. By subscribing to Impact Radar, you agree that:
                </p>
                <ul className="list-disc pl-6 mt-4 space-y-2">
                  <li>Monthly subscriptions are non-refundable</li>
                  <li>Annual subscriptions are non-refundable after 14 days</li>
                  <li>Partial refunds for unused time are not provided</li>
                </ul>

                <h3 className="text-xl font-semibold text-[--text] mt-6 mb-3">3.2 14-Day Money-Back Guarantee (Annual Plans Only)</h3>
                <p>
                  For annual subscriptions, we offer a 14-day money-back guarantee:
                </p>
                <ul className="list-disc pl-6 mt-4 space-y-2">
                  <li>You may request a full refund within 14 days of your initial annual subscription purchase</li>
                  <li>This applies only to first-time annual subscribers</li>
                  <li>The guarantee does not apply to renewal charges</li>
                  <li>To request a refund, email support@impactradar.co with your account email and reason</li>
                </ul>

                <h3 className="text-xl font-semibold text-[--text] mt-6 mb-3">3.3 Billing Errors</h3>
                <p>
                  If you believe you have been charged in error, please contact us immediately at billing@impactradar.co. We will investigate and issue a refund if the charge was indeed made in error.
                </p>

                <h3 className="text-xl font-semibold text-[--text] mt-6 mb-3">3.4 Service Outages</h3>
                <p>
                  If the Service experiences extended downtime (more than 24 consecutive hours) due to our fault, Pro and Enterprise users may be eligible for a prorated credit. Contact support@impactradar.co to request a service credit.
                </p>

                <h3 className="text-xl font-semibold text-[--text] mt-6 mb-3">3.5 Account Termination by Impact Radar</h3>
                <p>
                  If we terminate your account for violation of our Terms of Service, you are not entitled to a refund of any fees already paid.
                </p>
                <p className="mt-4">
                  If we terminate your account for reasons other than Terms violations, or if we discontinue the Service, you will receive a prorated refund for the unused portion of your subscription.
                </p>
              </section>

              <section>
                <h2 className="text-2xl font-semibold text-[--text] mb-4">4. Downgrades and Plan Changes</h2>
                
                <h3 className="text-xl font-semibold text-[--text] mt-6 mb-3">4.1 Upgrading Your Plan</h3>
                <p>
                  When you upgrade from a lower plan to a higher plan:
                </p>
                <ul className="list-disc pl-6 mt-4 space-y-2">
                  <li>The upgrade takes effect immediately</li>
                  <li>You are charged a prorated amount for the remainder of your billing cycle</li>
                  <li>Your next full billing cycle will be at the new plan rate</li>
                </ul>

                <h3 className="text-xl font-semibold text-[--text] mt-6 mb-3">4.2 Downgrading Your Plan</h3>
                <p>
                  When you downgrade from a higher plan to a lower plan:
                </p>
                <ul className="list-disc pl-6 mt-4 space-y-2">
                  <li>The downgrade takes effect at the end of your current billing period</li>
                  <li>You will not receive a refund for the difference</li>
                  <li>You will retain access to premium features until the end of your billing period</li>
                  <li>Features that exceed the lower plan's limits will be disabled after downgrade</li>
                </ul>

                <h3 className="text-xl font-semibold text-[--text] mt-6 mb-3">4.3 Switching Between Monthly and Annual</h3>
                <p>
                  To switch between monthly and annual billing:
                </p>
                <ul className="list-disc pl-6 mt-4 space-y-2">
                  <li>Cancel your current subscription</li>
                  <li>Wait for the current billing period to end</li>
                  <li>Subscribe to the desired billing frequency</li>
                  <li>No refunds are provided for the time remaining on your current plan</li>
                </ul>
              </section>

              <section>
                <h2 className="text-2xl font-semibold text-[--text] mb-4">5. Failed Payments</h2>
                
                <h3 className="text-xl font-semibold text-[--text] mt-6 mb-3">5.1 Payment Failures</h3>
                <p>
                  If your payment method fails during a renewal:
                </p>
                <ul className="list-disc pl-6 mt-4 space-y-2">
                  <li>We will attempt to charge your payment method up to 3 times over 7 days</li>
                  <li>You will receive email notifications about the failed payment</li>
                  <li>Your account will remain active during the retry period</li>
                  <li>If all retries fail, your subscription will be cancelled and your account will downgrade to Free</li>
                </ul>

                <h3 className="text-xl font-semibold text-[--text] mt-6 mb-3">5.2 Updating Payment Information</h3>
                <p>
                  You can update your payment method at any time in your account settings to prevent payment failures.
                </p>
              </section>

              <section>
                <h2 className="text-2xl font-semibold text-[--text] mb-4">6. Chargebacks and Disputes</h2>
                <p>
                  If you initiate a chargeback or payment dispute with your credit card company or payment provider:
                </p>
                <ul className="list-disc pl-6 mt-4 space-y-2">
                  <li>Your account will be immediately suspended pending resolution</li>
                  <li>We encourage you to contact us first at billing@impactradar.co to resolve billing issues</li>
                  <li>Fraudulent chargebacks may result in permanent account termination</li>
                  <li>You may be liable for chargeback fees and collection costs</li>
                </ul>
              </section>

              <section>
                <h2 className="text-2xl font-semibold text-[--text] mb-4">7. Enterprise Subscriptions</h2>
                <p>
                  Enterprise subscriptions may have custom terms, including:
                </p>
                <ul className="list-disc pl-6 mt-4 space-y-2">
                  <li>Custom contract lengths</li>
                  <li>Different cancellation notice periods</li>
                  <li>Custom refund policies</li>
                  <li>Minimum commitment periods</li>
                </ul>
                <p className="mt-4">
                  Enterprise customers should refer to their signed agreement for specific terms. If you have questions about your Enterprise subscription, contact your account manager or enterprise@impactradar.co.
                </p>
              </section>

              <section>
                <h2 className="text-2xl font-semibold text-[--text] mb-4">8. Taxes</h2>
                <p>
                  All prices are exclusive of applicable taxes unless otherwise stated. You are responsible for:
                </p>
                <ul className="list-disc pl-6 mt-4 space-y-2">
                  <li>Any sales tax, VAT, GST, or other taxes required by your jurisdiction</li>
                  <li>Providing accurate billing information for tax purposes</li>
                  <li>Paying any additional taxes that may apply to your subscription</li>
                </ul>
                <p className="mt-4">
                  Taxes are generally non-refundable, even if you receive a refund for your subscription fees.
                </p>
              </section>

              <section>
                <h2 className="text-2xl font-semibold text-[--text] mb-4">9. Refund Processing</h2>
                
                <h3 className="text-xl font-semibold text-[--text] mt-6 mb-3">9.1 How to Request a Refund</h3>
                <p>
                  To request a refund (if eligible):
                </p>
                <ol className="list-decimal pl-6 mt-4 space-y-2">
                  <li>Email support@impactradar.co or billing@impactradar.co</li>
                  <li>Include your account email address</li>
                  <li>Provide your reason for the refund request</li>
                  <li>Include any relevant transaction details</li>
                </ol>

                <h3 className="text-xl font-semibold text-[--text] mt-6 mb-3">9.2 Refund Timeline</h3>
                <p>
                  If your refund request is approved:
                </p>
                <ul className="list-disc pl-6 mt-4 space-y-2">
                  <li>We will process your refund within 5-7 business days</li>
                  <li>Refunds are issued to the original payment method</li>
                  <li>Depending on your payment provider, it may take 5-10 business days for the refund to appear in your account</li>
                  <li>You will receive a confirmation email when the refund is processed</li>
                </ul>
              </section>

              <section>
                <h2 className="text-2xl font-semibold text-[--text] mb-4">10. Questions and Support</h2>
                <p>
                  If you have questions about our refund or cancellation policy, please contact us:
                </p>
                <div className="mt-4 p-4 bg-[--panel] rounded-lg border border-white/10">
                  <p className="font-semibold text-[--text]">Impact Radar - Billing Team</p>
                  <p>Email: billing@impactradar.co</p>
                  <p>Support: support@impactradar.co</p>
                  <p>Website: https://impactradar.co</p>
                </div>
              </section>

              <section className="mt-12 p-6 bg-blue-500/10 border border-blue-500/20 rounded-lg">
                <h2 className="text-xl font-semibold text-[--text] mb-4">Summary</h2>
                <ul className="space-y-2">
                  <li>✓ Cancel anytime through account settings</li>
                  <li>✓ Access continues until end of billing period</li>
                  <li>✓ 14-day money-back guarantee for annual plans</li>
                  <li>✓ Monthly subscriptions are non-refundable</li>
                  <li>✓ Free trial can be cancelled before it ends to avoid charges</li>
                </ul>
              </section>
            </div>
          </div>
        </div>
      </main>
      <Footer />
    </div>
  );
}

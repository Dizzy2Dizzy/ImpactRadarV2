import { Metadata } from "next";
import Link from "next/link";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import { DollarSign, Users, TrendingUp, Zap, CheckCircle, ArrowRight } from "lucide-react";

export const metadata: Metadata = {
  title: "Affiliate Program | Impact Radar - Earn 30% Recurring Commissions",
  description:
    "Join the Impact Radar affiliate program and earn 30% recurring commissions on every referral. Perfect for trading educators, financial bloggers, and market analysts.",
};

export default function AffiliatePage() {
  return (
    <div className="min-h-screen bg-[--background]">
      <Header />
      <main className="pt-24 pb-16">
        <div className="max-w-7xl mx-auto px-6 lg:px-8">
          {/* Hero Section */}
          <div className="text-center mb-16">
            <div className="inline-flex items-center gap-2 rounded-full bg-[--primary]/10 px-4 py-2 text-sm font-medium text-[--primary] mb-6">
              <Zap className="h-4 w-4" />
              30% Recurring Commission
            </div>
            <h1 className="text-4xl md:text-6xl font-bold text-[--text] mb-4">
              Earn with <span className="text-[--primary]">Impact Radar</span>
            </h1>
            <p className="text-lg text-[--muted] max-w-2xl mx-auto mb-8">
              Promote the leading event-driven signal engine and earn generous recurring
              commissions for every trader you refer.
            </p>
            <Link
              href="/affiliate/apply"
              className="inline-flex items-center gap-2 rounded-lg bg-[--primary] px-8 py-4 text-lg font-semibold text-black hover:bg-[--primary]/90 transition-colors"
            >
              Apply to Join Program
              <ArrowRight className="h-5 w-5" />
            </Link>
          </div>

          {/* Stats */}
          <div className="grid gap-6 md:grid-cols-3 mb-16">
            <div className="rounded-2xl border border-white/10 bg-[--panel] p-8 text-center">
              <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-[--primary]/10 text-[--primary] mb-4">
                <DollarSign className="h-8 w-8" />
              </div>
              <div className="text-4xl font-bold text-[--text] mb-2">30%</div>
              <p className="text-[--muted]">Recurring Commission</p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-[--panel] p-8 text-center">
              <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-[--primary]/10 text-[--primary] mb-4">
                <Users className="h-8 w-8" />
              </div>
              <div className="text-4xl font-bold text-[--text] mb-2">90 Days</div>
              <p className="text-[--muted]">Cookie Duration</p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-[--panel] p-8 text-center">
              <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-[--primary]/10 text-[--primary] mb-4">
                <TrendingUp className="h-8 w-8" />
              </div>
              <div className="text-4xl font-bold text-[--text] mb-2">$14.70</div>
              <p className="text-[--muted]">Avg. Commission/User</p>
            </div>
          </div>

          {/* Why Join */}
          <div className="mb-16">
            <h2 className="text-3xl font-bold text-[--text] mb-8 text-center">
              Why Join Our Affiliate Program?
            </h2>
            <div className="grid gap-6 md:grid-cols-2">
              {[
                {
                  title: "Recurring Revenue",
                  description:
                    "Earn 30% commission every month as long as your referrals remain subscribed. One referral can generate $14.70/month in passive income.",
                },
                {
                  title: "Premium Product",
                  description:
                    "Promote a professional tool that traders actually need. 1,490+ validated events, ML predictions, and real-time alerts sell themselves.",
                },
                {
                  title: "High Conversion Rate",
                  description:
                    "Our 7-day free trial and live demo convert browsers into paying customers. You bring the traffic, we handle the conversion.",
                },
                {
                  title: "Marketing Materials",
                  description:
                    "Access pre-made banners, email templates, and landing pages. Copy-paste promotional content that's proven to convert.",
                },
                {
                  title: "Real-Time Dashboard",
                  description:
                    "Track clicks, signups, conversions, and earnings in real-time. Know exactly how much you're making from each referral source.",
                },
                {
                  title: "Monthly Payouts",
                  description:
                    "Get paid on the 1st of every month via Stripe, PayPal, or bank transfer. Minimum payout threshold is just $50.",
                },
              ].map((item, i) => (
                <div
                  key={i}
                  className="rounded-xl border border-white/10 bg-[--panel] p-6"
                >
                  <div className="flex items-start gap-3">
                    <CheckCircle className="h-6 w-6 text-[--primary] mt-1 flex-shrink-0" />
                    <div>
                      <h3 className="text-lg font-semibold text-[--text] mb-2">
                        {item.title}
                      </h3>
                      <p className="text-[--muted] text-sm">{item.description}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Who Should Join */}
          <div className="mb-16">
            <h2 className="text-3xl font-bold text-[--text] mb-8 text-center">
              Perfect For
            </h2>
            <div className="grid gap-6 md:grid-cols-4">
              {[
                {
                  title: "Trading Educators",
                  description:
                    "Recommend Impact Radar to your students and course members.",
                },
                {
                  title: "Financial Bloggers",
                  description:
                    "Write reviews and tutorials featuring Impact Radar's capabilities.",
                },
                {
                  title: "YouTube Creators",
                  description:
                    "Showcase Impact Radar in trading videos and strategy breakdowns.",
                },
                {
                  title: "Discord Communities",
                  description:
                    "Share your affiliate link with your trading community members.",
                },
              ].map((item, i) => (
                <div
                  key={i}
                  className="rounded-xl border border-white/10 bg-[--panel] p-6 text-center"
                >
                  <h3 className="text-lg font-semibold text-[--text] mb-2">
                    {item.title}
                  </h3>
                  <p className="text-sm text-[--muted]">{item.description}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Commission Breakdown */}
          <div className="mb-16 rounded-2xl border border-white/10 bg-[--panel] p-8">
            <h2 className="text-2xl font-bold text-[--text] mb-6 text-center">
              Commission Breakdown
            </h2>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-white/10">
                    <th className="text-left py-3 px-4 text-[--text] font-semibold">
                      Plan
                    </th>
                    <th className="text-left py-3 px-4 text-[--text] font-semibold">
                      Price
                    </th>
                    <th className="text-left py-3 px-4 text-[--text] font-semibold">
                      Your Commission (30%)
                    </th>
                    <th className="text-left py-3 px-4 text-[--text] font-semibold">
                      Annual Value
                    </th>
                  </tr>
                </thead>
                <tbody>
                  <tr className="border-b border-white/10">
                    <td className="py-3 px-4 text-[--text]">Pro</td>
                    <td className="py-3 px-4 text-[--muted]">$49/mo</td>
                    <td className="py-3 px-4 text-[--primary] font-semibold">
                      $14.70/mo
                    </td>
                    <td className="py-3 px-4 text-[--muted]">$176.40/year</td>
                  </tr>
                  <tr>
                    <td className="py-3 px-4 text-[--text]">Team</td>
                    <td className="py-3 px-4 text-[--muted]">$199/mo</td>
                    <td className="py-3 px-4 text-[--primary] font-semibold">
                      $59.70/mo
                    </td>
                    <td className="py-3 px-4 text-[--muted]">$716.40/year</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <p className="text-sm text-[--muted] mt-6 text-center">
              Commissions paid monthly for as long as your referral remains a paying
              customer
            </p>
          </div>

          {/* CTA */}
          <div className="text-center">
            <div className="rounded-2xl border border-white/10 bg-gradient-to-br from-[--primary]/10 to-blue-600/10 p-12">
              <h2 className="text-3xl font-bold text-[--text] mb-4">
                Ready to Start Earning?
              </h2>
              <p className="text-lg text-[--muted] mb-8 max-w-2xl mx-auto">
                Join hundreds of affiliates earning recurring commissions by promoting
                the best event-driven trading platform.
              </p>
              <Link
                href="/affiliate/apply"
                className="inline-flex items-center gap-2 rounded-lg bg-[--primary] px-8 py-4 text-lg font-semibold text-black hover:bg-[--primary]/90 transition-colors"
              >
                Apply Now - It's Free
                <ArrowRight className="h-5 w-5" />
              </Link>
            </div>
          </div>
        </div>
      </main>
      <Footer />
    </div>
  );
}

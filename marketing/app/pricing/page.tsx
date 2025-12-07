import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import { Plans } from "@/components/pricing/Plans";
import { Comparison } from "@/components/pricing/Comparison";
import { plans, comparisonFeatures } from "@/data/plans";

const faqs = [
  {
    question: "What payment methods do you accept?",
    answer:
      "We accept all major credit cards (Visa, MasterCard, Amex) through Stripe. Enterprise customers can also pay via invoice.",
  },
  {
    question: "Can I change my plan later?",
    answer:
      "Yes! You can upgrade or downgrade your plan at any time. Changes take effect immediately, with prorated billing.",
  },
  {
    question: "Is there a free trial?",
    answer:
      "Pro plan includes a 7-day free trial. No credit card required to start.",
  },
  {
    question: "What happens to my data if I cancel?",
    answer:
      "Your data remains accessible for 30 days after cancellation. You can export everything before deletion.",
  },
  {
    question: "Do you offer discounts for nonprofits or students?",
    answer:
      "Yes! We offer 50% discounts for verified nonprofits and students. Contact us for details.",
  },
];

export default function PricingPage() {
  return (
    <div className="min-h-screen">
      <Header />
      <main className="py-16 lg:py-24">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <div className="mx-auto max-w-4xl text-center">
            <h1 className="text-4xl md:text-6xl font-semibold tracking-tight text-[--text]">
              Pricing built for{" "}
              <span className="text-[--primary]">traders</span>
            </h1>
            <p className="mt-6 text-lg text-[--muted]">
              Start free. Scale as you grow. No hidden fees, cancel anytime.
            </p>
          </div>

          <div className="mt-16">
            <Plans plans={plans} />
          </div>

          <Comparison features={comparisonFeatures} />

          <div className="mt-24">
            <h2 className="text-3xl font-semibold text-[--text] text-center mb-12">
              Frequently asked questions
            </h2>
            <dl className="mx-auto max-w-3xl space-y-6">
              {faqs.map((faq) => (
                <div
                  key={faq.question}
                  className="rounded-2xl border border-white/10 bg-[--panel] p-6"
                >
                  <dt className="text-base font-semibold text-[--text]">
                    {faq.question}
                  </dt>
                  <dd className="mt-2 text-sm text-[--muted]">{faq.answer}</dd>
                </div>
              ))}
            </dl>
          </div>
        </div>
      </main>
      <Footer />
    </div>
  );
}

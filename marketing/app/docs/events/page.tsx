import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import { ScoreChip } from "@/components/ScoreChip";

const eventTypes = [
  {
    type: "fda_approval",
    name: "FDA Approval",
    impact: "70-95",
    description:
      "FDA drug or device approval. Typically triggers 20-40% upside in biotech stocks.",
  },
  {
    type: "fda_rejection",
    name: "FDA Rejection",
    impact: "70-90",
    description:
      "FDA rejection or complete response letter. Often causes 15-30% selloff.",
  },
  {
    type: "earnings",
    name: "Earnings Report",
    impact: "60-80",
    description:
      "Quarterly earnings announcement. Impact varies by beat/miss magnitude.",
  },
  {
    type: "sec_8k",
    name: "SEC 8-K Filing",
    impact: "65",
    description:
      "Material event disclosure. Can signal M&A, executive changes, or major contracts.",
  },
  {
    type: "sec_10k",
    name: "SEC 10-K Filing",
    impact: "50",
    description: "Annual report. Less immediate impact but important for analysis.",
  },
  {
    type: "product_launch",
    name: "Product Launch",
    impact: "50-65",
    description:
      "New product or service announcement. Impact depends on market expectations.",
  },
];

export default function EventsPage() {
  return (
    <div className="min-h-screen">
      <Header />
      <main className="py-16 lg:py-24">
        <div className="mx-auto max-w-4xl px-6 lg:px-8">
          <h1 className="text-4xl md:text-6xl font-semibold tracking-tight text-[--text] mb-6">
            Event Types & Scoring
          </h1>
          <p className="text-lg text-[--muted] mb-12">
            Understanding how we classify and score market-moving events.
          </p>

          <div className="space-y-6">
            {eventTypes.map((event) => (
              <div
                key={event.type}
                className="rounded-3xl border border-white/10 bg-[--panel] p-6"
              >
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <h2 className="text-xl font-semibold text-[--text] mb-2">
                      {event.name}
                    </h2>
                    <code className="text-sm text-[--muted]">{event.type}</code>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-[--muted]">Impact:</span>
                    <span className="text-sm font-semibold text-[--text]">
                      {event.impact}
                    </span>
                  </div>
                </div>
                <p className="text-[--muted]">{event.description}</p>
              </div>
            ))}
          </div>

          <section className="mt-16 rounded-3xl border border-white/10 bg-[--panel] p-8">
            <h2 className="text-2xl font-semibold text-[--text] mb-6">
              Impact Score Components
            </h2>
            <div className="space-y-4">
              <div>
                <h3 className="text-base font-semibold text-[--text] mb-2">
                  Impact Score (0-100)
                </h3>
                <p className="text-sm text-[--muted]">
                  Numerical magnitude of expected market impact. Higher scores
                  indicate larger potential price movements.
                </p>
              </div>
              <div>
                <h3 className="text-base font-semibold text-[--text] mb-2">
                  Direction
                </h3>
                <p className="text-sm text-[--muted]">
                  Expected price movement: positive (up), negative (down),
                  neutral, or uncertain.
                </p>
              </div>
              <div>
                <h3 className="text-base font-semibold text-[--text] mb-2">
                  Confidence (0.0-1.0)
                </h3>
                <p className="text-sm text-[--muted]">
                  Statistical confidence in the direction and impact estimate.
                  FDA events typically have 0.85+ confidence.
                </p>
              </div>
              <div>
                <h3 className="text-base font-semibold text-[--text] mb-2">
                  Rationale
                </h3>
                <p className="text-sm text-[--muted]">
                  Human-readable explanation of scoring logic with historical
                  context.
                </p>
              </div>
            </div>
          </section>
        </div>
      </main>
      <Footer />
    </div>
  );
}

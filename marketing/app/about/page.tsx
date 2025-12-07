import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import { Target, Users, Zap } from "lucide-react";

export default function AboutPage() {
  return (
    <div className="min-h-screen">
      <Header />
      <main className="py-16 lg:py-24">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <div className="mx-auto max-w-2xl text-center mb-16">
            <h1 className="text-4xl md:text-6xl font-semibold tracking-tight text-[--text]">
              About <span className="text-[--primary]">Impact Radar</span>
            </h1>
            <p className="mt-6 text-lg text-[--muted]">
              Built by traders, for traders. We're on a mission to democratize
              access to market-moving information.
            </p>
          </div>

          <div className="grid gap-12 md:grid-cols-3 mb-16">
            <div className="text-center">
              <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-[--primary]/10 text-[--primary] mb-4">
                <Target className="h-6 w-6" />
              </div>
              <h3 className="text-lg font-semibold text-[--text] mb-2">
                Our Mission
              </h3>
              <p className="text-sm text-[--muted]">
                Level the playing field by providing institutional-grade event
                tracking to active traders and small funds.
              </p>
            </div>

            <div className="text-center">
              <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-[--primary]/10 text-[--primary] mb-4">
                <Users className="h-6 w-6" />
              </div>
              <h3 className="text-lg font-semibold text-[--text] mb-2">
                Our Team
              </h3>
              <p className="text-sm text-[--muted]">
                We are a team of active traders and programmers with years of experience in quantitative and algorithmic trading.
              </p>
            </div>

            <div className="text-center">
              <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-[--primary]/10 text-[--primary] mb-4">
                <Zap className="h-6 w-6" />
              </div>
              <h3 className="text-lg font-semibold text-[--text] mb-2">
                Our Values
              </h3>
              <p className="text-sm text-[--muted]">
                Transparency, accuracy, and speed. We never compromise on data
                quality or user privacy.
              </p>
            </div>
          </div>

          <div className="mx-auto max-w-4xl">
            <div className="rounded-3xl border border-white/10 bg-[--panel] p-8">
              <h2 className="text-2xl font-semibold text-[--text] mb-4">
                Why We Built Impact Radar
              </h2>
              <div className="space-y-4 text-[--muted]">
                <p>
                  As active traders ourselves, we were frustrated by the
                  fragmented landscape of market information. Critical events
                  were buried across SEC filings, FDA announcements, and company
                  press releases, with no unified way to track and score their
                  potential impact.
                </p>
                <p>
                  We built Impact Radar to solve this problem. Our platform
                  aggregates events from multiple authoritative sources,
                  applies deterministic impact scoring, and delivers actionable
                  insights in real-time.
                </p>
                <p>
                  Today, Impact Radar serves hundreds of active traders and
                  small funds, helping them stay ahead of market-moving events
                  and make more informed trading decisions.
                </p>
              </div>
            </div>
          </div>
        </div>
      </main>
      <Footer />
    </div>
  );
}

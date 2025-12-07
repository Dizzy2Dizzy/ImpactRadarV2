import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import { Book, Code, Zap, FileText } from "lucide-react";
import Link from "next/link";

const docs = [
  {
    icon: <Zap className="h-6 w-6" />,
    title: "Quickstart",
    description: "Get up and running in 5 minutes",
    href: "/docs/quickstart",
  },
  {
    icon: <Code className="h-6 w-6" />,
    title: "API Reference",
    description: "Complete API documentation and examples",
    href: "/docs/api",
  },
  {
    icon: <Book className="h-6 w-6" />,
    title: "Event Types",
    description: "Understanding impact scores and event categories",
    href: "/docs/events",
  },
  {
    icon: <FileText className="h-6 w-6" />,
    title: "Changelog",
    description: "Latest updates and release notes",
    href: "/changelog",
  },
];

export default function DocsPage() {
  return (
    <div className="min-h-screen">
      <Header />
      <main className="py-16 lg:py-24">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <div className="mx-auto max-w-2xl text-center">
            <h1 className="text-4xl md:text-6xl font-semibold tracking-tight text-[--text]">
              Documentation
            </h1>
            <p className="mt-6 text-lg text-[--muted]">
              Everything you need to integrate and use Impact Radar.
            </p>
          </div>

          <div className="mt-16 grid gap-8 md:grid-cols-2 lg:grid-cols-4">
            {docs.map((doc) => (
              <Link
                key={doc.title}
                href={doc.href}
                className="group rounded-2xl border border-white/10 bg-[--panel] p-6 hover:border-white/20 transition-all"
              >
                <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-[--primary]/10 text-[--primary] mb-4 group-hover:bg-[--primary]/20 transition-colors">
                  {doc.icon}
                </div>
                <h3 className="text-lg font-semibold text-[--text] mb-2">
                  {doc.title}
                </h3>
                <p className="text-sm text-[--muted]">{doc.description}</p>
              </Link>
            ))}
          </div>

          <div className="mt-24 max-w-4xl mx-auto">
            <div className="rounded-3xl border border-white/10 bg-[--panel] p-8">
              <h2 className="text-2xl font-semibold text-[--text] mb-6">
                Quickstart
              </h2>
              <div className="prose prose-invert max-w-none">
                <p className="text-[--muted]">
                  Get started with Impact Radar in minutes:
                </p>
                <ol className="mt-6 space-y-4 text-[--text]">
                  <li>
                    <strong>Sign up</strong> for a free account at{" "}
                    <Link
                      href="/app"
                      className="text-[--primary] hover:text-[--accent]"
                    >
                      impactradar.co/app
                    </Link>
                  </li>
                  <li>
                    <strong>Add companies</strong> to your watchlist by searching
                    for ticker symbols
                  </li>
                  <li>
                    <strong>Configure alerts</strong> for specific event types or
                    impact scores
                  </li>
                  <li>
                    <strong>Integrate via API</strong> (Pro plan) to pipe events
                    into your own systems
                  </li>
                </ol>
              </div>
            </div>
          </div>
        </div>
      </main>
      <Footer />
    </div>
  );
}

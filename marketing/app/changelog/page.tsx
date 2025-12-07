"use client";

import { useState, useEffect } from "react";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import { CheckCircle2, Zap, Shield, Database, Sparkles, Bug, Settings, Loader2 } from "lucide-react";

interface ChangelogItem {
  id: number;
  category: string;
  description: string;
  icon: string;
}

interface ChangelogRelease {
  id: number;
  version: string;
  title: string;
  release_date: string;
  items: ChangelogItem[];
}

const fallbackReleases = [
  {
    id: 1,
    version: "1.0.0",
    release_date: "2024-11-10",
    title: "Enterprise Refactoring & Marketing Launch",
    items: [
      {
        id: 1,
        icon: "Database",
        category: "Architecture",
        description:
          "Complete enterprise refactoring with modular package structure, SQLAlchemy 2.0, and Alembic migrations",
      },
      {
        id: 2,
        icon: "Shield",
        category: "Security",
        description:
          "Enhanced security with bcrypt hashing, 2FA, and comprehensive PII protection",
      },
      {
        id: 3,
        icon: "Zap",
        category: "Marketing",
        description:
          "Launched Next.js 14 marketing website with Dyad-inspired design and 7 comprehensive pages",
      },
      {
        id: 4,
        icon: "CheckCircle2",
        category: "Testing",
        description:
          "Backward compatibility verified with smoke tests (10/10 passed)",
      },
    ],
  },
  {
    id: 2,
    version: "0.9.0",
    release_date: "2024-11-09",
    title: "Event Type Normalization",
    items: [
      {
        id: 5,
        icon: "Database",
        category: "Data",
        description:
          "Migrated 533 events to canonical type codes and fixed FDA event classification",
      },
      {
        id: 6,
        icon: "Zap",
        category: "Features",
        description: "Added manual scanner capability and portfolio earnings tracking",
      },
    ],
  },
];

const getIconComponent = (iconName: string) => {
  switch (iconName) {
    case "Sparkles":
      return <Sparkles className="h-5 w-5" />;
    case "Zap":
      return <Zap className="h-5 w-5" />;
    case "Bug":
      return <Bug className="h-5 w-5" />;
    case "Shield":
      return <Shield className="h-5 w-5" />;
    case "Settings":
      return <Settings className="h-5 w-5" />;
    case "Database":
      return <Database className="h-5 w-5" />;
    case "CheckCircle2":
    default:
      return <CheckCircle2 className="h-5 w-5" />;
  }
};

const formatDate = (dateStr: string) => {
  try {
    const date = new Date(dateStr);
    return date.toLocaleDateString("en-US", {
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  } catch {
    return dateStr;
  }
};

export default function ChangelogPage() {
  const [releases, setReleases] = useState<ChangelogRelease[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchChangelog = async () => {
      try {
        const response = await fetch("/api/proxy/changelog");
        if (response.ok) {
          const data = await response.json();
          if (data.releases && data.releases.length > 0) {
            setReleases(data.releases);
          } else {
            setReleases(fallbackReleases);
          }
        } else {
          setReleases(fallbackReleases);
        }
      } catch (error) {
        console.error("Failed to fetch changelog:", error);
        setReleases(fallbackReleases);
      } finally {
        setIsLoading(false);
      }
    };

    fetchChangelog();
  }, []);

  return (
    <div className="min-h-screen">
      <Header />
      <main className="py-16 lg:py-24">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <div className="mx-auto max-w-2xl text-center mb-16">
            <h1 className="text-4xl md:text-6xl font-semibold tracking-tight text-[--text]">
              Changelog
            </h1>
            <p className="mt-6 text-lg text-[--muted]">
              Track our progress as we build Impact Radar into the best event
              tracking platform for traders.
            </p>
          </div>

          {isLoading ? (
            <div className="flex items-center justify-center py-16">
              <Loader2 className="h-8 w-8 animate-spin text-[--primary]" />
            </div>
          ) : (
            <div className="mx-auto max-w-4xl space-y-16">
              {releases.map((release) => (
                <div
                  key={release.id}
                  className="rounded-3xl border border-white/10 bg-[--panel] p-8"
                >
                  <div className="flex items-start justify-between mb-6">
                    <div>
                      <h2 className="text-2xl font-semibold text-[--text] mb-2">
                        {release.title}
                      </h2>
                      <div className="flex items-center gap-4 text-sm text-[--muted]">
                        <span className="font-mono text-[--primary]">
                          v{release.version}
                        </span>
                        <span>-</span>
                        <time>{formatDate(release.release_date)}</time>
                      </div>
                    </div>
                  </div>

                  <div className="space-y-4">
                    {release.items.map((item) => (
                      <div
                        key={item.id}
                        className="flex gap-4 p-4 rounded-xl bg-[--bg]/50"
                      >
                        <div className="inline-flex items-center justify-center w-10 h-10 rounded-lg bg-[--primary]/10 text-[--primary] flex-shrink-0">
                          {getIconComponent(item.icon)}
                        </div>
                        <div>
                          <h3 className="text-sm font-semibold text-[--text] mb-1">
                            {item.category}
                          </h3>
                          <p className="text-sm text-[--muted]">
                            {item.description}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>
      <Footer />
    </div>
  );
}

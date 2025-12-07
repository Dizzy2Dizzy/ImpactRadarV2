"use client";

import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import Image from "next/image";
import Link from "next/link";

export default function Hero() {
  return (
    <section className="relative overflow-hidden">
      <div className="mx-auto max-w-7xl px-6 py-24 lg:py-32 grid lg:grid-cols-12 gap-10 items-center">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          whileInView={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35 }}
          viewport={{ once: true }}
          className="lg:col-span-6"
        >
          <h1 className="text-4xl/tight md:text-6xl font-semibold tracking-tight text-[--text]">
            Get market-moving news{" "}
            <span className="text-[--primary]">first.</span>
          </h1>
          <p className="mt-5 text-lg text-[--muted] max-w-xl">
            SEC filings, FDA approvals, earnings - delivered 15 minutes before social media. Stop being last to profitable opportunities.
          </p>
          <div className="mt-6 flex items-center gap-4">
            <div className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[--primary]/10 border border-[--primary]/20">
              <svg className="w-4 h-4 text-[--primary]" fill="currentColor" viewBox="0 0 20 20">
                <path d="M9 6a3 3 0 11-6 0 3 3 0 016 0zM17 6a3 3 0 11-6 0 3 3 0 016 0zM12.93 17c.046-.327.07-.66.07-1a6.97 6.97 0 00-1.5-4.33A5 5 0 0119 16v1h-6.07zM6 11a5 5 0 015 5v1H1v-1a5 5 0 015-5z" />
              </svg>
              <span className="text-sm font-medium text-[--text]">Institutional-Grade Analytics</span>
            </div>
          </div>
          <div className="mt-8">
            <Button asChild className="bg-[--primary] hover:bg-[--primary-contrast] text-black hover:text-white text-lg px-8 py-6">
              <Link href="/signup">Get Instant Alerts - Start Free Trial</Link>
            </Button>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 12 }}
          whileInView={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35, delay: 0.05 }}
          viewport={{ once: true }}
          className="lg:col-span-6"
        >
          <div className="relative rounded-3xl border border-white/10 bg-[--panel] p-3 shadow-soft">
            <div className="relative aspect-[4/3] rounded-2xl bg-gradient-to-br from-[--panel] to-[--bg] overflow-hidden">
              <Image
                src="/impact-radar-hero.png"
                alt="Impact Radar event tracking visualization"
                fill
                className="object-cover rounded-2xl"
                priority
              />
            </div>
            <div className="pointer-events-none absolute inset-0 rounded-3xl ring-1 ring-white/5" />
          </div>
        </motion.div>
      </div>

      <div className="absolute -top-20 -left-20 h-72 w-72 rounded-full bg-[--primary] opacity-10 blur-3xl" />
      <div className="absolute -bottom-24 -right-16 h-72 w-72 rounded-full bg-[--accent] opacity-10 blur-3xl" />
    </section>
  );
}

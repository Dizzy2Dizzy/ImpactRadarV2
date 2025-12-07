"use client";

import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import { Button } from "@/components/ui/button";
import { Mail } from "lucide-react";
import { FormEvent, useState } from "react";

export default function ContactPage() {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitStatus, setSubmitStatus] = useState<{type: 'success' | 'error', message: string} | null>(null);

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setIsSubmitting(true);
    setSubmitStatus(null);

    const formData = new FormData(e.currentTarget);
    const data = {
      name: formData.get("name") as string,
      email: formData.get("email") as string,
      message: formData.get("message") as string,
    };

    try {
      const response = await fetch("/api/contact", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });

      const result = await response.json();

      if (response.ok) {
        setSubmitStatus({ type: 'success', message: result.message || 'Message sent successfully!' });
        (e.target as HTMLFormElement).reset();
      } else {
        setSubmitStatus({ type: 'error', message: result.error || 'Failed to send message' });
      }
    } catch (error) {
      setSubmitStatus({ type: 'error', message: 'Failed to send message. Please try again.' });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen">
      <Header />
      <main className="py-16 lg:py-24">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <div className="mx-auto max-w-2xl text-center">
            <h1 className="text-4xl md:text-6xl font-semibold tracking-tight text-[--text]">
              Get in <span className="text-[--primary]">touch</span>
            </h1>
            <p className="mt-6 text-lg text-[--muted]">
              Have questions? We're here to help.
            </p>
          </div>

          <div className="mt-16 grid gap-8 lg:grid-cols-2">
            <div className="rounded-3xl border border-white/10 bg-[--panel] p-8">
              <h2 className="text-2xl font-semibold text-[--text] mb-6">
                Send us a message
              </h2>
              <form onSubmit={handleSubmit} className="space-y-6">
                <div>
                  <label
                    htmlFor="name"
                    className="block text-sm font-medium text-[--text] mb-2"
                  >
                    Name
                  </label>
                  <input
                    type="text"
                    id="name"
                    name="name"
                    required
                    className="w-full rounded-lg border border-white/10 bg-[--bg] px-4 py-3 text-[--text] placeholder:text-[--muted] focus:border-[--primary] focus:outline-none focus:ring-2 focus:ring-[--primary]"
                    placeholder="John Doe"
                  />
                </div>
                <div>
                  <label
                    htmlFor="email"
                    className="block text-sm font-medium text-[--text] mb-2"
                  >
                    Email
                  </label>
                  <input
                    type="email"
                    id="email"
                    name="email"
                    required
                    className="w-full rounded-lg border border-white/10 bg-[--bg] px-4 py-3 text-[--text] placeholder:text-[--muted] focus:border-[--primary] focus:outline-none focus:ring-2 focus:ring-[--primary]"
                    placeholder="you@example.com"
                  />
                </div>
                <div>
                  <label
                    htmlFor="message"
                    className="block text-sm font-medium text-[--text] mb-2"
                  >
                    Message
                  </label>
                  <textarea
                    id="message"
                    name="message"
                    required
                    rows={6}
                    className="w-full rounded-lg border border-white/10 bg-[--bg] px-4 py-3 text-[--text] placeholder:text-[--muted] focus:border-[--primary] focus:outline-none focus:ring-2 focus:ring-[--primary]"
                    placeholder="Tell us how we can help..."
                  />
                </div>
                {submitStatus && (
                  <div className={`p-4 rounded-lg ${
                    submitStatus.type === 'success' 
                      ? 'bg-green-500/10 border border-green-500/20 text-green-400' 
                      : 'bg-red-500/10 border border-red-500/20 text-red-400'
                  }`}>
                    {submitStatus.message}
                  </div>
                )}
                <Button type="submit" className="w-full" disabled={isSubmitting}>
                  {isSubmitting ? 'Sending...' : 'Send Message'}
                </Button>
              </form>
            </div>

            <div className="space-y-8">
              <div className="rounded-2xl border border-white/10 bg-[--panel] p-6">
                <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-[--primary]/10 text-[--primary] mb-4">
                  <Mail className="h-6 w-6" />
                </div>
                <h3 className="text-lg font-semibold text-[--text] mb-2">
                  Email us
                </h3>
                <p className="text-sm text-[--muted] mb-4">
                  For general inquiries and support
                </p>
                <a
                  href="mailto:support@impactradar.co"
                  className="text-[--primary] hover:text-[--accent] transition-colors"
                >
                  support@impactradar.co
                </a>
              </div>
            </div>
          </div>
        </div>
      </main>
      <Footer />
    </div>
  );
}

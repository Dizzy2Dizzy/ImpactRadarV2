'use client';

import { Header } from '@/components/Header';
import { Footer } from '@/components/Footer';
import { XFeedTab } from '@/components/dashboard/XFeedTab';

export default function XFeedPage() {
  return (
    <div className="min-h-screen bg-[--bg]">
      <Header />
      <main className="py-8">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <XFeedTab />
        </div>
      </main>
      <Footer />
    </div>
  );
}

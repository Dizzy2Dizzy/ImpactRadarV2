import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import { Button } from "@/components/ui/button";
import Link from "next/link";
import { AlertCircle } from "lucide-react";

export default function NotFound() {
  return (
    <div className="min-h-screen flex flex-col">
      <Header />
      <main className="flex-1 flex items-center justify-center px-6 py-24">
        <div className="text-center max-w-2xl">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-[--primary]/10 text-[--primary] mb-6">
            <AlertCircle className="h-8 w-8" />
          </div>
          <h1 className="text-6xl font-semibold text-[--text] mb-4">404</h1>
          <h2 className="text-2xl font-semibold text-[--text] mb-4">
            Page not found
          </h2>
          <p className="text-lg text-[--muted] mb-8">
            The page you're looking for doesn't exist or has been moved.
          </p>
          <div className="flex gap-4 justify-center flex-wrap">
            <Button size="lg" asChild>
              <Link href="/">Go Home</Link>
            </Button>
            <Button size="lg" variant="outline" asChild>
              <Link href="/contact">Contact Support</Link>
            </Button>
          </div>
        </div>
      </main>
      <Footer />
    </div>
  );
}

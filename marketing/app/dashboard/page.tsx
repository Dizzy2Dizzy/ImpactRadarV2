import { redirect } from "next/navigation";
import { cookies } from "next/headers";
import { getSession } from "@/lib/auth";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import { DashboardWithOnboarding } from "@/components/dashboard/DashboardWithOnboarding";
import { LiveEventsProvider } from "@/components/dashboard/LiveEventsProvider";
import { ErrorBoundary } from "@/components/ErrorBoundary";

export default async function DashboardPage() {
  const session = await getSession();

  if (!session) {
    redirect("/login");
  }

  const token = (await cookies()).get("session")?.value || null;

  return (
    <div className="min-h-screen flex flex-col bg-[#131722]">
      <Header />
      <main className="flex-1 px-4 py-6">
        <div className="w-full max-w-[1920px] mx-auto">
          <div className="mb-6">
            <h1 className="text-4xl font-bold text-[--text] mb-2">Dashboard</h1>
            <p className="text-lg text-[--muted]">
              Welcome to Impact Radar! Your event tracking dashboard.
            </p>
          </div>

          <ErrorBoundary>
            <LiveEventsProvider token={token}>
              <DashboardWithOnboarding />
            </LiveEventsProvider>
          </ErrorBoundary>
        </div>
      </main>
      <Footer />
    </div>
  );
}

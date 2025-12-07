"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Tooltip } from "@/components/ui/tooltip";
import { CheckCircle2 } from "lucide-react";
import Link from "next/link";
import { Plan } from "@/data/plans";

interface PlansProps {
  plans: Plan[];
}

export function Plans({ plans }: PlansProps) {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [userPlan, setUserPlan] = useState<string | undefined>();

  useEffect(() => {
    async function checkAuth() {
      try {
        const response = await fetch("/api/auth/me");
        const data = await response.json();
        setIsLoggedIn(data.isLoggedIn);
        setUserPlan(data.plan);
      } catch (error) {
        console.error("Failed to check auth status:", error);
        setIsLoggedIn(false);
      } finally {
        setIsLoading(false);
      }
    }

    checkAuth();
  }, []);

  const getPlanHref = (plan: Plan) => {
    if (!isLoggedIn) return plan.href;
    
    if (plan.id === 'pro' || plan.id === 'team') {
      return `/account/billing?upgrade=${plan.id}`;
    }
    return plan.href;
  };

  return (
    <div className="grid gap-8 lg:grid-cols-3 lg:gap-6">
      {plans.map((plan) => (
        <div
          key={plan.id}
          className={`relative rounded-3xl border p-8 ${
            plan.highlighted
              ? "border-[--primary] bg-[--primary]/5"
              : "border-white/10 bg-[--panel]"
          }`}
        >
          {plan.badge && (
            <div className="absolute -top-4 left-1/2 -translate-x-1/2">
              <span className="inline-flex items-center rounded-full bg-[--primary] px-3 py-1 text-sm font-semibold text-black">
                {plan.badge}
              </span>
            </div>
          )}

          <div className="text-center">
            <h3 className="text-lg font-semibold text-[--text]">
              {plan.name}
            </h3>
            <p className="mt-4 flex items-baseline justify-center gap-x-2">
              <span className="text-5xl font-bold text-[--text]">
                {plan.price}
              </span>
              <span className="text-sm text-[--muted]">
                {plan.period}
              </span>
            </p>
            <p className="mt-4 text-sm text-[--muted]">
              {plan.description}
            </p>
            {plan.note && (
              <p className="mt-2 text-xs text-[--muted] italic">
                {plan.note}
              </p>
            )}
          </div>

          <ul className="mt-8 space-y-3">
            {plan.features.map((feature, index) => (
              <li key={index} className="flex gap-3">
                <CheckCircle2 className="h-5 w-5 text-[--accent] flex-shrink-0 mt-0.5" />
                <span className="text-sm text-[--text] flex items-center gap-1.5">
                  {feature.text}
                  {feature.tooltip && (
                    <Tooltip content={feature.tooltip} />
                  )}
                </span>
              </li>
            ))}
          </ul>

          <div className="mt-8">
            {isLoading ? (
              <Button
                disabled
                className="w-full"
                variant={plan.highlighted ? "default" : "outline"}
              >
                Loading...
              </Button>
            ) : (
              <Button
                asChild
                className="w-full"
                variant={plan.highlighted ? "default" : "outline"}
              >
                <Link href={getPlanHref(plan)}>{plan.cta}</Link>
              </Button>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

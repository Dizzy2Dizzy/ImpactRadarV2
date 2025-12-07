"use client";

import { RiskMetrics } from "@/lib/api";
import { AlertTriangle, TrendingDown, TrendingUp, Shield, Target, PieChart } from "lucide-react";

interface RiskMetricsCardsProps {
  metrics: RiskMetrics;
}

export function RiskMetricsCards({ metrics }: RiskMetricsCardsProps) {
  const getRiskLevel = (value: number, thresholds: { low: number; medium: number }): 'low' | 'medium' | 'high' => {
    if (value <= thresholds.low) return 'low';
    if (value <= thresholds.medium) return 'medium';
    return 'high';
  };

  const getRiskColor = (level: 'low' | 'medium' | 'high'): string => {
    switch (level) {
      case 'low':
        return 'text-green-400 border-green-500/30 bg-green-500/10';
      case 'medium':
        return 'text-yellow-400 border-yellow-500/30 bg-yellow-500/10';
      case 'high':
        return 'text-red-400 border-red-500/30 bg-red-500/10';
    }
  };

  const getTextColor = (level: 'low' | 'medium' | 'high'): string => {
    switch (level) {
      case 'low':
        return 'text-green-400';
      case 'medium':
        return 'text-yellow-400';
      case 'high':
        return 'text-red-400';
    }
  };

  const exposureLevel = getRiskLevel(metrics.total_event_exposure, { low: 25, medium: 50 });
  const concentrationLevel = getRiskLevel(metrics.concentration_risk_score, { low: 30, medium: 60 });
  const diversificationLevel = metrics.sector_diversification_score >= 60 ? 'low' : 
                               metrics.sector_diversification_score >= 30 ? 'medium' : 'high';
  const varLevel = getRiskLevel(Math.abs(metrics.var_95), { low: 5, medium: 10 });
  const esLevel = getRiskLevel(Math.abs(metrics.expected_shortfall), { low: 7, medium: 12 });

  const metricCards = [
    {
      title: "Event Exposure",
      value: `${metrics.total_event_exposure.toFixed(1)}%`,
      level: exposureLevel,
      icon: Target,
      tooltip: "Percentage of portfolio exposed to upcoming events in the next 30 days",
      description: exposureLevel === 'high' ? 'High event exposure' : exposureLevel === 'medium' ? 'Moderate exposure' : 'Low exposure'
    },
    {
      title: "Concentration Risk",
      value: metrics.concentration_risk_score.toFixed(0),
      level: concentrationLevel,
      icon: PieChart,
      tooltip: "Portfolio concentration measured by Herfindahl index (0-100). Lower is more diversified.",
      description: concentrationLevel === 'high' ? 'Highly concentrated' : concentrationLevel === 'medium' ? 'Moderately concentrated' : 'Well diversified'
    },
    {
      title: "Sector Diversification",
      value: metrics.sector_diversification_score.toFixed(0),
      level: diversificationLevel,
      icon: Shield,
      tooltip: "Sector diversification score (0-100). Higher scores indicate better diversification across sectors.",
      description: diversificationLevel === 'high' ? 'Poor diversification' : diversificationLevel === 'medium' ? 'Moderate diversification' : 'Well diversified'
    },
    {
      title: "VaR (95%)",
      value: `${Math.abs(metrics.var_95).toFixed(2)}%`,
      level: varLevel,
      icon: TrendingDown,
      tooltip: "Value at Risk at 95% confidence. Maximum expected loss in worst 5% of scenarios.",
      description: varLevel === 'high' ? 'High downside risk' : varLevel === 'medium' ? 'Moderate risk' : 'Low risk'
    },
    {
      title: "Expected Shortfall",
      value: `${Math.abs(metrics.expected_shortfall).toFixed(2)}%`,
      level: esLevel,
      icon: AlertTriangle,
      tooltip: "Expected Shortfall (CVaR). Average loss in worst-case scenarios beyond VaR.",
      description: esLevel === 'high' ? 'High tail risk' : esLevel === 'medium' ? 'Moderate tail risk' : 'Low tail risk'
    }
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
      {metricCards.map((card, idx) => {
        const Icon = card.icon;
        return (
          <div
            key={idx}
            className={`relative rounded-lg border p-4 ${getRiskColor(card.level)} transition-all hover:shadow-lg`}
            title={card.tooltip}
          >
            <div className="flex items-start justify-between mb-2">
              <div className="flex-1">
                <p className="text-xs text-[--muted] uppercase tracking-wider mb-1">
                  {card.title}
                </p>
                <p className={`text-2xl font-bold ${getTextColor(card.level)}`}>
                  {card.value}
                </p>
              </div>
              <Icon className={`h-6 w-6 ${getTextColor(card.level)} opacity-60`} />
            </div>
            <p className="text-xs text-[--muted] mt-2">
              {card.description}
            </p>
          </div>
        );
      })}
    </div>
  );
}

"use client";

import { Tooltip } from "@/components/ui/tooltip";
import { CheckCircle2, XCircle } from "lucide-react";
import { ComparisonFeature } from "@/data/plans";

interface ComparisonProps {
  features: ComparisonFeature[];
}

export function Comparison({ features }: ComparisonProps) {
  const renderCell = (value: boolean | string) => {
    if (typeof value === 'boolean') {
      return value ? (
        <span className="inline-flex items-center justify-center" role="img" aria-label="Included">
          <CheckCircle2 className="h-5 w-5 text-green-400" />
          <span className="sr-only">Included</span>
        </span>
      ) : (
        <span className="inline-flex items-center justify-center" role="img" aria-label="Not included">
          <XCircle className="h-5 w-5 text-gray-600" />
          <span className="sr-only">Not included</span>
        </span>
      );
    }
    return <span className="text-sm text-[--text]">{value}</span>;
  };

  return (
    <div className="mt-24">
      <h2 className="text-3xl font-semibold text-[--text] text-center mb-12">
        Feature Comparison
      </h2>
      <div className="overflow-x-auto">
        <table className="w-full border-collapse">
          <thead>
            <tr className="border-b border-white/10">
              <th className="text-left py-4 px-4 text-sm font-semibold text-[--text]">
                Feature
              </th>
              <th className="text-center py-4 px-4 text-sm font-semibold text-[--text]">
                Free
              </th>
              <th className="text-center py-4 px-4 text-sm font-semibold text-[--text]">
                Pro
              </th>
              <th className="text-center py-4 px-4 text-sm font-semibold text-[--text]">
                Team
              </th>
            </tr>
          </thead>
          <tbody>
            {features.map((feature, index) => (
              <tr
                key={index}
                className="border-b border-white/5 hover:bg-white/5 transition-colors"
              >
                <td className="py-4 px-4 text-sm text-[--text] flex items-center gap-1.5">
                  {feature.name}
                  {feature.tooltip && (
                    <Tooltip content={feature.tooltip} />
                  )}
                </td>
                <td className="py-4 px-4 text-center">
                  {renderCell(feature.free)}
                </td>
                <td className="py-4 px-4 text-center">
                  {renderCell(feature.pro)}
                </td>
                <td className="py-4 px-4 text-center">
                  {renderCell(feature.team)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

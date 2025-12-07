"use client";

interface SectorCorrelationMatrixProps {
  correlationData: Record<string, any>;
}

export function SectorCorrelationMatrix({ correlationData }: SectorCorrelationMatrixProps) {
  if (!correlationData || Object.keys(correlationData).length === 0) {
    return (
      <div className="rounded-lg border border-white/10 bg-[--panel] p-8 text-center">
        <p className="text-[--muted]">
          Sector correlation data will be available after risk calculation.
        </p>
        <p className="text-xs text-[--muted] mt-2">
          This feature shows how different sectors in your portfolio move together.
        </p>
      </div>
    );
  }

  const sectors = Object.keys(correlationData);
  
  if (sectors.length === 0) {
    return (
      <div className="rounded-lg border border-white/10 bg-[--panel] p-8 text-center">
        <p className="text-[--muted]">
          No sector correlation data available. Your portfolio may need more diverse sector exposure.
        </p>
      </div>
    );
  }

  const getCorrelationColor = (value: number): string => {
    if (value >= 0.7) return 'bg-red-500';
    if (value >= 0.5) return 'bg-orange-500';
    if (value >= 0.3) return 'bg-yellow-500';
    if (value >= 0) return 'bg-green-500';
    if (value >= -0.3) return 'bg-blue-500';
    return 'bg-purple-500';
  };

  const getCorrelationOpacity = (value: number): string => {
    const absValue = Math.abs(value);
    if (absValue >= 0.8) return 'opacity-100';
    if (absValue >= 0.6) return 'opacity-80';
    if (absValue >= 0.4) return 'opacity-60';
    if (absValue >= 0.2) return 'opacity-40';
    return 'opacity-20';
  };

  return (
    <div className="rounded-lg border border-white/10 bg-[--panel] p-6">
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-[--text]">Sector Correlation Matrix</h3>
        <p className="text-xs text-[--muted] mt-1">
          Shows how strongly sectors in your portfolio are correlated. High correlation (red) means sectors move together.
        </p>
      </div>

      <div className="overflow-x-auto">
        <div className="inline-block min-w-full">
          <table className="w-full border-collapse">
            <thead>
              <tr>
                <th className="text-xs text-[--muted] text-left p-2 border-b border-white/10"></th>
                {sectors.map((sector) => (
                  <th
                    key={sector}
                    className="text-xs text-[--muted] text-center p-2 border-b border-white/10 min-w-[80px]"
                    title={sector}
                  >
                    <div className="truncate max-w-[80px]">{sector}</div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {sectors.map((rowSector) => (
                <tr key={rowSector}>
                  <td className="text-xs text-[--muted] p-2 border-r border-white/10 font-medium" title={rowSector}>
                    <div className="truncate max-w-[100px]">{rowSector}</div>
                  </td>
                  {sectors.map((colSector) => {
                    const correlation = correlationData[rowSector]?.[colSector] ?? 0;
                    const isDiagonal = rowSector === colSector;
                    
                    return (
                      <td
                        key={colSector}
                        className="p-1 text-center"
                        title={`${rowSector} vs ${colSector}: ${correlation.toFixed(2)}`}
                      >
                        <div
                          className={`
                            h-12 w-full rounded flex items-center justify-center
                            ${isDiagonal ? 'bg-gray-700' : getCorrelationColor(correlation)}
                            ${isDiagonal ? 'opacity-30' : getCorrelationOpacity(correlation)}
                            transition-all hover:scale-105 hover:opacity-100
                          `}
                        >
                          <span className="text-xs font-medium text-white">
                            {isDiagonal ? '1.0' : correlation.toFixed(2)}
                          </span>
                        </div>
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="mt-4 flex items-center gap-4 text-xs text-[--muted]">
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded bg-red-500"></div>
          <span>Strong Positive (0.7+)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded bg-yellow-500"></div>
          <span>Moderate (0.3-0.7)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded bg-green-500"></div>
          <span>Weak (0-0.3)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded bg-blue-500"></div>
          <span>Negative</span>
        </div>
      </div>
    </div>
  );
}

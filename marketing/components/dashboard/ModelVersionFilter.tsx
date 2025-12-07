'use client';

import { Cpu, Calculator, Zap } from 'lucide-react';

export type ModelVersion = 'v1.0' | 'v1.5' | 'v2.0';

interface ModelVersionFilterProps {
  value: ModelVersion;
  onChange: (version: ModelVersion) => void;
  className?: string;
}

const modelVersions = [
  {
    id: 'v1.0' as ModelVersion,
    label: 'V1.0',
    description: 'Deterministic',
    tooltip: 'Rule-based scoring using event type, sector, and volatility factors',
    icon: Calculator,
    color: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
    activeColor: 'bg-blue-500 text-white border-blue-500',
  },
  {
    id: 'v1.5' as ModelVersion,
    label: 'V1.5',
    description: 'Hybrid',
    tooltip: 'Combines deterministic rules with ML predictions using confidence weighting',
    icon: Zap,
    color: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
    activeColor: 'bg-emerald-500 text-white border-emerald-500',
  },
  {
    id: 'v2.0' as ModelVersion,
    label: 'V2.0',
    description: 'Market Echo',
    tooltip: 'ML-only scoring from the Market Echo Engine using XGBoost models',
    icon: Cpu,
    color: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
    activeColor: 'bg-purple-500 text-white border-purple-500',
  },
];

export function ModelVersionFilter({ value, onChange, className = '' }: ModelVersionFilterProps) {
  return (
    <div className={`flex items-center gap-1 ${className}`}>
      <span className="text-xs text-[--muted] mr-2">Model:</span>
      <div className="flex rounded-lg border border-white/10 overflow-hidden">
        {modelVersions.map((version) => {
          const Icon = version.icon;
          const isActive = value === version.id;
          
          return (
            <button
              key={version.id}
              onClick={() => onChange(version.id)}
              title={version.tooltip}
              className={`
                flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium transition-all
                ${isActive 
                  ? version.activeColor 
                  : 'bg-[--card] text-[--muted] hover:text-[--text] hover:bg-white/5'
                }
                ${version.id !== 'v1.0' ? 'border-l border-white/10' : ''}
              `}
            >
              <Icon className="w-3.5 h-3.5" />
              <span>{version.label}</span>
              <span className="hidden sm:inline text-[10px] opacity-75">
                ({version.description})
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

export function ModelVersionBadge({ version }: { version: ModelVersion }) {
  const versionConfig = modelVersions.find(v => v.id === version) || modelVersions[1];
  const Icon = versionConfig.icon;
  
  return (
    <span 
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-medium border ${versionConfig.color}`}
      title={versionConfig.tooltip}
    >
      <Icon className="w-3 h-3" />
      {versionConfig.label}
    </span>
  );
}

export function getScoreForVersion(event: any, version: ModelVersion): number {
  switch (version) {
    case 'v1.0':
      return event.impact_score || 50;
    case 'v1.5':
      return event.ml_adjusted_score || event.impact_score || 50;
    case 'v2.0':
      if (event.model_source && event.model_source !== 'deterministic') {
        return event.ml_adjusted_score || event.impact_score || 50;
      }
      return event.impact_score || 50;
    default:
      return event.ml_adjusted_score || event.impact_score || 50;
  }
}

export function getScoreLabel(version: ModelVersion): string {
  switch (version) {
    case 'v1.0':
      return 'Deterministic Score';
    case 'v1.5':
      return 'Hybrid Score';
    case 'v2.0':
      return 'ML Score';
    default:
      return 'Impact Score';
  }
}

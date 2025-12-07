import { LucideIcon } from 'lucide-react';

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description: string;
  action?: {
    label: string;
    onClick: () => void;
  };
}

export function EmptyState({ icon: Icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-12 px-4 text-center rounded-lg border border-[--border] bg-[--panel]">
      <Icon className="w-12 h-12 text-[--muted] mb-4" />
      <h3 className="text-lg font-semibold text-[--text] mb-2">{title}</h3>
      <p className="text-[--muted] mb-4 max-w-md">{description}</p>
      {action && (
        <button
          onClick={action.onClick}
          className="px-4 py-2 bg-[--primary] text-[--text-on-primary] rounded-lg hover:opacity-90 transition-colors"
        >
          {action.label}
        </button>
      )}
    </div>
  );
}

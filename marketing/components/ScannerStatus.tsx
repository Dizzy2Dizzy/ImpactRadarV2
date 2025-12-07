import { CheckCircle2, XCircle, Clock } from "lucide-react";

interface ScannerStatusProps {
  name: string;
  lastRun: string;
  discoveries: number;
  status: "success" | "error" | "pending";
}

export function ScannerStatus({
  name,
  lastRun,
  discoveries,
  status,
}: ScannerStatusProps) {
  const statusConfig = {
    success: {
      icon: <CheckCircle2 className="h-5 w-5 text-green-400" />,
      dot: "bg-green-400",
    },
    error: {
      icon: <XCircle className="h-5 w-5 text-red-400" />,
      dot: "bg-red-400",
    },
    pending: {
      icon: <Clock className="h-5 w-5 text-yellow-400" />,
      dot: "bg-yellow-400",
    },
  };

  const config = statusConfig[status];

  return (
    <div className="rounded-2xl border border-white/10 bg-[--panel] p-5 hover:border-white/20 transition-all">
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          {config.icon}
          <h3 className="text-base font-semibold text-[--text]">{name}</h3>
        </div>
        <div className={`h-2 w-2 rounded-full ${config.dot} animate-pulse`} />
      </div>
      <div className="space-y-2 text-sm">
        <div className="flex justify-between">
          <span className="text-[--muted]">Last run</span>
          <time className="text-[--text] font-medium">{lastRun}</time>
        </div>
        <div className="flex justify-between">
          <span className="text-[--muted]">Discoveries</span>
          <span className="text-[--text] font-semibold">{discoveries}</span>
        </div>
      </div>
    </div>
  );
}

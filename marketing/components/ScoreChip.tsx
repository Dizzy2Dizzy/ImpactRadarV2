import { cn } from "@/lib/utils";

export function ScoreChip({ score }: { score: number }) {
  const band =
    score >= 80
      ? "bg-green-500/15 text-green-300 ring-1 ring-green-500/20"
      : score >= 60
      ? "bg-yellow-500/15 text-yellow-300 ring-1 ring-yellow-500/20"
      : "bg-red-500/15 text-red-300 ring-1 ring-red-500/20";

  return (
    <span
      aria-label={`Impact score ${score}`}
      className={cn(
        "inline-flex items-center justify-center rounded-full px-2.5 py-1 text-sm font-semibold tabular-nums",
        band
      )}
    >
      {score}
    </span>
  );
}

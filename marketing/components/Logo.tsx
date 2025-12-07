import Image from "next/image";

export function Logo({ className = "h-8 w-8" }: { className?: string }) {
  return (
    <Image
      src="/impact-radar-logo.png"
      alt="Impact Radar"
      width={32}
      height={32}
      className={className}
      priority
    />
  );
}

import Image from "next/image";
import { cn } from "@/lib/utils";

const logoSizes = {
  sidebar: "w-[184px]",
  auth: "w-[230px]",
  mobile: "w-[148px]",
} as const;

export function BrandLogo({
  size = "sidebar",
  className,
  priority = false,
}: {
  size?: keyof typeof logoSizes;
  className?: string;
  priority?: boolean;
}) {
  return (
    <Image
      src="/logo-organiza-financas.png"
      alt="Organiza Finanças"
      width={1983}
      height={793}
      priority={priority}
      className={cn("h-auto max-w-full object-contain", logoSizes[size], className)}
    />
  );
}

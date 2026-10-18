import Image from "next/image";
import branding from "../../public/branding/shift-logo.manifest.json";

/** Official source-derived wordmark. Surface describes its background, not OS theme. */
export function ShiftLogo({
  variant = "full",
  surface = "dark",
}: {
  variant?: "compact" | "full" | "footer";
  surface?: "dark" | "light";
}) {
  return (
    <span className={`shift-logo ${variant}`}>
      <Image
        src={branding.variants[surface]}
        alt="SHIFT"
        width={branding.width}
        height={branding.height}
        unoptimized
        preload={variant !== "footer"}
      />
    </span>
  );
}

import { motion } from "framer-motion";

function getVariantClass(variant) {
  const normalized = String(variant || "default").toLowerCase();

  const variants = {
    default: "tn-badge-default",
    info: "tn-badge-info",
    success: "tn-badge-success",
    warning: "tn-badge-warning",
    danger: "tn-badge-danger",
    error: "tn-badge-danger",
    cyan: "tn-badge-info",
    blue: "tn-badge-info",
    violet: "tn-badge-violet",
    muted: "tn-badge-muted",
  };

  return variants[normalized] || variants.default;
}

export default function Badge({
  children,
  variant = "default",
  className = "",
  size = "md",
  ...props
}) {
  const sizeClass =
    size === "sm"
      ? "tn-badge-sm"
      : size === "lg"
        ? "tn-badge-lg"
        : "tn-badge-md";

  return (
    <motion.span
      className={[
        "tn-badge",
        getVariantClass(variant),
        sizeClass,
        className,
      ]
        .filter(Boolean)
        .join(" ")}
      initial={{ opacity: 0, scale: 0.96 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{
        duration: 0.18,
        ease: "easeOut",
      }}
      {...props}
    >
      {children}
    </motion.span>
  );
}
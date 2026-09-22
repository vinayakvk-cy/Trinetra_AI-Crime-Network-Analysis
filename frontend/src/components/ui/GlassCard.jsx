import { motion } from "framer-motion";

export default function GlassCard({
  children,
  className = "",
  hover = false,
  animate = true,
  ...props
}) {
  const classes = [
    "tn-glass",
    className,
  ]
    .filter(Boolean)
    .join(" ");

  if (!animate && !hover) {
    return (
      <div className={classes} {...props}>
        {children}
      </div>
    );
  }

  return (
    <motion.div
      className={classes}
      initial={
        animate
          ? {
              opacity: 0,
              y: 8,
            }
          : false
      }
      animate={
        animate
          ? {
              opacity: 1,
              y: 0,
            }
          : undefined
      }
      whileHover={
        hover
          ? {
              y: -2,
            }
          : undefined
      }
      transition={{
        duration: 0.28,
        ease: [0.22, 1, 0.36, 1],
      }}
      {...props}
    >
      {children}
    </motion.div>
  );
}
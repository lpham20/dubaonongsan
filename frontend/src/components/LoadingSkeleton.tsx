type LoadingSkeletonVariant = "page" | "chart" | "article" | "table";

type LoadingSkeletonProps = {
  label: string;
  variant?: LoadingSkeletonVariant;
  rows?: number;
};

export function LoadingSkeleton({ label, variant = "page", rows = 4 }: LoadingSkeletonProps) {
  const lines = Array.from({ length: rows }, (_, index) => index);

  return (
    <div className={`loading-skeleton loading-skeleton--${variant}`} role="status" aria-live="polite" aria-label={label}>
      <span className="visually-hidden">{label}</span>
      <div className="loading-skeleton__header">
        <span />
        <span />
      </div>
      <div className="loading-skeleton__body">
        {lines.map((line) => (
          <span key={line} />
        ))}
      </div>
    </div>
  );
}

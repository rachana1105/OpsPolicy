export function ComingSoon({
  title,
  milestone,
  children,
}: {
  title: string;
  milestone: string;
  children?: React.ReactNode;
}) {
  return (
    <div>
      <h1 className="font-display text-3xl text-ink mb-1">{title}</h1>
      <p className="text-muted mb-8">{children}</p>
      <div className="card p-10 grid place-items-center text-center">
        <div className="h-14 w-14 rounded-2xl bg-primary-soft grid place-items-center mb-4">
          <span className="font-display text-2xl text-primary-deep">◷</span>
        </div>
        <div className="font-display text-xl text-ink mb-1">
          Arriving in {milestone}
        </div>
        <p className="text-sm text-muted max-w-sm">
          The backend contracts and data model for this area are in place. The
          screen lands as its milestone is built out.
        </p>
      </div>
    </div>
  );
}

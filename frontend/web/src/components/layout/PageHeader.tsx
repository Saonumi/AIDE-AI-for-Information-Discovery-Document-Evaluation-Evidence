/** Shared page chrome so every screen states what it is and where it sits in §10.2. */
export function PageHeader({
  navOrder,
  title,
  subtitle,
  actions,
}: {
  navOrder?: number
  title: string
  subtitle?: string
  actions?: React.ReactNode
}) {
  return (
    <header className="page__header" data-testid="page-header" data-nav-order={navOrder}>
      <h1 className="page__title">
        {navOrder != null && <span className="page__nav-order">{navOrder}. </span>}
        {title}
      </h1>
      {subtitle && <p className="page__subtitle">{subtitle}</p>}
      {actions && <div className="page__actions">{actions}</div>}
    </header>
  )
}

export function LoadingState({ label = 'Đang tải…' }: { label?: string }) {
  return (
    <div className="state" data-testid="loading-state">
      {label}
    </div>
  )
}

export function EmptyState({ label }: { label: string }) {
  return (
    <div className="state" data-testid="empty-state">
      {label}
    </div>
  )
}

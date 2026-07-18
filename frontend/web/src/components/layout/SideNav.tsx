'use client'

/** Left navigation — the 10 entries of spec §10.2, grouped by workflow. */
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { NAV_GROUP_LABEL, NAV_ITEMS, type NavItem } from '@/lib/navigation'

function isActive(pathname: string, item: NavItem): boolean {
  if (item.href === '/overview') return pathname === '/overview'
  // section roots: /regulatory-sources/new should not light up while on /regulatory-sources/doc-1
  if (item.href.endsWith('/new')) return pathname === item.href
  return pathname === item.href || pathname.startsWith(`${item.href}/`)
}

export function SideNav() {
  const pathname = usePathname()

  const groups: NavItem['group'][] = ['overview', 'workflow_a', 'workflow_b', 'support']

  return (
    <nav className="sidenav" aria-label="Điều hướng chính" data-testid="sidenav">
      <div className="sidenav__brand">
        <span className="sidenav__brand-mark">VAIC</span>
        <span className="sidenav__brand-text">
          <strong>Compliance Knowledge</strong>
          <small>&amp; Document Review Platform</small>
        </span>
      </div>

      {groups.map((group) => {
        const items = NAV_ITEMS.filter((i) => i.group === group)
        if (items.length === 0) return null
        return (
          <div key={group} className="sidenav__group" data-group={group}>
            {NAV_GROUP_LABEL[group] && <p className="sidenav__group-label">{NAV_GROUP_LABEL[group]}</p>}
            <ul className="sidenav__list">
              {items.map((item) => (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    className="sidenav__link"
                    data-active={isActive(pathname, item) ? 'true' : 'false'}
                    data-nav-order={item.order}
                  >
                    <span className="sidenav__order">{item.order}</span>
                    <span className="sidenav__label">{item.label}</span>
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        )
      })}
    </nav>
  )
}

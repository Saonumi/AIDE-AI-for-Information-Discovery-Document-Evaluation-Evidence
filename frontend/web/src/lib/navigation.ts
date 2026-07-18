/**
 * Navigation — spec §10.2, in the exact order the spec lists them.
 *
 * The numbering is part of the contract, so it is kept explicit here rather than
 * left to array position by accident.
 */
export interface NavItem {
  order: number
  label: string
  href: string
  /** Which of the two workflows this screen belongs to; used to group the nav. */
  group: 'overview' | 'workflow_a' | 'workflow_b' | 'support'
}

export const NAV_ITEMS: NavItem[] = [
  { order: 1, label: 'Tổng quan', href: '/overview', group: 'overview' },
  { order: 2, label: 'Add Regulatory Source', href: '/regulatory-sources/new', group: 'workflow_a' },
  { order: 3, label: 'Source Review Inbox', href: '/source-review-inbox', group: 'workflow_a' },
  { order: 4, label: 'Regulatory Changes', href: '/regulatory-changes', group: 'workflow_a' },
  { order: 5, label: 'Policy Mapping', href: '/policy-mapping', group: 'workflow_a' },
  { order: 6, label: 'Regulatory Impact Reports', href: '/impact-reports', group: 'workflow_a' },
  { order: 7, label: 'Check Document Compliance', href: '/compliance-checks/new', group: 'workflow_b' },
  { order: 8, label: 'Compliance Review Reports', href: '/compliance-reports', group: 'workflow_b' },
  { order: 9, label: 'Tra cứu bằng chứng', href: '/evidence-query', group: 'support' },
  { order: 10, label: 'Audit & System Health', href: '/audit-health', group: 'support' },
]

export const NAV_GROUP_LABEL: Record<NavItem['group'], string> = {
  overview: '',
  workflow_a: 'A · Xây dựng kho pháp lý',
  workflow_b: 'B · Kiểm tra tài liệu',
  support: 'Hỗ trợ',
}

import {
  LayoutDashboard,
  Search,
  BarChart3,
  FlaskConical,
  Settings,
  Target,
  Play,
  Bell,
  List,
  Briefcase,
  Bot,
  Database,
  type LucideIcon,
} from 'lucide-react'

export interface NavItem {
  title: string
  href: string
  icon: LucideIcon
}

export interface NavGroup {
  label: string
  items: NavItem[]
}

/** Single source of truth for navigation groups (sidebar + mobile drawer). */
export const navGroups: NavGroup[] = [
  {
    label: 'Overview',
    items: [
      { title: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
      { title: 'Copilot', href: '/copilot', icon: Bot },
      { title: 'Knowledge', href: '/knowledge', icon: Database },
    ],
  },
  {
    label: 'Research',
    items: [
      { title: 'Watchlist', href: '/watchlist', icon: List },
      { title: 'Scanner', href: '/scanner', icon: Search },
      { title: 'Analysis', href: '/analysis', icon: BarChart3 },
    ],
  },
  {
    label: 'Trading',
    items: [
      { title: 'Strategy', href: '/strategy', icon: Target },
      { title: 'Backtest', href: '/backtest', icon: FlaskConical },
      { title: 'Simulation', href: '/simulation', icon: Play },
      { title: 'Portfolio', href: '/portfolio', icon: Briefcase },
      { title: 'Alerts', href: '/alerts', icon: Bell },
    ],
  },
]

export const bottomNavItems: NavItem[] = [
  { title: 'Settings', href: '/settings', icon: Settings },
]

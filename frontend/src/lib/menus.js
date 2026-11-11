import {
  BarChart3,
  Bell,
  CalendarDays,
  ClipboardList,
  FilePlus2,
  FileText,
  Gauge,
  History,
  Home,
  KeyRound,
  Mail,
  ListChecks,
  PackageCheck,
  Route,
  SprayCan,
  Settings,
  Snowflake,
  Store,
  Thermometer,
  Truck,
  Users,
} from 'lucide-react'
import { CleaningNavBadge } from '../components/CleaningNotices.jsx'

// The left-hand menu of each module. A group marked adminOnly is hidden from the night login.
// To add a module: add its menu here, its card in modules.js and its routes in App.jsx.

export const temperatureMenu = {
  name: 'Temperature Logger',
  Icon: Thermometer,
  home: { to: '/temperature', label: 'Home', Icon: Home },
  groups: [
    {
      label: 'Log',
      links: [
        { to: '/log/storage', label: 'Storage', Icon: Snowflake },
        { to: '/log/receiving', label: 'Receiving', Icon: PackageCheck },
        { to: '/log/dispatch', label: 'Dispatch', Icon: Truck },
      ],
    },
    {
      label: 'Admin',
      adminOnly: true,
      links: [
        { to: '/records', label: 'Records', Icon: ClipboardList },
        { to: '/trends', label: 'Trends', Icon: BarChart3 },
        { to: '/reports', label: 'Reports', Icon: FileText },
        { to: '/audit', label: 'Audit log', Icon: History },
      ],
    },
    {
      label: 'Lists',
      adminOnly: true,
      links: [
        { to: '/lists/units', label: 'Storage units', Icon: Snowflake },
        { to: '/lists/suppliers', label: 'Suppliers', Icon: Store },
        { to: '/lists/runs', label: 'Delivery runs', Icon: Route },
      ],
    },
  ],
}

export const cleaningMenu = {
  name: 'Cleaning & Maintenance',
  Icon: SprayCan,
  home: { to: '/cleaning', label: 'Tick tasks', Icon: ListChecks },
  groups: [
    {
      label: 'Table 8: Cleaning',
      adminOnly: true,
      links: [
        { to: '/cleaning/notifications', label: 'Notifications', Icon: Bell, Badge: CleaningNavBadge },
        { to: '/cleaning/records', label: 'Records', Icon: ClipboardList },
        { to: '/cleaning/tasks', label: 'Tasks', Icon: Settings },
        { to: '/cleaning/audit', label: 'Audit log', Icon: History },
      ],
    },
    {
      label: 'Table 14: Calibration',
      adminOnly: true,
      links: [
        { to: '/calibration', label: 'Calibration', Icon: Gauge, end: true },
        { to: '/calibration/new', label: 'New calibration', Icon: FilePlus2 },
        { to: '/calibration/records', label: 'Records', Icon: ClipboardList },
        { to: '/calibration/audit', label: 'Audit log', Icon: History },
      ],
    },
  ],
}

export const recordsMenu = {
  name: 'Records',
  Icon: ClipboardList,
  home: { to: '/all-records', label: 'All records', Icon: ClipboardList },
  groups: [],
}

export const settingsMenu = {
  name: 'Settings',
  Icon: Settings,
  groups: [
    {
      label: 'Settings',
      links: [
        { to: '/settings/staff', label: 'Staff names', Icon: Users },
        { to: '/settings/closed-days', label: 'Public holidays', Icon: CalendarDays },
        { to: '/settings/alerts', label: 'Alert emails', Icon: Mail },
        { to: '/settings/logins', label: 'Logins', Icon: KeyRound },
      ],
    },
  ],
}

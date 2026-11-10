import {
  BarChart3,
  Bell,
  ClipboardList,
  FilePlus2,
  FileText,
  Gauge,
  History,
  Home,
  ListChecks,
  PackageCheck,
  SprayCan,
  Settings,
  Snowflake,
  Thermometer,
  Truck,
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
        { to: '/settings', label: 'Settings', Icon: Settings },
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

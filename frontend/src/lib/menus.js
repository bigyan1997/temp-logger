import {
  BarChart3,
  ClipboardList,
  FilePlus2,
  FileText,
  Gauge,
  History,
  Home,
  PackageCheck,
  Settings,
  Snowflake,
  Thermometer,
  Truck,
} from 'lucide-react'

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

export const calibrationMenu = {
  name: 'Calibration',
  Icon: Gauge,
  home: { to: '/calibration', label: 'Home', Icon: Home },
  groups: [
    {
      label: 'Table 14',
      links: [{ to: '/calibration/new', label: 'New calibration', Icon: FilePlus2 }],
    },
    {
      label: 'Admin',
      adminOnly: true,
      links: [
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

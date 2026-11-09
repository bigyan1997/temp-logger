import { FilePlus2 } from 'lucide-react'
import { Link } from 'react-router-dom'
import CalibrationStatus from '../../components/CalibrationStatus.jsx'

// Day staff: when the next calibration is due, and the button to do one. Past forms are on the Records page.
export default function CalibrationHome() {
  return (
    <div className="max-w-3xl">
      <h1 className="text-2xl font-semibold">Thermometer calibration</h1>
      <p className="mt-1 max-w-prose text-muted">
        HACCP Table 14. The probe thermometer is checked in iced water every 6 months (it must read 0 °C, give or take 1 °C).
      </p>

      <div className="mt-6">
        <CalibrationStatus>
          <Link to="/calibration/new" className="inline-flex h-11 items-center gap-2 rounded-lg bg-brand px-4 font-semibold text-white hover:bg-brand-dark">
            <FilePlus2 size={18} aria-hidden="true" /> New calibration
          </Link>
        </CalibrationStatus>
      </div>
    </div>
  )
}

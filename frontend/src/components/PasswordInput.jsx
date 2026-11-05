import { Eye, EyeOff } from 'lucide-react'
import { useState } from 'react'

// A password box with an eye button to show or hide what was typed.
// `wrapperClass` is for spacing around the box; the other props go to the input.
export default function PasswordInput({ wrapperClass = '', className = '', ...inputProps }) {
  const [visible, setVisible] = useState(false)
  const Icon = visible ? EyeOff : Eye

  return (
    <div className={`relative ${wrapperClass}`}>
      <input {...inputProps} type={visible ? 'text' : 'password'} className={`${className} pr-12`} />
      <button
        type="button"
        onClick={() => setVisible(!visible)}
        aria-label={visible ? 'Hide password' : 'Show password'}
        aria-pressed={visible}
        className="absolute right-1 top-1/2 grid size-10 -translate-y-1/2 place-items-center rounded-lg text-muted hover:bg-brand-soft hover:text-ink"
      >
        <Icon size={20} aria-hidden="true" />
      </button>
    </div>
  )
}

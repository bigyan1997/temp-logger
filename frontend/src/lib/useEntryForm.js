import { useQueryClient } from '@tanstack/react-query'
import { useRef, useState } from 'react'
import { api, ApiError } from '../api/client.js'
import { correctiveBody, emptyCorrective } from '../components/CorrectiveFields.jsx'

const blankEntry = () => ({
  temp: '',
  note: '',
  noDelivery: false,
  packagingOk: true,
  productType: 'chilled',
  corrective: emptyCorrective,
  confirmed: false,
  phase: 'idle', // idle | saving | saved | error | needs_confirm | needs_corrective
  message: '',
  warnings: [],
})

// The state and saving logic for a screen that takes one reading per row (storage, receiving, dispatch).
//
//   endpoint      where to POST, e.g. '/storage-readings/'
//   staffId       the person taking the readings (required)
//   buildBody     (rowKey, entry) => the fields for that row, without the shared ones
//
// Each row is saved on its own. The server may answer that a value needs confirming, or that
// a corrective action is needed; the row then shows that question and the user answers it.
export function useEntryForm({ endpoint, staffId, buildBody }) {
  const queryClient = useQueryClient()
  const [entries, setEntries] = useState({})
  const ids = useRef({}) // one stable id per row, so a retry can never save twice

  const entryFor = (key) => entries[key] ?? blankEntry()
  const update = (key, patch) => setEntries((all) => ({ ...all, [key]: { ...(all[key] ?? blankEntry()), ...patch } }))

  function setField(key, patch) {
    // Changing the value starts over: any earlier confirmation no longer applies.
    const changesValue = 'temp' in patch || 'noDelivery' in patch || 'packagingOk' in patch || 'productType' in patch
    update(key, { ...patch, ...(changesValue && { confirmed: false, phase: 'idle', message: '', warnings: [] }) })
  }

  async function save(key, overrides = {}) {
    const entry = { ...entryFor(key), ...overrides }
    if (!staffId) return update(key, { phase: 'error', message: 'Choose your name at the top first.' })

    ids.current[key] ??= crypto.randomUUID()
    const body = {
      id: ids.current[key],
      recorded_by: staffId,
      note: entry.note,
      confirm_unusual: entry.confirmed,
      ...buildBody(key, entry),
      ...(entry.phase === 'needs_corrective' && entry.corrective.action && { corrective: correctiveBody(entry.corrective) }),
    }

    update(key, { ...overrides, phase: 'saving', message: '' })
    try {
      await api(endpoint, { method: 'POST', body })
      update(key, { phase: 'saved' })
      queryClient.invalidateQueries({ queryKey: ['day'] })
    } catch (error) {
      if (!(error instanceof ApiError)) throw error
      if (error.code === 'needs_confirmation') {
        update(key, { phase: 'needs_confirm', warnings: error.body.warnings ?? [error.message] })
      } else if (error.code === 'corrective_required') {
        update(key, { phase: 'needs_corrective', message: entry.phase === 'needs_corrective' ? 'Choose what was done.' : '' })
      } else {
        const stayOnCorrective = entry.phase === 'needs_corrective' // let them fix the form, not start over
        update(key, { phase: stayOnCorrective ? 'needs_corrective' : 'error', message: error.message })
      }
    }
  }

  // "Yes, that value is right": save again with the confirmation.
  const confirm = (key) => save(key, { confirmed: true })

  // Saves each row in turn. A row that needs a question answered stays open; the others are saved.
  async function saveAll(keys) {
    for (const key of keys) await save(key)
  }

  const isBusy = Object.values(entries).some((entry) => entry.phase === 'saving')

  return { entryFor, setField, save, saveAll, confirm, isBusy }
}

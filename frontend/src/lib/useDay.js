import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client.js'

// What is due and what is already logged on one day. Refreshes so two people
// working at once see each other's entries.
export function useDay(date) {
  return useQuery({
    queryKey: ['day', date],
    queryFn: () => api(`/day/?date=${date}`),
    refetchInterval: 30_000,
  })
}

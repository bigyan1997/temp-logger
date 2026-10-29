import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client.js'

// Limits, corrective-action choices and product types. They rarely change, so fetch once.
export function useReadingOptions() {
  return useQuery({
    queryKey: ['reading-options'],
    queryFn: () => api('/reading-options/'),
    staleTime: Infinity,
  })
}

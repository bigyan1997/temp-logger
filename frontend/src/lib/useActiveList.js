import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client.js'

// An admin-managed list (units, suppliers, runs, staff) with only the active items.
export function useActiveList(endpoint) {
  return useQuery({ queryKey: ['list', endpoint], queryFn: () => api(endpoint) })
}

import { useQuery } from '@tanstack/react-query'
import { getDashboard } from '../api/hq'

export function useDashboard() {
  return useQuery({
    queryKey: ['dashboard'],
    queryFn: getDashboard,
    refetchInterval: 30_000,
  })
}

import { useQuery } from '@tanstack/react-query'
import { getResupply } from '../api/hq'

export function useResupply(stationId?: string) {
  return useQuery({
    queryKey: ['resupply', stationId],
    queryFn: () => getResupply(stationId),
    refetchInterval: 300_000,  // refresh every 5 minutes
  })
}

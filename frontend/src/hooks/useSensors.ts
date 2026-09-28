import { useQuery } from '@tanstack/react-query'
import { getSensors } from '../api/hq'

export function useSensors(stationId: string, domain?: string) {
  return useQuery({
    queryKey: ['sensors', stationId, domain],
    queryFn: () => getSensors(stationId, domain),
    refetchInterval: 10_000,
    enabled: Boolean(stationId),
  })
}

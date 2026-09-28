import { useQuery } from '@tanstack/react-query'
import { getAnalytics } from '../api/hq'

export function useAnalytics(stationId: string, periodHours = 24) {
  return useQuery({
    queryKey: ['analytics', stationId, periodHours],
    queryFn: () => getAnalytics(stationId, periodHours),
    refetchInterval: 60_000,
    enabled: Boolean(stationId),
  })
}

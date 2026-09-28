import { useQuery } from '@tanstack/react-query'
import { getInventory } from '../api/hq'

export function useInventory(stationId: string, category?: string) {
  return useQuery({
    queryKey: ['inventory', stationId, category],
    queryFn: () => getInventory(stationId, category),
    refetchInterval: 60_000,
    enabled: Boolean(stationId),
  })
}

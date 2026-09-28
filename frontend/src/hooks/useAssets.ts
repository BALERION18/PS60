import { useQuery } from '@tanstack/react-query'
import { getAssets } from '../api/hq'

export function useAssets(stationId: string, assetType?: string) {
  return useQuery({
    queryKey: ['assets', stationId, assetType],
    queryFn: () => getAssets(stationId, assetType),
    refetchInterval: 120_000,
    enabled: Boolean(stationId),
  })
}

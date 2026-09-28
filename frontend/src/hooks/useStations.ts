import { useQuery } from '@tanstack/react-query'
import { getStations, getStationStatus } from '../api/hq'

export function useStations() {
  return useQuery({
    queryKey: ['stations'],
    queryFn: getStations,
    refetchInterval: 30_000,
  })
}

export function useStationStatus(stationId: string) {
  return useQuery({
    queryKey: ['station-status', stationId],
    queryFn: () => getStationStatus(stationId),
    refetchInterval: 15_000,
    enabled: Boolean(stationId),
  })
}

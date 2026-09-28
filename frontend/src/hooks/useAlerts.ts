import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getAlerts, acknowledgeAlert } from '../api/hq'

export function useAlerts(params?: {
  station_id?: string
  ack_state?: string
  page_size?: number
}) {
  return useQuery({
    queryKey: ['alerts', params],
    queryFn: () => getAlerts(params),
    refetchInterval: 15_000,
  })
}

export function useAcknowledgeAlert() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ alertId, note }: { alertId: string; note?: string }) =>
      acknowledgeAlert(alertId, note),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['alerts'] })
    },
  })
}

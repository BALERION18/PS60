import { useQuery } from '@tanstack/react-query'
import { getReportData } from '../api/hq'

export function useReport(reportType: string, stationId?: string) {
  return useQuery({
    queryKey: ['report', reportType, stationId],
    queryFn: () => getReportData(reportType, stationId),
    refetchInterval: 120_000,
    enabled: Boolean(reportType),
  })
}

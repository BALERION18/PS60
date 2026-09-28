/**
 * React Query hooks for AI model outputs — Models 1, 2, and 4.
 *
 * useFuelForecast       — Model 1 (Prophet): 90-day fuel burn forecast
 * useAnomalyEvents      — Model 2 (Isolation Forest): recent anomaly events
 * useMaintenancePredictions — Model 4 (Random Forest): maintenance urgency per asset
 * useAIModelStatus      — status of all loaded models (trained_at, metrics)
 */
import { useQuery } from '@tanstack/react-query'
import {
  getFuelForecast,
  getAnomalyEvents,
  getMaintenancePredictions,
  getAIModelStatus,
  type FuelForecastOut,
  type AnomalyEventOut,
  type MaintenancePredictionOut,
  type AIModelStatusOut,
} from '../api/hq'

// ── Model 1: Fuel Forecast (Prophet) ─────────────────────────────────────────
export function useFuelForecast(
  stationId: string,
  horizonDays = 90,
  currentTankLitres?: number,
) {
  return useQuery<FuelForecastOut, Error>({
    queryKey: ['ai', 'fuel-forecast', stationId, horizonDays, currentTankLitres],
    queryFn:  () => getFuelForecast(stationId, horizonDays, currentTankLitres),
    // Fuel forecast is expensive to run — refresh every 10 minutes
    staleTime:       10 * 60 * 1000,
    refetchInterval: 10 * 60 * 1000,
    enabled:  Boolean(stationId),
    retry: 1,
  })
}

// ── Model 2: Anomaly Events (Isolation Forest) ────────────────────────────────
export function useAnomalyEvents(stationId: string, limit = 20) {
  return useQuery<AnomalyEventOut[], Error>({
    queryKey: ['ai', 'anomalies', stationId, limit],
    queryFn:  () => getAnomalyEvents(stationId, limit),
    // Anomalies are real-time — refresh every 30 seconds
    staleTime:       30_000,
    refetchInterval: 30_000,
    enabled:  Boolean(stationId),
    retry: 1,
  })
}

// ── Model 4: Maintenance Predictions (Random Forest) ─────────────────────────
export function useMaintenancePredictions(stationId: string) {
  return useQuery<MaintenancePredictionOut[], Error>({
    queryKey: ['ai', 'maintenance', stationId],
    queryFn:  () => getMaintenancePredictions(stationId),
    // Maintenance predictions change slowly — refresh every 5 minutes
    staleTime:       5 * 60 * 1000,
    refetchInterval: 5 * 60 * 1000,
    enabled:  Boolean(stationId),
    retry: 1,
  })
}

// ── All model status ──────────────────────────────────────────────────────────
export function useAIModelStatus(stationId: string) {
  return useQuery<AIModelStatusOut, Error>({
    queryKey: ['ai', 'status', stationId],
    queryFn:  () => getAIModelStatus(stationId),
    staleTime:       60_000,
    refetchInterval: 60_000,
    enabled:  Boolean(stationId),
    retry: 1,
  })
}

import { useQuery } from '@tanstack/react-query';
import { permitsApi } from '@/api/permits';
import type { Permit, PermitAlert } from '@/types';

export interface UsePermitsResult {
  permits: Permit[];
  alerts: PermitAlert[];
  isLoading: boolean;
  isError: boolean;
  refetch: () => Promise<any>;
}

export function usePermits(buildingId: string): UsePermitsResult {
  const {
    data: permits = [],
    isLoading: permitsLoading,
    isError: permitsError,
    refetch: refetchPermits,
  } = useQuery({
    queryKey: ['building-permits', buildingId],
    queryFn: () => permitsApi.list(buildingId),
    enabled: !!buildingId,
  });

  const {
    data: alerts = [],
    isLoading: alertsLoading,
    isError: alertsError,
  } = useQuery({
    queryKey: ['building-permit-alerts', buildingId],
    queryFn: () => permitsApi.getAlerts(buildingId),
    enabled: !!buildingId,
  });

  return {
    permits,
    alerts,
    isLoading: permitsLoading || alertsLoading,
    isError: permitsError || alertsError,
    refetch: refetchPermits,
  };
}

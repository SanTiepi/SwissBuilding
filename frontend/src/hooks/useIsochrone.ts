import { useQuery } from '@tanstack/react-query';
import { isochroneApi } from '@/api/isochrone';
import type { IsochroneResponse } from '@/api/isochrone';

export function useIsochrone(buildingId: string | undefined, profile = 'walking', minutes = '5,10,15') {
  return useQuery<IsochroneResponse>({
    queryKey: ['isochrone', buildingId, profile, minutes],
    queryFn: () => isochroneApi.get(buildingId!, profile, minutes),
    enabled: !!buildingId,
    staleTime: 7 * 24 * 60 * 60 * 1000, // 7 days — isochrones are stable
    retry: 1,
  });
}

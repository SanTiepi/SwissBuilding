import { useQuery } from '@tanstack/react-query';
import { complianceScanApi } from '@/api/complianceScan';
import type { ComplianceScanResponse } from '@/api/complianceScan';

export function useComplianceScan(buildingId: string | undefined, force = false) {
  return useQuery<ComplianceScanResponse>({
    queryKey: ['compliance-scan', buildingId, force],
    queryFn: () => complianceScanApi.scan(buildingId!, force),
    enabled: !!buildingId,
    staleTime: 24 * 60 * 60 * 1000, // 24h — matches backend cache
    retry: 1,
  });
}

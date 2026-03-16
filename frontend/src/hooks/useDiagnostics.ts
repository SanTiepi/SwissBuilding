import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { diagnosticsApi } from '@/api/diagnostics';
import { riskApi } from '@/api/risk';
import type { Diagnostic, Sample } from '@/types';
import { toast } from '@/store/toastStore';

function extractError(err: unknown): string {
  const e = err as any;
  return e?.response?.data?.detail || e?.message || 'Unknown error';
}

export function useDiagnostics(buildingId: string) {
  return useQuery({
    queryKey: ['diagnostics', 'building', buildingId],
    queryFn: () => diagnosticsApi.listByBuilding(buildingId),
    enabled: !!buildingId,
  });
}

export function useDiagnostic(id: string) {
  return useQuery({
    queryKey: ['diagnostics', id],
    queryFn: () => diagnosticsApi.get(id),
    enabled: !!id,
  });
}

export function useCreateDiagnostic() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ buildingId, data }: { buildingId: string; data: Partial<Diagnostic> }) =>
      diagnosticsApi.create(buildingId, data),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({
        queryKey: ['diagnostics', 'building', variables.buildingId],
      });
    },
    onError: (err) => toast(extractError(err)),
  });
}

export function useUpdateDiagnostic() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<Diagnostic> }) => diagnosticsApi.update(id, data),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['diagnostics', variables.id] });
      queryClient.invalidateQueries({ queryKey: ['diagnostics', 'building'] });
    },
    onError: (err) => toast(extractError(err)),
  });
}

export function useValidateDiagnostic() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => diagnosticsApi.validate(id),
    onSuccess: (_data, id) => {
      queryClient.invalidateQueries({ queryKey: ['diagnostics', id] });
      queryClient.invalidateQueries({ queryKey: ['diagnostics', 'building'] });
    },
    onError: (err) => toast(extractError(err)),
  });
}

export function useSamples(diagnosticId: string) {
  return useQuery({
    queryKey: ['samples', diagnosticId],
    queryFn: () => diagnosticsApi.listSamples(diagnosticId),
    enabled: !!diagnosticId,
  });
}

export function useCreateSample() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ diagnosticId, data }: { diagnosticId: string; data: Partial<Sample> }) =>
      diagnosticsApi.createSample(diagnosticId, data),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({
        queryKey: ['samples', variables.diagnosticId],
      });
    },
    onError: (err) => toast(extractError(err)),
  });
}

export function useUpdateSample() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<Sample> }) => diagnosticsApi.updateSample(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['samples'] });
    },
    onError: (err) => toast(extractError(err)),
  });
}

export function useDeleteSample() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => diagnosticsApi.deleteSample(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['samples'] });
    },
    onError: (err) => toast(extractError(err)),
  });
}

export function useUploadReport() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, file }: { id: string; file: File }) => diagnosticsApi.uploadReport(id, file),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['diagnostics', variables.id] });
      queryClient.invalidateQueries({ queryKey: ['samples'] });
    },
    onError: (err) => toast(extractError(err)),
  });
}

export function useRiskSimulation() {
  return useMutation({
    mutationFn: (data: { building_id: string; renovation_type: string }) => riskApi.simulate(data),
    onError: (err) => toast(extractError(err)),
  });
}

export function useBuildingRisk(buildingId: string) {
  return useQuery({
    queryKey: ['risk', buildingId],
    queryFn: () => riskApi.getBuildingRisk(buildingId),
    enabled: !!buildingId,
  });
}

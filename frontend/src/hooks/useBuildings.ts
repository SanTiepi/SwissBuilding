import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { buildingsApi, type BuildingFilters } from '@/api/buildings';
import type { Building } from '@/types';
import { toast } from '@/store/toastStore';

function extractError(err: unknown): string {
  const e = err as any;
  return e?.response?.data?.detail || e?.message || 'Unknown error';
}

export function useBuildings(filters?: BuildingFilters) {
  return useQuery({
    queryKey: ['buildings', filters],
    queryFn: () => buildingsApi.list(filters),
  });
}

export function useBuilding(id: string) {
  return useQuery({
    queryKey: ['buildings', id],
    queryFn: () => buildingsApi.get(id),
    enabled: !!id,
  });
}

export function useCreateBuilding() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: Partial<Building>) => buildingsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['buildings'] });
    },
    onError: (err) => toast(extractError(err)),
  });
}

export function useUpdateBuilding() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<Building> }) => buildingsApi.update(id, data),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['buildings'] });
      queryClient.invalidateQueries({ queryKey: ['buildings', variables.id] });
    },
    onError: (err) => toast(extractError(err)),
  });
}

export function useDeleteBuilding() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => buildingsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['buildings'] });
    },
    onError: (err) => toast(extractError(err)),
  });
}

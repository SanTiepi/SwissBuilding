import { api } from './client';
import type { Permit, PermitAlert, PermitCreate, PermitUpdate, PaginatedResponse } from '@/types';

export const permitsApi = {
  list: async (buildingId: string): Promise<Permit[]> => {
    const res = await api.get(`/buildings/${buildingId}/permits`);
    const data = res.data as PaginatedResponse<Permit>;
    return data.items;
  },

  get: async (buildingId: string, permitId: string): Promise<Permit> => {
    return api.get(`/buildings/${buildingId}/permits/${permitId}`).then((r) => r.data);
  },

  create: async (buildingId: string, permit: PermitCreate): Promise<Permit> => {
    return api.post(`/buildings/${buildingId}/permits`, permit).then((r) => r.data);
  },

  update: async (buildingId: string, permitId: string, updates: Partial<PermitUpdate>): Promise<Permit> => {
    return api.patch(`/buildings/${buildingId}/permits/${permitId}`, updates).then((r) => r.data);
  },

  delete: async (buildingId: string, permitId: string): Promise<void> => {
    return api.delete(`/buildings/${buildingId}/permits/${permitId}`);
  },

  getAlerts: async (buildingId: string): Promise<PermitAlert[]> => {
    return api.get(`/buildings/${buildingId}/permits/deadline-alerts`).then((r) => r.data);
  },
};

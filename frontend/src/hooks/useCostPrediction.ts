import { useMutation } from '@tanstack/react-query';
import { costPredictionApi } from '@/api/costPrediction';
import type { CostPredictionRequest, CostPredictionResponse } from '@/api/costPrediction';
import { toast } from '@/store/toastStore';

export function useCostPrediction() {
  return useMutation<CostPredictionResponse, Error, CostPredictionRequest>({
    mutationFn: (data) => costPredictionApi.predict(data),
    onError: (err: any) => {
      const msg = err?.response?.data?.detail || err?.message || 'Estimation failed';
      toast(msg, 'error');
    },
  });
}

export function useCostPredictionPdf() {
  return useMutation<Blob, Error, CostPredictionRequest>({
    mutationFn: (data) => costPredictionApi.exportPdf(data),
    onSuccess: (blob) => {
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'estimation-remediation.pdf';
      a.click();
      URL.revokeObjectURL(url);
    },
    onError: (err: any) => {
      const msg = err?.response?.data?.detail || err?.message || 'PDF export failed';
      toast(msg, 'error');
    },
  });
}

import { useMutation } from '@tanstack/react-query';
import { materialRecognitionApi, type MaterialRecognitionResult } from '@/api/materialRecognition';

interface RecognizeParams {
  buildingId: string;
  file: File;
  zoneId?: string;
  elementId?: string;
  save?: boolean;
}

export function useMaterialRecognition() {
  return useMutation<MaterialRecognitionResult, Error, RecognizeParams>({
    mutationFn: ({ buildingId, file, zoneId, elementId, save }) =>
      materialRecognitionApi.recognize(buildingId, file, { zoneId, elementId, save }),
  });
}

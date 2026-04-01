import { useCallback, useRef, useState } from 'react';
import { Camera, Loader2, Upload, X } from 'lucide-react';
import { useMaterialRecognition } from '@/hooks/useMaterialRecognition';
import { MaterialIdentificationCard } from '@/components/MaterialIdentificationCard';
import type { MaterialRecognitionResult } from '@/api/materialRecognition';

interface Props {
  buildingId: string;
  zoneId?: string;
  elementId?: string;
  onSaved?: () => void;
}

const MAX_FILE_SIZE = 5 * 1024 * 1024; // 5 MB
const ACCEPTED_TYPES = ['image/jpeg', 'image/png', 'image/webp'];

export function MaterialRecognitionForm({ buildingId, zoneId, elementId, onSaved }: Props) {
  const [preview, setPreview] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [result, setResult] = useState<MaterialRecognitionResult | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const mutation = useMaterialRecognition();

  const handleFile = useCallback((file: File) => {
    if (file.size > MAX_FILE_SIZE) {
      alert('Fichier trop volumineux (max 5 MB)');
      return;
    }
    if (!ACCEPTED_TYPES.includes(file.type)) {
      alert('Format non supporté. Utilisez JPG, PNG ou WebP.');
      return;
    }
    setSelectedFile(file);
    setResult(null);
    const reader = new FileReader();
    reader.onload = (e) => setPreview(e.target?.result as string);
    reader.readAsDataURL(file);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile],
  );

  const handleAnalyze = () => {
    if (!selectedFile) return;
    mutation.mutate(
      { buildingId, file: selectedFile, zoneId, elementId },
      {
        onSuccess: (data) => setResult(data),
      },
    );
  };

  const handleSave = () => {
    if (!selectedFile || !elementId) return;
    mutation.mutate(
      { buildingId, file: selectedFile, zoneId, elementId, save: true },
      {
        onSuccess: (data) => {
          setResult(data);
          onSaved?.();
        },
      },
    );
  };

  const handleClear = () => {
    setSelectedFile(null);
    setPreview(null);
    setResult(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  return (
    <div className="space-y-6">
      {/* Upload zone */}
      {!preview && (
        <div
          className={`border-2 border-dashed rounded-xl p-8 text-center transition-colors cursor-pointer ${
            dragOver
              ? 'border-indigo-400 bg-indigo-50 dark:bg-indigo-900/20'
              : 'border-gray-300 dark:border-slate-600 hover:border-indigo-300 dark:hover:border-indigo-500'
          }`}
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
        >
          <Camera className="w-12 h-12 mx-auto text-gray-400 dark:text-slate-500 mb-3" />
          <p className="text-sm text-gray-600 dark:text-slate-300 font-medium">
            Glissez une photo de matériau ici
          </p>
          <p className="text-xs text-gray-400 dark:text-slate-500 mt-1">
            ou cliquez pour sélectionner (JPG, PNG, WebP — max 5 MB)
          </p>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/jpeg,image/png,image/webp"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) handleFile(file);
            }}
          />
        </div>
      )}

      {/* Preview */}
      {preview && (
        <div className="relative">
          <img
            src={preview}
            alt="Matériau à identifier"
            className="w-full max-h-80 object-contain rounded-xl border border-gray-200 dark:border-slate-700"
          />
          <button
            onClick={handleClear}
            className="absolute top-2 right-2 p-1.5 bg-white dark:bg-slate-700 rounded-full shadow hover:bg-gray-100 dark:hover:bg-slate-600"
          >
            <X className="w-4 h-4 text-gray-600 dark:text-slate-300" />
          </button>
        </div>
      )}

      {/* Action buttons */}
      {selectedFile && !result && (
        <div className="flex gap-3">
          <button
            onClick={handleAnalyze}
            disabled={mutation.isPending}
            className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 transition-colors"
          >
            {mutation.isPending ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Upload className="w-4 h-4" />
            )}
            {mutation.isPending ? 'Analyse en cours...' : 'Identifier le matériau'}
          </button>
        </div>
      )}

      {/* Error */}
      {mutation.isError && (
        <div className="p-3 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-lg text-sm text-red-700 dark:text-red-300">
          Erreur: {mutation.error?.message || 'Échec de l\'identification'}
        </div>
      )}

      {/* Result */}
      {result && (
        <>
          <MaterialIdentificationCard result={result} />

          {/* Save button */}
          {elementId && (
            <div className="flex gap-3">
              <button
                onClick={handleSave}
                disabled={mutation.isPending}
                className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 transition-colors"
              >
                {mutation.isPending ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : null}
                Sauvegarder dans l&apos;inventaire
              </button>
              <button
                onClick={handleClear}
                className="px-4 py-2 border border-gray-300 dark:border-slate-600 text-gray-700 dark:text-slate-300 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-700 transition-colors"
              >
                Nouvelle photo
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}

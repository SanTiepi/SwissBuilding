import { memo, useCallback, useRef, useState } from 'react';
import { useTranslation } from '@/i18n';
import { Camera, Image, X } from 'lucide-react';

export interface CapturedPhoto {
  uri: string;
  element_part?: string;
  timestamp: string;
}

interface PhotoCaptureWidgetProps {
  photos: CapturedPhoto[];
  onAdd: (photo: CapturedPhoto) => void;
  onRemove: (index: number) => void;
  maxPhotos?: number;
}

export const PhotoCaptureWidget = memo(function PhotoCaptureWidget({
  photos,
  onAdd,
  onRemove,
  maxPhotos = 5,
}: PhotoCaptureWidgetProps) {
  const { t } = useTranslation();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isCapturing, setIsCapturing] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);

  const handleFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = e.target.files;
      if (!files) return;
      Array.from(files).forEach((file) => {
        const reader = new FileReader();
        reader.onload = () => {
          onAdd({
            uri: reader.result as string,
            timestamp: new Date().toISOString(),
          });
        };
        reader.readAsDataURL(file);
      });
      e.target.value = '';
    },
    [onAdd],
  );

  const startCamera = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment' },
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
      setIsCapturing(true);
    } catch {
      fileInputRef.current?.click();
    }
  }, []);

  const capturePhoto = useCallback(() => {
    if (!videoRef.current) return;
    const canvas = document.createElement('canvas');
    canvas.width = videoRef.current.videoWidth;
    canvas.height = videoRef.current.videoHeight;
    const ctx = canvas.getContext('2d');
    ctx?.drawImage(videoRef.current, 0, 0);
    const uri = canvas.toDataURL('image/jpeg', 0.8);
    onAdd({ uri, timestamp: new Date().toISOString() });
    stopCamera();
  }, [onAdd]);

  const stopCamera = useCallback(() => {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    setIsCapturing(false);
  }, []);

  const canAdd = photos.length < maxPhotos;

  return (
    <div data-testid="photo-capture-widget">
      <label className="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-300">
        {t('observation.photos') || 'Photos'} ({photos.length}/{maxPhotos})
      </label>

      {isCapturing && (
        <div className="relative mb-3 overflow-hidden rounded-xl">
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            className="w-full rounded-xl"
            data-testid="camera-preview"
          />
          <div className="absolute bottom-3 left-0 right-0 flex justify-center gap-3">
            <button
              type="button"
              onClick={capturePhoto}
              className="rounded-full bg-white p-4 shadow-lg active:scale-95"
              data-testid="capture-button"
            >
              <Camera className="h-6 w-6 text-gray-900" />
            </button>
            <button
              type="button"
              onClick={stopCamera}
              className="rounded-full bg-red-500 p-4 shadow-lg active:scale-95"
            >
              <X className="h-6 w-6 text-white" />
            </button>
          </div>
        </div>
      )}

      {/* Photo grid */}
      <div className="grid grid-cols-3 gap-2">
        {photos.map((photo, idx) => (
          <div key={idx} className="group relative aspect-square overflow-hidden rounded-lg">
            <img src={photo.uri} alt={`Photo ${idx + 1}`} className="h-full w-full object-cover" />
            <button
              type="button"
              onClick={() => onRemove(idx)}
              className="absolute right-1 top-1 rounded-full bg-black/50 p-1 text-white opacity-0 transition group-hover:opacity-100"
              data-testid={`remove-photo-${idx}`}
            >
              <X className="h-3 w-3" />
            </button>
          </div>
        ))}

        {canAdd && !isCapturing && (
          <button
            type="button"
            onClick={startCamera}
            data-testid="add-photo-button"
            className="flex aspect-square flex-col items-center justify-center gap-1 rounded-lg border-2 border-dashed border-gray-300 text-gray-500 transition hover:border-indigo-400 hover:text-indigo-500 dark:border-gray-600 dark:text-gray-400"
          >
            <Camera className="h-6 w-6" />
            <span className="text-xs">{t('observation.add_photo') || 'Add'}</span>
          </button>
        )}
      </div>

      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        capture="environment"
        multiple
        onChange={handleFileSelect}
        className="hidden"
        data-testid="file-input"
      />

      {!isCapturing && canAdd && (
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          className="mt-2 flex w-full items-center justify-center gap-2 rounded-lg border border-gray-300 px-4 py-2.5 text-sm text-gray-700 transition hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
        >
          <Image className="h-4 w-4" />
          {t('observation.upload_from_gallery') || 'Upload from gallery'}
        </button>
      )}
    </div>
  );
});

import { useState, useRef, useCallback } from 'react';
import { Upload, X, FileIcon, AlertCircle, Loader2 } from 'lucide-react';
import { useTranslation } from '@/i18n';
import { cn } from '@/utils/formatters';

interface FileUploadProps {
  onUpload: (file: File) => void;
  accept?: string;
  maxSizeMB?: number;
  isLoading?: boolean;
}

export function FileUpload({ onUpload, accept, maxSizeMB = 50, isLoading = false }: FileUploadProps) {
  const { t } = useTranslation();
  const inputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);

  const maxSizeBytes = maxSizeMB * 1024 * 1024;

  const validateFile = useCallback(
    (file: File): boolean => {
      setError(null);

      // Check file size
      if (file.size > maxSizeBytes) {
        setError(t('form.error') + ` (Max. ${maxSizeMB} MB)`);
        return false;
      }

      // Check file type if accept is specified
      if (accept) {
        const acceptedTypes = accept.split(',').map((t) => t.trim());
        const fileExtension = '.' + file.name.split('.').pop()?.toLowerCase();
        const matchesType = acceptedTypes.some(
          (acceptType) =>
            acceptType === file.type ||
            acceptType === fileExtension ||
            (acceptType.endsWith('/*') && file.type.startsWith(acceptType.replace('/*', '/'))),
        );
        if (!matchesType) {
          setError(t('form.error') + ` (${accept})`);
          return false;
        }
      }

      return true;
    },
    [accept, maxSizeBytes, maxSizeMB, t],
  );

  const handleFile = useCallback(
    (file: File) => {
      if (validateFile(file)) {
        setSelectedFile(file);
        onUpload(file);
      }
    },
    [validateFile, onUpload],
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragging(false);

      const file = e.dataTransfer.files?.[0];
      if (file) {
        handleFile(file);
      }
    },
    [handleFile],
  );

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) {
        handleFile(file);
      }
      // Reset input so the same file can be selected again
      e.target.value = '';
    },
    [handleFile],
  );

  const clearFile = useCallback(() => {
    setSelectedFile(null);
    setError(null);
  }, []);

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="w-full">
      {/* Drop zone */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => !isLoading && inputRef.current?.click()}
        onKeyDown={(e) => {
          if ((e.key === 'Enter' || e.key === ' ') && !isLoading) {
            e.preventDefault();
            inputRef.current?.click();
          }
        }}
        role="button"
        tabIndex={0}
        aria-label={t('form.upload')}
        className={cn(
          'relative flex flex-col items-center justify-center px-6 py-10 border-2 border-dashed rounded-xl cursor-pointer transition-all duration-200',
          isDragging
            ? 'border-red-400 bg-red-50'
            : 'border-slate-300 dark:border-slate-600 bg-slate-50 dark:bg-slate-800 hover:border-slate-400 dark:hover:border-slate-500 hover:bg-slate-100 dark:hover:bg-slate-700',
          isLoading && 'pointer-events-none opacity-60',
        )}
      >
        <input
          ref={inputRef}
          type="file"
          accept={accept}
          onChange={handleInputChange}
          className="hidden"
          disabled={isLoading}
        />

        {isLoading ? (
          <>
            <Loader2 className="w-10 h-10 text-red-500 animate-spin mb-3" />
            <p className="text-sm font-medium text-slate-700">{t('form.loading')}</p>
          </>
        ) : (
          <>
            <div className="w-12 h-12 rounded-full bg-slate-200 dark:bg-slate-600 flex items-center justify-center mb-3">
              <Upload className="w-6 h-6 text-slate-500 dark:text-slate-300" />
            </div>
            <p className="text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">{t('form.upload')}</p>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              {accept && `${accept} | `}Max. {maxSizeMB} MB
            </p>
          </>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="flex items-center gap-2 mt-3 px-3 py-2 bg-red-50 border border-red-200 rounded-lg">
          <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0" />
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      {/* Selected file preview */}
      {selectedFile && !error && (
        <div className="flex items-center gap-3 mt-3 px-4 py-3 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg">
          <FileIcon className="w-5 h-5 text-slate-400 dark:text-slate-500 flex-shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-slate-700 dark:text-slate-200 truncate">{selectedFile.name}</p>
            <p className="text-xs text-slate-500 dark:text-slate-400">{formatFileSize(selectedFile.size)}</p>
          </div>
          <button
            onClick={(e) => {
              e.stopPropagation();
              clearFile();
            }}
            className="p-1 text-slate-400 hover:text-slate-600 rounded transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}
    </div>
  );
}

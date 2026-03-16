import { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import { useTranslation } from '@/i18n';
import { formatDate, cn } from '@/utils/formatters';
import { useBuildings } from '@/hooks/useBuildings';
import { useDebouncedValue } from '@/hooks/useDebouncedValue';
import { documentsApi } from '@/api/documents';
import { toast } from '@/store/toastStore';
import { DataTable } from '@/components/DataTable';
import type { Building } from '@/types';
import {
  FileText,
  Download,
  Loader2,
  Search,
  Upload,
  X,
  File,
  Image,
  FileSpreadsheet,
  FileArchive,
  ShieldCheck,
  ShieldX,
  LayoutGrid,
  List,
  Eye,
  AlertCircle,
  CheckCircle2,
  Clock,
} from 'lucide-react';
import type { DocumentProcessingMetadata } from '@/types';

// ── Types ──────────────────────────────────────────────────────────────────────

interface DocFile {
  id: string;
  building_id: string;
  file_path: string;
  file_name: string;
  file_size_bytes: number | null;
  mime_type: string | null;
  document_type: string;
  description: string | null;
  uploaded_by: string;
  processing_metadata: DocumentProcessingMetadata | null;
  created_at: string;
  building_address?: string;
}

type ViewMode = 'list' | 'grid';
type DocStatus = 'processing' | 'ready' | 'error';

interface UploadQueueItem {
  id: string;
  file: File;
  documentType: string;
  description: string;
  progress: number; // 0-100
  status: 'pending' | 'uploading' | 'done' | 'error';
  error?: string;
}

// ── Constants ──────────────────────────────────────────────────────────────────

const DOCUMENT_TYPES = [
  'diagnostic_report',
  'lab_analysis',
  'plan',
  'photo',
  'permit',
  'notification',
  'invoice',
  'other',
] as const;

const fileTypeConfig: Record<string, { icon: React.ElementType; color: string; bg: string }> = {
  pdf: { icon: FileText, color: 'text-red-600', bg: 'bg-red-50 dark:bg-red-900/30' },
  doc: { icon: FileText, color: 'text-blue-600', bg: 'bg-blue-50 dark:bg-blue-900/30' },
  docx: { icon: FileText, color: 'text-blue-600', bg: 'bg-blue-50 dark:bg-blue-900/30' },
  xls: { icon: FileSpreadsheet, color: 'text-green-600', bg: 'bg-green-50 dark:bg-green-900/30' },
  xlsx: { icon: FileSpreadsheet, color: 'text-green-600', bg: 'bg-green-50 dark:bg-green-900/30' },
  jpg: { icon: Image, color: 'text-purple-600', bg: 'bg-purple-50 dark:bg-purple-900/30' },
  jpeg: { icon: Image, color: 'text-purple-600', bg: 'bg-purple-50 dark:bg-purple-900/30' },
  png: { icon: Image, color: 'text-purple-600', bg: 'bg-purple-50 dark:bg-purple-900/30' },
  zip: { icon: FileArchive, color: 'text-yellow-600', bg: 'bg-yellow-50 dark:bg-yellow-900/30' },
};

// ── Helpers ────────────────────────────────────────────────────────────────────

function getFileType(name: string): string {
  return name.split('.').pop()?.toLowerCase() || 'file';
}

function formatSize(bytes: number): string {
  if (!bytes) return '-';
  const units = ['B', 'KB', 'MB', 'GB'];
  let i = 0;
  let size = bytes;
  while (size >= 1024 && i < units.length - 1) {
    size /= 1024;
    i++;
  }
  return `${size.toFixed(1)} ${units[i]}`;
}

function getFileIconConfig(fileName: string) {
  const ext = getFileType(fileName);
  return (
    fileTypeConfig[ext] || {
      icon: File,
      color: 'text-gray-600',
      bg: 'bg-gray-50 dark:bg-slate-700',
    }
  );
}

function getDocStatus(doc: DocFile): DocStatus {
  const meta = doc.processing_metadata;
  if (!meta) return 'ready';
  if (meta.virus_scan && !meta.virus_scan.clean) return 'error';
  return 'ready';
}

function isPreviewable(mimeType: string | null): boolean {
  if (!mimeType) return false;
  return mimeType.startsWith('image/') || mimeType === 'application/pdf';
}

let _queueId = 0;
function nextQueueId(): string {
  _queueId += 1;
  return `uq-${_queueId}`;
}

// ── Status Badge Component ─────────────────────────────────────────────────────

function StatusBadge({ status, t }: { status: DocStatus; t: (k: string) => string }) {
  const config = {
    processing: {
      icon: Clock,
      label: t('document.status_processing'),
      cls: 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300',
    },
    ready: {
      icon: CheckCircle2,
      label: t('document.status_ready'),
      cls: 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300',
    },
    error: {
      icon: AlertCircle,
      label: t('document.status_error'),
      cls: 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300',
    },
  }[status];
  const Icon = config.icon;
  return (
    <span className={cn('inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full', config.cls)}>
      <Icon className="w-3 h-3" />
      {config.label}
    </span>
  );
}

// ── Grid Card Component ────────────────────────────────────────────────────────

function DocumentCard({
  doc,
  t,
  onDownload,
  onSelect,
  isSelected,
}: {
  doc: DocFile;
  t: (k: string) => string;
  onDownload: (id: string) => void;
  onSelect: (doc: DocFile) => void;
  isSelected: boolean;
}) {
  const config = getFileIconConfig(doc.file_name);
  const Icon = config.icon;
  const status = getDocStatus(doc);
  const ext = getFileType(doc.file_name);

  return (
    <div
      onClick={() => onSelect(doc)}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onSelect(doc);
        }
      }}
      role="button"
      tabIndex={0}
      className={cn(
        'group relative flex flex-col rounded-xl border bg-white dark:bg-slate-800 p-4 cursor-pointer transition-all hover:shadow-md',
        isSelected
          ? 'border-red-500 ring-2 ring-red-500/20'
          : 'border-gray-200 dark:border-slate-700 hover:border-gray-300 dark:hover:border-slate-600',
      )}
    >
      {/* Thumbnail area */}
      <div className={cn('w-full h-24 rounded-lg flex items-center justify-center mb-3', config.bg)}>
        <Icon className={cn('w-10 h-10', config.color)} />
      </div>

      {/* File name */}
      <p className="text-sm font-medium text-gray-900 dark:text-white truncate" title={doc.file_name}>
        {doc.file_name}
      </p>

      {/* Meta row */}
      <div className="flex items-center justify-between mt-2">
        <span className="px-2 py-0.5 text-[10px] font-semibold bg-gray-100 dark:bg-slate-700 text-gray-500 dark:text-slate-400 rounded-full uppercase">
          {ext}
        </span>
        <StatusBadge status={status} t={t} />
      </div>

      {/* Size + date */}
      <div className="flex items-center justify-between mt-2 text-xs text-gray-400 dark:text-slate-500">
        <span className="font-mono">{formatSize(doc.file_size_bytes ?? 0)}</span>
        <span>{formatDate(doc.created_at)}</span>
      </div>

      {/* Processing badges */}
      {doc.processing_metadata && (
        <div className="flex items-center gap-1.5 mt-2">
          {doc.processing_metadata.virus_scan && (
            <span
              title={
                doc.processing_metadata.virus_scan.clean
                  ? doc.processing_metadata.virus_scan.message === 'scanning_disabled'
                    ? t('document.scan_disabled')
                    : t('document.scan_clean')
                  : t('document.scan_infected')
              }
            >
              {doc.processing_metadata.virus_scan.clean ? (
                <ShieldCheck className="w-3.5 h-3.5 text-green-500" />
              ) : (
                <ShieldX className="w-3.5 h-3.5 text-red-500" />
              )}
            </span>
          )}
          {doc.processing_metadata.ocr?.applied && (
            <span
              className="px-1.5 py-0.5 text-[9px] font-semibold bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 rounded"
              title={t('document.ocr_applied')}
            >
              OCR
            </span>
          )}
        </div>
      )}

      {/* Hover download button */}
      <button
        onClick={(e) => {
          e.stopPropagation();
          onDownload(doc.id);
        }}
        className="absolute top-3 right-3 p-1.5 bg-white dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg shadow-sm opacity-0 group-hover:opacity-100 transition-opacity hover:bg-gray-50 dark:hover:bg-slate-600"
        title={t('document.download')}
        aria-label={t('document.download')}
      >
        <Download className="w-3.5 h-3.5 text-gray-500 dark:text-slate-400" />
      </button>
    </div>
  );
}

// ── Detail Panel Component ─────────────────────────────────────────────────────

function DetailPanel({
  doc,
  t,
  onClose,
  onDownload,
  onPreview,
}: {
  doc: DocFile;
  t: (k: string, p?: Record<string, string | number>) => string;
  onClose: () => void;
  onDownload: (id: string) => void;
  onPreview: (doc: DocFile) => void;
}) {
  const config = getFileIconConfig(doc.file_name);
  const Icon = config.icon;
  const status = getDocStatus(doc);

  return (
    <div className="bg-white dark:bg-slate-800 border-l border-gray-200 dark:border-slate-700 w-full lg:w-96 flex-shrink-0 overflow-y-auto">
      {/* Header */}
      <div className="sticky top-0 bg-white dark:bg-slate-800 border-b border-gray-200 dark:border-slate-700 px-4 py-3 flex items-center justify-between z-10">
        <h3 className="text-sm font-semibold text-gray-900 dark:text-white">{t('document.detail_panel')}</h3>
        <button
          onClick={onClose}
          className="p-1 hover:bg-gray-100 dark:hover:bg-slate-700 rounded-lg"
          aria-label={t('form.close')}
        >
          <X className="w-4 h-4 text-gray-500 dark:text-slate-400" />
        </button>
      </div>

      <div className="p-4 space-y-5">
        {/* File icon + name */}
        <div className="flex items-start gap-3">
          <div className={cn('w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0', config.bg)}>
            <Icon className={cn('w-6 h-6', config.color)} />
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-sm font-semibold text-gray-900 dark:text-white break-all">{doc.file_name}</p>
            <p className="text-xs text-gray-500 dark:text-slate-400 mt-0.5 font-mono">
              {formatSize(doc.file_size_bytes ?? 0)}
            </p>
          </div>
        </div>

        {/* Status */}
        <div>
          <label className="text-xs font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wider">
            {t('document.status')}
          </label>
          <div className="mt-1">
            <StatusBadge status={status} t={t} />
          </div>
        </div>

        {/* Document type */}
        <div>
          <label className="text-xs font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wider">
            {t('document.type')}
          </label>
          <p className="mt-1 text-sm text-gray-900 dark:text-white">
            {t(`document_type.${doc.document_type}`) || doc.document_type}
          </p>
        </div>

        {/* Description */}
        <div>
          <label className="text-xs font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wider">
            {t('document.description')}
          </label>
          <p className="mt-1 text-sm text-gray-700 dark:text-slate-300">{doc.description || '-'}</p>
        </div>

        {/* Uploaded by */}
        <div>
          <label className="text-xs font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wider">
            {t('document.uploaded_by')}
          </label>
          <p className="mt-1 text-sm text-gray-900 dark:text-white">{doc.uploaded_by}</p>
        </div>

        {/* Date */}
        <div>
          <label className="text-xs font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wider">
            {t('document.created_at')}
          </label>
          <p className="mt-1 text-sm text-gray-900 dark:text-white">{formatDate(doc.created_at)}</p>
        </div>

        {/* Processing metadata */}
        {doc.processing_metadata && (
          <div className="pt-2 border-t border-gray-100 dark:border-slate-700 space-y-2">
            {doc.processing_metadata.virus_scan && (
              <div className="flex items-center gap-2">
                {doc.processing_metadata.virus_scan.clean ? (
                  <ShieldCheck className="w-4 h-4 text-green-500" />
                ) : (
                  <ShieldX className="w-4 h-4 text-red-500" />
                )}
                <span className="text-xs text-gray-600 dark:text-slate-300">
                  {doc.processing_metadata.virus_scan.clean
                    ? doc.processing_metadata.virus_scan.message === 'scanning_disabled'
                      ? t('document.scan_disabled')
                      : t('document.scan_clean')
                    : t('document.scan_infected')}
                </span>
              </div>
            )}
            {doc.processing_metadata.ocr && (
              <div className="flex items-center gap-2">
                <span className="px-1.5 py-0.5 text-[10px] font-semibold bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 rounded">
                  OCR
                </span>
                <span className="text-xs text-gray-600 dark:text-slate-300">
                  {doc.processing_metadata.ocr.applied ? t('document.ocr_applied') : t('document.ocr_not_applicable')}
                </span>
              </div>
            )}
          </div>
        )}

        {/* Action buttons */}
        <div className="flex gap-2 pt-2">
          {isPreviewable(doc.mime_type) && (
            <button
              onClick={() => onPreview(doc)}
              className="flex-1 inline-flex items-center justify-center gap-2 px-3 py-2 text-sm font-medium text-gray-700 dark:text-slate-200 bg-gray-100 dark:bg-slate-700 rounded-lg hover:bg-gray-200 dark:hover:bg-slate-600 transition-colors"
            >
              <Eye className="w-4 h-4" />
              {t('document.quick_preview')}
            </button>
          )}
          <button
            onClick={() => onDownload(doc.id)}
            className="flex-1 inline-flex items-center justify-center gap-2 px-3 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors"
          >
            <Download className="w-4 h-4" />
            {t('document.download')}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Preview Modal Component ────────────────────────────────────────────────────

function PreviewModal({
  doc,
  downloadUrl,
  t,
  onClose,
}: {
  doc: DocFile;
  downloadUrl: string | null;
  t: (k: string) => string;
  onClose: () => void;
}) {
  const isImage = doc.mime_type?.startsWith('image/');

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm" onClick={onClose}>
      <div
        className="relative bg-white dark:bg-slate-800 rounded-2xl shadow-2xl w-full max-w-4xl max-h-[90vh] mx-4 overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-slate-700">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-white truncate">{doc.file_name}</h3>
          <button
            onClick={onClose}
            className="p-1 hover:bg-gray-100 dark:hover:bg-slate-700 rounded-lg"
            aria-label={t('form.close')}
          >
            <X className="w-5 h-5 text-gray-500 dark:text-slate-400" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto flex items-center justify-center p-4 bg-gray-50 dark:bg-slate-900 min-h-[400px]">
          {!downloadUrl ? (
            <Loader2 className="w-8 h-8 animate-spin text-red-600" />
          ) : isImage ? (
            <img src={downloadUrl} alt={doc.file_name} className="max-w-full max-h-full object-contain rounded" />
          ) : (
            <iframe src={downloadUrl} className="w-full h-full min-h-[500px] rounded" title={doc.file_name} />
          )}
        </div>
      </div>
    </div>
  );
}

// ── Upload Modal Component ─────────────────────────────────────────────────────

function UploadModal({
  buildings,
  t,
  onClose,
  onUploadComplete,
}: {
  buildings: Building[];
  t: (k: string, p?: Record<string, string | number>) => string;
  onClose: () => void;
  onUploadComplete: () => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [uploadBuildingId, setUploadBuildingId] = useState('');
  const [queue, setQueue] = useState<UploadQueueItem[]>([]);
  const [isUploading, setIsUploading] = useState(false);

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

  const addFiles = useCallback((files: FileList | File[]) => {
    const maxSizeBytes = 50 * 1024 * 1024;
    const newItems: UploadQueueItem[] = [];
    for (const file of Array.from(files)) {
      if (file.size > maxSizeBytes) continue;
      newItems.push({
        id: nextQueueId(),
        file,
        documentType: 'other',
        description: '',
        progress: 0,
        status: 'pending',
      });
    }
    setQueue((prev) => [...prev, ...newItems]);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragging(false);
      if (e.dataTransfer.files?.length) {
        addFiles(e.dataTransfer.files);
      }
    },
    [addFiles],
  );

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      if (e.target.files?.length) {
        addFiles(e.target.files);
      }
      e.target.value = '';
    },
    [addFiles],
  );

  const updateQueueItem = useCallback((id: string, patch: Partial<UploadQueueItem>) => {
    setQueue((prev) => prev.map((item) => (item.id === id ? { ...item, ...patch } : item)));
  }, []);

  const removeQueueItem = useCallback((id: string) => {
    setQueue((prev) => prev.filter((item) => item.id !== id));
  }, []);

  const handleUploadAll = useCallback(async () => {
    if (!uploadBuildingId || queue.length === 0) return;
    setIsUploading(true);

    for (const item of queue) {
      if (item.status === 'done') continue;
      updateQueueItem(item.id, { status: 'uploading', progress: 30 });
      try {
        await documentsApi.upload(uploadBuildingId, item.file, item.documentType, item.description || undefined);
        updateQueueItem(item.id, { status: 'done', progress: 100 });
      } catch (err: any) {
        updateQueueItem(item.id, {
          status: 'error',
          error: err?.response?.data?.detail || err?.message || 'Upload failed',
          progress: 0,
        });
      }
    }

    setIsUploading(false);
    onUploadComplete();
  }, [uploadBuildingId, queue, updateQueueItem, onUploadComplete]);

  const pendingCount = queue.filter((i) => i.status === 'pending' || i.status === 'error').length;
  const allDone = queue.length > 0 && queue.every((i) => i.status === 'done');

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl w-full max-w-lg mx-4 max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 pt-6 pb-4">
          <h2 className="text-lg font-bold text-gray-900 dark:text-white">{t('document.upload')}</h2>
          <button
            onClick={onClose}
            className="p-1 hover:bg-gray-100 dark:hover:bg-slate-600 rounded-lg"
            aria-label={t('form.close')}
          >
            <X className="w-5 h-5 text-gray-500 dark:text-slate-400" />
          </button>
        </div>

        <div className="px-6 pb-6 space-y-4 overflow-y-auto">
          {/* Building selector */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">
              {t('building.title')} *
            </label>
            <select
              value={uploadBuildingId}
              onChange={(e) => setUploadBuildingId(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
            >
              <option value="">{t('form.select_option')}</option>
              {buildings.map((b) => (
                <option key={b.id} value={b.id}>
                  {b.address}, {b.city}
                </option>
              ))}
            </select>
          </div>

          {/* Drop zone */}
          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => !isUploading && inputRef.current?.click()}
            onKeyDown={(e) => {
              if ((e.key === 'Enter' || e.key === ' ') && !isUploading) {
                e.preventDefault();
                inputRef.current?.click();
              }
            }}
            role="button"
            tabIndex={0}
            aria-label={t('form.upload')}
            className={cn(
              'relative flex flex-col items-center justify-center px-6 py-8 border-2 border-dashed rounded-xl cursor-pointer transition-all duration-200',
              isDragging
                ? 'border-red-400 bg-red-50 dark:bg-red-900/20'
                : 'border-gray-300 dark:border-slate-600 bg-gray-50 dark:bg-slate-700/50 hover:border-gray-400 dark:hover:border-slate-500',
              isUploading && 'pointer-events-none opacity-60',
            )}
          >
            <input
              ref={inputRef}
              type="file"
              multiple
              onChange={handleInputChange}
              className="hidden"
              disabled={isUploading}
            />

            {isDragging ? (
              <>
                <Upload className="w-10 h-10 text-red-500 mb-2" />
                <p className="text-sm font-medium text-red-600 dark:text-red-400">{t('document.drop_zone_active')}</p>
              </>
            ) : (
              <>
                <div className="w-12 h-12 rounded-full bg-gray-200 dark:bg-slate-600 flex items-center justify-center mb-3">
                  <Upload className="w-6 h-6 text-gray-500 dark:text-slate-300" />
                </div>
                <p className="text-sm font-medium text-gray-700 dark:text-slate-200">{t('document.drop_zone_title')}</p>
                <p className="text-xs text-gray-500 dark:text-slate-400 mt-1">{t('document.drop_zone_subtitle')}</p>
                <p className="text-xs text-gray-400 dark:text-slate-500 mt-1">
                  {t('document.drop_zone_hint', { max: '50' })}
                </p>
              </>
            )}
          </div>

          {/* Upload queue */}
          {queue.length > 0 && (
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-semibold text-gray-500 dark:text-slate-400 uppercase tracking-wider">
                  {t('document.upload_queue')} ({queue.length})
                </h4>
                {!isUploading && (
                  <button
                    onClick={() => setQueue([])}
                    className="text-xs text-gray-400 hover:text-gray-600 dark:hover:text-slate-300"
                  >
                    {t('document.clear_queue')}
                  </button>
                )}
              </div>

              <div className="max-h-48 overflow-y-auto space-y-2">
                {queue.map((item) => {
                  const itemConfig = getFileIconConfig(item.file.name);
                  const ItemIcon = itemConfig.icon;
                  return (
                    <div
                      key={item.id}
                      className="flex items-center gap-3 px-3 py-2.5 bg-gray-50 dark:bg-slate-700/50 rounded-lg"
                    >
                      <div
                        className={cn(
                          'w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0',
                          itemConfig.bg,
                        )}
                      >
                        <ItemIcon className={cn('w-4 h-4', itemConfig.color)} />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-800 dark:text-slate-200 truncate">
                          {item.file.name}
                        </p>
                        <div className="flex items-center gap-2 mt-0.5">
                          <span className="text-xs text-gray-400 dark:text-slate-500 font-mono">
                            {formatSize(item.file.size)}
                          </span>
                          {/* Document type selector */}
                          {item.status === 'pending' && (
                            <select
                              value={item.documentType}
                              onChange={(e) => updateQueueItem(item.id, { documentType: e.target.value })}
                              className="text-xs px-1.5 py-0.5 border border-gray-200 dark:border-slate-600 rounded bg-white dark:bg-slate-700 dark:text-slate-300 focus:outline-none"
                              onClick={(e) => e.stopPropagation()}
                            >
                              {DOCUMENT_TYPES.map((dt) => (
                                <option key={dt} value={dt}>
                                  {t(`document_type.${dt}`)}
                                </option>
                              ))}
                            </select>
                          )}
                        </div>
                        {/* Description input */}
                        {item.status === 'pending' && (
                          <input
                            type="text"
                            value={item.description}
                            onChange={(e) => updateQueueItem(item.id, { description: e.target.value })}
                            placeholder={t('document.description')}
                            className="mt-1 w-full text-xs px-2 py-1 border border-gray-200 dark:border-slate-600 rounded bg-white dark:bg-slate-700 dark:text-slate-300 placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-red-500"
                          />
                        )}
                        {/* Progress bar */}
                        {item.status === 'uploading' && (
                          <div className="mt-1 w-full h-1.5 bg-gray-200 dark:bg-slate-600 rounded-full overflow-hidden">
                            <div
                              className="h-full bg-red-500 rounded-full transition-all duration-300"
                              style={{ width: `${item.progress}%` }}
                            />
                          </div>
                        )}
                        {/* Error */}
                        {item.status === 'error' && <p className="mt-0.5 text-xs text-red-500">{item.error}</p>}
                      </div>
                      {/* Status indicator / remove */}
                      <div className="flex-shrink-0">
                        {item.status === 'done' ? (
                          <CheckCircle2 className="w-4 h-4 text-green-500" />
                        ) : item.status === 'uploading' ? (
                          <Loader2 className="w-4 h-4 animate-spin text-red-500" />
                        ) : item.status === 'error' ? (
                          <button onClick={() => removeQueueItem(item.id)} className="p-0.5">
                            <AlertCircle className="w-4 h-4 text-red-500" />
                          </button>
                        ) : (
                          <button
                            onClick={() => removeQueueItem(item.id)}
                            className="p-0.5 text-gray-400 hover:text-gray-600 dark:hover:text-slate-300"
                          >
                            <X className="w-3.5 h-3.5" />
                          </button>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Upload button */}
          <div className="flex justify-end gap-2 pt-2">
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-slate-300 bg-gray-100 dark:bg-slate-700 rounded-lg hover:bg-gray-200 dark:hover:bg-slate-600 transition-colors"
            >
              {allDone ? t('form.close') : t('form.cancel')}
            </button>
            {!allDone && (
              <button
                onClick={handleUploadAll}
                disabled={!uploadBuildingId || pendingCount === 0 || isUploading}
                className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {isUploading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    {t('document.upload_progress')}
                  </>
                ) : (
                  <>
                    <Upload className="w-4 h-4" />
                    {t('document.upload_confirm')} ({pendingCount})
                  </>
                )}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Main Page Component ────────────────────────────────────────────────────────

export default function Documents() {
  const { t } = useTranslation();
  const { data: buildingsData } = useBuildings();
  const buildings: Building[] = useMemo(() => buildingsData?.items ?? [], [buildingsData]);

  const [documents, setDocuments] = useState<DocFile[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [search, setSearch] = useState('');
  const debouncedSearch = useDebouncedValue(search, 300);
  const [filterBuildingId, setFilterBuildingId] = useState('');
  const [filterDocType, setFilterDocType] = useState('');
  const [filterStatus, setFilterStatus] = useState('');
  const [filterDateFrom, setFilterDateFrom] = useState('');
  const [filterDateTo, setFilterDateTo] = useState('');
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [viewMode, setViewMode] = useState<ViewMode>('list');
  const [selectedDoc, setSelectedDoc] = useState<DocFile | null>(null);
  const [previewDoc, setPreviewDoc] = useState<DocFile | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  // Fetch documents
  const fetchDocuments = useCallback(async () => {
    setIsLoading(true);
    try {
      if (filterBuildingId) {
        const data = await documentsApi.listByBuilding(filterBuildingId);
        setDocuments(Array.isArray(data) ? data : []);
      } else if (Array.isArray(buildings) && buildings.length > 0) {
        const results = await Promise.all(buildings.map((b) => documentsApi.listByBuilding(b.id).catch(() => [])));
        setDocuments(results.flat());
      } else {
        setDocuments([]);
      }
    } catch (err: any) {
      toast(err?.message || t('app.error'));
      setDocuments([]);
    } finally {
      setIsLoading(false);
    }
  }, [filterBuildingId, buildings, t]);

  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  // Filter documents
  const filteredDocuments = useMemo(() => {
    return documents.filter((doc) => {
      // Text search
      if (debouncedSearch) {
        const q = debouncedSearch.toLowerCase();
        const matchesSearch =
          doc.file_name?.toLowerCase().includes(q) ||
          doc.uploaded_by?.toLowerCase().includes(q) ||
          doc.building_address?.toLowerCase().includes(q) ||
          doc.description?.toLowerCase().includes(q);
        if (!matchesSearch) return false;
      }

      // Document type filter
      if (filterDocType && doc.document_type !== filterDocType) return false;

      // Status filter
      if (filterStatus) {
        const status = getDocStatus(doc);
        if (status !== filterStatus) return false;
      }

      // Date range filter
      if (filterDateFrom) {
        const docDate = new Date(doc.created_at).getTime();
        const from = new Date(filterDateFrom).getTime();
        if (docDate < from) return false;
      }
      if (filterDateTo) {
        const docDate = new Date(doc.created_at).getTime();
        const to = new Date(filterDateTo).getTime() + 86400000; // include the full day
        if (docDate > to) return false;
      }

      return true;
    });
  }, [documents, debouncedSearch, filterDocType, filterStatus, filterDateFrom, filterDateTo]);

  const handleDownload = useCallback(async (docId: string) => {
    try {
      const url = await documentsApi.getDownloadUrl(docId);
      if (url) window.open(url, '_blank');
    } catch (err: any) {
      toast(err?.response?.data?.detail || err?.message || 'Download failed');
    }
  }, []);

  const handlePreview = useCallback(async (doc: DocFile) => {
    setPreviewDoc(doc);
    setPreviewUrl(null);
    try {
      const url = await documentsApi.getDownloadUrl(doc.id);
      setPreviewUrl(url);
    } catch (err: any) {
      toast(err?.response?.data?.detail || err?.message || 'Preview failed');
      setPreviewDoc(null);
    }
  }, []);

  const handleSelectDoc = useCallback((doc: DocFile) => {
    setSelectedDoc((prev) => (prev?.id === doc.id ? null : doc));
  }, []);

  const hasActiveFilters = filterDocType || filterStatus || filterDateFrom || filterDateTo;

  // ── Table columns ─────────────────────────────────────────────────────────

  const columns = useMemo(
    () => [
      {
        key: 'file_name',
        header: t('document.file_name'),
        sortable: true,
        render: (row: DocFile) => {
          const config = getFileIconConfig(row.file_name);
          const Icon = config.icon;
          return (
            <div className="flex items-center gap-2">
              <div className={cn('w-8 h-8 rounded-lg flex items-center justify-center', config.bg)}>
                <Icon className={cn('w-4 h-4', config.color)} />
              </div>
              <span className="text-sm font-medium text-gray-900 dark:text-white truncate max-w-[200px]">
                {row.file_name}
              </span>
            </div>
          );
        },
      },
      {
        key: 'document_type',
        header: t('document.type'),
        render: (row: DocFile) => {
          const ext = getFileType(row.file_name);
          return (
            <span className="px-2 py-0.5 text-xs font-medium bg-gray-100 dark:bg-slate-700 text-gray-600 dark:text-slate-300 rounded-full uppercase">
              {ext}
            </span>
          );
        },
      },
      {
        key: 'status',
        header: t('document.status'),
        render: (row: DocFile) => <StatusBadge status={getDocStatus(row)} t={t} />,
      },
      {
        key: 'uploaded_by',
        header: t('document.uploaded_by'),
        sortable: true,
      },
      {
        key: 'created_at',
        header: t('document.created_at'),
        sortable: true,
        render: (row: DocFile) => (
          <span className="text-sm text-gray-500 dark:text-slate-400">{formatDate(row.created_at)}</span>
        ),
      },
      {
        key: 'file_size_bytes',
        header: t('document.file_size'),
        sortable: true,
        render: (row: DocFile) => (
          <span className="text-sm text-gray-500 dark:text-slate-400 font-mono">
            {formatSize(row.file_size_bytes ?? 0)}
          </span>
        ),
      },
      {
        key: 'processing',
        header: '',
        render: (row: DocFile) => {
          const meta = row.processing_metadata;
          if (!meta) return null;
          const scan = meta.virus_scan;
          const ocr = meta.ocr;
          return (
            <div className="flex items-center gap-1.5">
              {scan && (
                <span
                  title={
                    scan.clean
                      ? scan.message === 'scanning_disabled'
                        ? t('document.scan_disabled')
                        : t('document.scan_clean')
                      : t('document.scan_infected')
                  }
                >
                  {scan.clean ? (
                    <ShieldCheck className="w-4 h-4 text-green-500" />
                  ) : (
                    <ShieldX className="w-4 h-4 text-red-500" />
                  )}
                </span>
              )}
              {ocr?.applied && (
                <span
                  className="px-1.5 py-0.5 text-[10px] font-semibold bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 rounded"
                  title={t('document.ocr_applied')}
                >
                  OCR
                </span>
              )}
            </div>
          );
        },
      },
      {
        key: 'actions',
        header: '',
        render: (row: DocFile) => (
          <div className="flex items-center gap-1">
            {isPreviewable(row.mime_type) && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handlePreview(row);
                }}
                className="p-1.5 text-gray-400 dark:text-slate-500 hover:text-gray-600 hover:bg-gray-100 dark:hover:bg-slate-600 rounded-lg transition-colors"
                title={t('document.quick_preview')}
                aria-label={t('document.quick_preview')}
              >
                <Eye className="w-4 h-4" />
              </button>
            )}
            <button
              onClick={(e) => {
                e.stopPropagation();
                handleDownload(row.id);
              }}
              className="p-1.5 text-gray-400 dark:text-slate-500 hover:text-gray-600 hover:bg-gray-100 dark:hover:bg-slate-600 rounded-lg transition-colors"
              title={t('document.download')}
              aria-label={t('document.download')}
            >
              <Download className="w-4 h-4" />
            </button>
          </div>
        ),
      },
    ],
    [t, handleDownload, handlePreview],
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{t('document.title')}</h1>
          <p className="text-sm text-gray-500 dark:text-slate-400 mt-1">
            {filteredDocuments.length} {t('document.title').toLowerCase()}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {/* View mode toggle */}
          <div className="flex items-center bg-gray-100 dark:bg-slate-700 rounded-lg p-0.5">
            <button
              onClick={() => setViewMode('list')}
              className={cn(
                'p-1.5 rounded-md transition-colors',
                viewMode === 'list'
                  ? 'bg-white dark:bg-slate-600 shadow-sm text-gray-900 dark:text-white'
                  : 'text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-200',
              )}
              title={t('document.list_view')}
              aria-label={t('document.list_view')}
            >
              <List className="w-4 h-4" />
            </button>
            <button
              onClick={() => setViewMode('grid')}
              className={cn(
                'p-1.5 rounded-md transition-colors',
                viewMode === 'grid'
                  ? 'bg-white dark:bg-slate-600 shadow-sm text-gray-900 dark:text-white'
                  : 'text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-200',
              )}
              title={t('document.grid_view')}
              aria-label={t('document.grid_view')}
            >
              <LayoutGrid className="w-4 h-4" />
            </button>
          </div>

          <button
            onClick={() => setShowUploadModal(true)}
            className="inline-flex items-center gap-2 px-4 py-2 bg-red-600 text-white text-sm font-medium rounded-lg hover:bg-red-700 transition-colors"
          >
            <Upload className="w-4 h-4" />
            {t('document.upload')}
          </button>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-4 shadow-sm">
        <div className="flex flex-wrap items-center gap-3">
          {/* Search */}
          <div className="relative flex-1 min-w-[200px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 dark:text-slate-500" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder={t('form.search')}
              aria-label={t('form.search')}
              className="w-full pl-9 pr-4 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm dark:bg-slate-700 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
            />
          </div>

          {/* Building filter */}
          <select
            value={filterBuildingId}
            onChange={(e) => setFilterBuildingId(e.target.value)}
            aria-label={t('building.title')}
            className="px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
          >
            <option value="">{t('form.all')}</option>
            {Array.isArray(buildings) &&
              buildings.map((b: Building) => (
                <option key={b.id} value={b.id}>
                  {b.address}, {b.city}
                </option>
              ))}
          </select>

          {/* Document type filter */}
          <select
            value={filterDocType}
            onChange={(e) => setFilterDocType(e.target.value)}
            aria-label={t('document.filter_type')}
            className="px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
          >
            <option value="">{t('document.filter_type')}</option>
            {DOCUMENT_TYPES.map((dt) => (
              <option key={dt} value={dt}>
                {t(`document_type.${dt}`)}
              </option>
            ))}
          </select>

          {/* Status filter */}
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            aria-label={t('document.filter_status')}
            className="px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
          >
            <option value="">{t('document.filter_status')}</option>
            <option value="processing">{t('document.status_processing')}</option>
            <option value="ready">{t('document.status_ready')}</option>
            <option value="error">{t('document.status_error')}</option>
          </select>

          {/* Date from */}
          <input
            type="date"
            value={filterDateFrom}
            onChange={(e) => setFilterDateFrom(e.target.value)}
            aria-label={t('document.filter_date_from')}
            title={t('document.filter_date_from')}
            className="px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
          />

          {/* Date to */}
          <input
            type="date"
            value={filterDateTo}
            onChange={(e) => setFilterDateTo(e.target.value)}
            aria-label={t('document.filter_date_to')}
            title={t('document.filter_date_to')}
            className="px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
          />

          {/* Clear filters */}
          {hasActiveFilters && (
            <button
              onClick={() => {
                setFilterDocType('');
                setFilterStatus('');
                setFilterDateFrom('');
                setFilterDateTo('');
              }}
              className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-slate-300 hover:bg-gray-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
              title={t('form.reset')}
              aria-label={t('form.reset')}
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Content */}
      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-red-600" />
        </div>
      ) : filteredDocuments.length === 0 ? (
        <div className="bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-xl p-12 text-center">
          <FileText className="w-12 h-12 text-gray-300 dark:text-slate-600 mx-auto mb-3" />
          <p className="text-gray-500 dark:text-slate-400 text-sm">{t('document.no_documents')}</p>
        </div>
      ) : (
        <div className="flex gap-0 lg:gap-4">
          {/* Main content area */}
          <div className="flex-1 min-w-0">
            {viewMode === 'list' ? (
              <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 shadow-sm overflow-x-auto">
                <DataTable columns={columns} data={filteredDocuments} onRowClick={(row) => handleSelectDoc(row)} />
              </div>
            ) : (
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3">
                {filteredDocuments.map((doc) => (
                  <DocumentCard
                    key={doc.id}
                    doc={doc}
                    t={t}
                    onDownload={handleDownload}
                    onSelect={handleSelectDoc}
                    isSelected={selectedDoc?.id === doc.id}
                  />
                ))}
              </div>
            )}
          </div>

          {/* Detail panel */}
          {selectedDoc && (
            <DetailPanel
              doc={selectedDoc}
              t={t}
              onClose={() => setSelectedDoc(null)}
              onDownload={handleDownload}
              onPreview={handlePreview}
            />
          )}
        </div>
      )}

      {/* Upload Modal */}
      {showUploadModal && (
        <UploadModal
          buildings={buildings}
          t={t}
          onClose={() => setShowUploadModal(false)}
          onUploadComplete={() => {
            fetchDocuments();
          }}
        />
      )}

      {/* Preview Modal */}
      {previewDoc && (
        <PreviewModal
          doc={previewDoc}
          downloadUrl={previewUrl}
          t={t}
          onClose={() => {
            setPreviewDoc(null);
            setPreviewUrl(null);
          }}
        />
      )}
    </div>
  );
}

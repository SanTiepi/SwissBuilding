import { useTranslation } from '@/i18n';
import { FileUpload } from '@/components/FileUpload';
import { formatDate } from '@/utils/formatters';
import { documentsApi } from '@/api/documents';
import { ExtractionTriggerButton } from '@/components/extractions/ExtractionTriggerButton';
import { toast } from '@/store/toastStore';
import type { Document as DocType } from '@/types';
import { Loader2, FileText, Download, AlertTriangle } from 'lucide-react';

interface DocumentsTabProps {
  documents: DocType[];
  isLoadingDocs: boolean;
  documentsError: boolean;
  buildingId: string;
  onUpload: (file: File) => void;
}

export function DocumentsTab({ documents, isLoadingDocs, documentsError, buildingId, onUpload }: DocumentsTabProps) {
  const { t } = useTranslation();

  if (isLoadingDocs) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="w-8 h-8 animate-spin text-red-600" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-gray-700 dark:text-slate-200">{t('building.documents')}</h3>
      </div>
      <FileUpload onUpload={onUpload} />
      {documentsError ? (
        <div className="flex flex-col items-center justify-center py-8 text-center">
          <AlertTriangle className="w-8 h-8 text-red-400 mb-2" />
          <p className="text-sm text-red-600 dark:text-red-400">{t('app.error')}</p>
        </div>
      ) : documents.length > 0 ? (
        <div className="divide-y divide-gray-100 dark:divide-slate-700">
          {documents.map((doc: DocType) => (
            <div key={doc.id} className="py-3 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <FileText className="w-5 h-5 text-gray-400 dark:text-slate-500" />
                <div>
                  <p className="text-sm font-medium text-gray-900 dark:text-white">{doc.file_name}</p>
                  <p className="text-xs text-gray-500 dark:text-slate-400">{formatDate(doc.created_at)}</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <ExtractionTriggerButton documentId={doc.id} buildingId={buildingId} mimeType={doc.mime_type} />
                <button
                  onClick={async () => {
                    try {
                      const url = await documentsApi.getDownloadUrl(doc.id);
                      if (url) window.open(url, '_blank');
                    } catch (err: any) {
                      toast(err?.response?.data?.detail || err?.message || 'Download failed');
                    }
                  }}
                  className="p-2 text-gray-400 dark:text-slate-500 hover:text-gray-600 dark:hover:text-slate-300"
                >
                  <Download className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-center text-sm text-gray-500 dark:text-slate-400 py-8">{t('building.noDocuments')}</p>
      )}
    </div>
  );
}

export default DocumentsTab;

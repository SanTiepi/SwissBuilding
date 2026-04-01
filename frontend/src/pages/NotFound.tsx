import { Link } from 'react-router-dom';
import { useTranslation } from '@/i18n';

export default function NotFound() {
  const { t } = useTranslation();

  return (
    <div className="flex items-center justify-center min-h-screen bg-slate-50 dark:bg-slate-900 p-8">
      <div className="text-center max-w-md">
        <h1 className="text-8xl font-bold text-red-600 dark:text-red-500 mb-4">404</h1>
        <h2 className="text-2xl font-semibold text-slate-900 dark:text-slate-100 mb-2">{t('error.not_found')}</h2>
        <p className="text-slate-600 dark:text-slate-400 mb-8">{t('error.not_found_desc')}</p>
        <Link
          to="/today"
          className="inline-flex items-center gap-2 px-6 py-3 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
        >
          {t('error.back_home')}
        </Link>
      </div>
    </div>
  );
}

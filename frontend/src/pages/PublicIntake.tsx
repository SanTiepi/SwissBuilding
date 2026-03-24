import { useState } from 'react';
import { useTranslation } from '@/i18n';
import { intakeApi, type IntakeRequestCreate } from '@/api/intake';
import { Building2, CheckCircle2, Loader2, Send } from 'lucide-react';
import { cn } from '@/utils/formatters';

const REQUEST_TYPES = ['asbestos', 'pcb', 'lead', 'multi', 'consultation', 'other'] as const;
const URGENCY_LEVELS = ['standard', 'urgent', 'emergency'] as const;

const urgencyColors: Record<string, string> = {
  standard: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  urgent: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400',
  emergency: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
};

export default function PublicIntake() {
  const { t } = useTranslation();
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [form, setForm] = useState<IntakeRequestCreate>({
    name: '',
    email: '',
    phone: '',
    company: '',
    building_address: '',
    city: '',
    postal_code: '',
    egid: '',
    request_type: 'asbestos',
    urgency: 'standard',
    description: '',
  });

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await intakeApi.submit(form);
      setSubmitted(true);
    } catch {
      setError(t('intake.submit_error'));
    } finally {
      setSubmitting(false);
    }
  };

  if (submitted) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-slate-900 flex items-center justify-center p-4">
        <div
          className="max-w-md w-full bg-white dark:bg-slate-800 rounded-2xl shadow-lg p-8 text-center"
          data-testid="intake-success"
        >
          <CheckCircle2 className="w-16 h-16 text-green-500 mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-slate-900 dark:text-white mb-2">{t('intake.success_title')}</h2>
          <p className="text-slate-600 dark:text-slate-400">{t('intake.success_message')}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900">
      {/* Header */}
      <header className="bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700">
        <div className="max-w-3xl mx-auto px-4 py-6 flex items-center gap-3">
          <div className="w-10 h-10 bg-red-600 rounded-lg flex items-center justify-center">
            <Building2 className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-slate-900 dark:text-white">BatiConnect</h1>
            <p className="text-sm text-slate-500 dark:text-slate-400">{t('intake.header_subtitle')}</p>
          </div>
        </div>
      </header>

      {/* Form */}
      <main className="max-w-3xl mx-auto px-4 py-8">
        <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-lg p-6 sm:p-8">
          <h2 className="text-2xl font-bold text-slate-900 dark:text-white mb-2">{t('intake.form_title')}</h2>
          <p className="text-slate-600 dark:text-slate-400 mb-6">{t('intake.form_subtitle')}</p>

          {error && (
            <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 rounded-lg text-sm">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Contact info */}
            <fieldset>
              <legend className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-3">
                {t('intake.section_contact')}
              </legend>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label htmlFor="name" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                    {t('intake.field_name')} *
                  </label>
                  <input
                    id="name"
                    name="name"
                    type="text"
                    required
                    value={form.name}
                    onChange={handleChange}
                    data-testid="intake-name"
                    className="w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-700 px-3 py-2 text-sm text-slate-900 dark:text-white focus:ring-2 focus:ring-red-500 focus:border-transparent"
                  />
                </div>
                <div>
                  <label htmlFor="email" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                    {t('intake.field_email')} *
                  </label>
                  <input
                    id="email"
                    name="email"
                    type="email"
                    required
                    value={form.email}
                    onChange={handleChange}
                    data-testid="intake-email"
                    className="w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-700 px-3 py-2 text-sm text-slate-900 dark:text-white focus:ring-2 focus:ring-red-500 focus:border-transparent"
                  />
                </div>
                <div>
                  <label htmlFor="phone" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                    {t('intake.field_phone')}
                  </label>
                  <input
                    id="phone"
                    name="phone"
                    type="tel"
                    value={form.phone}
                    onChange={handleChange}
                    data-testid="intake-phone"
                    className="w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-700 px-3 py-2 text-sm text-slate-900 dark:text-white focus:ring-2 focus:ring-red-500 focus:border-transparent"
                  />
                </div>
                <div>
                  <label
                    htmlFor="company"
                    className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1"
                  >
                    {t('intake.field_company')}
                  </label>
                  <input
                    id="company"
                    name="company"
                    type="text"
                    value={form.company}
                    onChange={handleChange}
                    data-testid="intake-company"
                    className="w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-700 px-3 py-2 text-sm text-slate-900 dark:text-white focus:ring-2 focus:ring-red-500 focus:border-transparent"
                  />
                </div>
              </div>
            </fieldset>

            {/* Building info */}
            <fieldset>
              <legend className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-3">
                {t('intake.section_building')}
              </legend>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="sm:col-span-2">
                  <label
                    htmlFor="building_address"
                    className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1"
                  >
                    {t('intake.field_address')} *
                  </label>
                  <input
                    id="building_address"
                    name="building_address"
                    type="text"
                    required
                    value={form.building_address}
                    onChange={handleChange}
                    data-testid="intake-address"
                    className="w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-700 px-3 py-2 text-sm text-slate-900 dark:text-white focus:ring-2 focus:ring-red-500 focus:border-transparent"
                  />
                </div>
                <div>
                  <label htmlFor="city" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                    {t('intake.field_city')}
                  </label>
                  <input
                    id="city"
                    name="city"
                    type="text"
                    value={form.city}
                    onChange={handleChange}
                    data-testid="intake-city"
                    className="w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-700 px-3 py-2 text-sm text-slate-900 dark:text-white focus:ring-2 focus:ring-red-500 focus:border-transparent"
                  />
                </div>
                <div>
                  <label
                    htmlFor="postal_code"
                    className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1"
                  >
                    {t('intake.field_postal_code')}
                  </label>
                  <input
                    id="postal_code"
                    name="postal_code"
                    type="text"
                    value={form.postal_code}
                    onChange={handleChange}
                    data-testid="intake-postal-code"
                    className="w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-700 px-3 py-2 text-sm text-slate-900 dark:text-white focus:ring-2 focus:ring-red-500 focus:border-transparent"
                  />
                </div>
                <div>
                  <label htmlFor="egid" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                    {t('intake.field_egid')}
                  </label>
                  <input
                    id="egid"
                    name="egid"
                    type="text"
                    value={form.egid}
                    onChange={handleChange}
                    data-testid="intake-egid"
                    placeholder={t('intake.field_egid_placeholder')}
                    className="w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-700 px-3 py-2 text-sm text-slate-900 dark:text-white focus:ring-2 focus:ring-red-500 focus:border-transparent"
                  />
                </div>
              </div>
            </fieldset>

            {/* Request details */}
            <fieldset>
              <legend className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-3">
                {t('intake.section_request')}
              </legend>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label
                    htmlFor="request_type"
                    className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1"
                  >
                    {t('intake.field_request_type')}
                  </label>
                  <select
                    id="request_type"
                    name="request_type"
                    value={form.request_type}
                    onChange={handleChange}
                    data-testid="intake-request-type"
                    className="w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-700 px-3 py-2 text-sm text-slate-900 dark:text-white focus:ring-2 focus:ring-red-500 focus:border-transparent"
                  >
                    {REQUEST_TYPES.map((type) => (
                      <option key={type} value={type}>
                        {t(`intake.request_type.${type}`)}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label
                    htmlFor="urgency"
                    className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1"
                  >
                    {t('intake.field_urgency')}
                  </label>
                  <select
                    id="urgency"
                    name="urgency"
                    value={form.urgency}
                    onChange={handleChange}
                    data-testid="intake-urgency"
                    className="w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-700 px-3 py-2 text-sm text-slate-900 dark:text-white focus:ring-2 focus:ring-red-500 focus:border-transparent"
                  >
                    {URGENCY_LEVELS.map((level) => (
                      <option key={level} value={level}>
                        {t(`intake.urgency.${level}`)}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="sm:col-span-2">
                  <label
                    htmlFor="description"
                    className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1"
                  >
                    {t('intake.field_description')}
                  </label>
                  <textarea
                    id="description"
                    name="description"
                    rows={4}
                    value={form.description}
                    onChange={handleChange}
                    data-testid="intake-description"
                    className="w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-700 px-3 py-2 text-sm text-slate-900 dark:text-white focus:ring-2 focus:ring-red-500 focus:border-transparent resize-y"
                  />
                </div>
              </div>
            </fieldset>

            {/* Urgency preview */}
            <div className="flex items-center gap-2">
              <span className="text-sm text-slate-600 dark:text-slate-400">{t('intake.field_urgency')}:</span>
              <span
                className={cn('px-2 py-0.5 rounded-full text-xs font-medium', urgencyColors[form.urgency])}
                data-testid="intake-urgency-badge"
              >
                {t(`intake.urgency.${form.urgency}`)}
              </span>
            </div>

            <button
              type="submit"
              disabled={submitting}
              data-testid="intake-submit"
              className="w-full flex items-center justify-center gap-2 bg-red-600 hover:bg-red-700 disabled:opacity-50 text-white font-medium py-3 px-4 rounded-lg transition-colors"
            >
              {submitting ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <Send className="w-5 h-5" />
              )}
              {submitting ? t('app.loading') : t('intake.submit')}
            </button>
          </form>
        </div>
      </main>
    </div>
  );
}

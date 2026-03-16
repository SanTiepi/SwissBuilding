import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '@/hooks/useAuth';
import { useAuthStore } from '@/store/authStore';
import { useTranslation } from '@/i18n';
import { cn } from '@/utils/formatters';
import { settingsApi } from '@/api/settings';
import { toast } from '@/store/toastStore';
import { RoleGate } from '@/components/RoleGate';
import type {
  NotificationPreference,
  FullNotificationPreferences,
  NotificationChannel,
  DigestFrequency,
} from '@/types';
import {
  User,
  Mail,
  Shield,
  Globe,
  Lock,
  Save,
  Loader2,
  CheckCircle2,
  AlertCircle,
  ExternalLink,
  Info,
  Bell,
  ChevronDown,
  ChevronRight,
} from 'lucide-react';

const passwordSchema = z
  .object({
    current_password: z.string().min(1, 'Current password is required'),
    new_password: z.string().min(8, 'Password must be at least 8 characters'),
    confirm_password: z.string().min(1, 'Please confirm your password'),
  })
  .refine((data) => data.new_password === data.confirm_password, {
    message: 'Passwords do not match',
    path: ['confirm_password'],
  });

type PasswordFormData = z.infer<typeof passwordSchema>;

const LANGUAGES = [
  { code: 'fr', label: 'Francais', flag: 'FR' },
  { code: 'de', label: 'Deutsch', flag: 'DE' },
  { code: 'it', label: 'Italiano', flag: 'IT' },
  { code: 'en', label: 'English', flag: 'EN' },
] as const;

export default function Settings() {
  const { t, locale, setLocale } = useTranslation();
  const { user } = useAuth();

  const [profileLoading, setProfileLoading] = useState(false);
  const [profileSuccess, setProfileSuccess] = useState(false);
  const [profileError, setProfileError] = useState<string | null>(null);

  const [passwordLoading, setPasswordLoading] = useState(false);
  const [passwordSuccess, setPasswordSuccess] = useState(false);
  const [passwordError, setPasswordError] = useState<string | null>(null);

  // Profile form
  const [name, setName] = useState(user?.first_name || '');
  const [email] = useState(user?.email || '');

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<PasswordFormData>({
    resolver: zodResolver(passwordSchema),
  });

  const onProfileSave = async () => {
    setProfileLoading(true);
    setProfileSuccess(false);
    setProfileError(null);
    try {
      const updated = await settingsApi.updateProfile({ first_name: name });
      useAuthStore.getState().updateUser(updated);
      setProfileSuccess(true);
      setTimeout(() => setProfileSuccess(false), 3000);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : t('form.error');
      setProfileError(message);
    } finally {
      setProfileLoading(false);
    }
  };

  const onPasswordSubmit = async (data: PasswordFormData) => {
    setPasswordLoading(true);
    setPasswordSuccess(false);
    setPasswordError(null);
    try {
      await settingsApi.changePassword({
        current_password: data.current_password,
        new_password: data.new_password,
      });
      setPasswordSuccess(true);
      reset();
      setTimeout(() => setPasswordSuccess(false), 3000);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : t('form.error');
      setPasswordError(message);
    } finally {
      setPasswordLoading(false);
    }
  };

  const queryClient = useQueryClient();

  // Notification preferences
  const {
    data: notifPrefs,
    isLoading: notifPrefsLoading,
    isError: notifPrefsError,
  } = useQuery({
    queryKey: ['notification-preferences'],
    queryFn: () => settingsApi.getNotificationPreferences(),
  });

  const updatePrefsMutation = useMutation({
    mutationFn: (prefs: NotificationPreference) => settingsApi.updateNotificationPreferences(prefs),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notification-preferences'] });
    },
  });

  const handleTogglePref = (key: keyof NotificationPreference) => {
    if (!notifPrefs) return;
    const updated = { ...notifPrefs, [key]: !notifPrefs[key] };
    updatePrefsMutation.mutate(updated);
  };

  // Advanced notification preferences
  const [advancedOpen, setAdvancedOpen] = useState(false);

  const { data: fullPrefs, isLoading: fullPrefsLoading } = useQuery({
    queryKey: ['full-notification-preferences'],
    queryFn: () => settingsApi.getFullNotificationPreferences(),
    enabled: advancedOpen,
  });

  const updateFullPrefsMutation = useMutation({
    mutationFn: (data: Partial<FullNotificationPreferences>) => settingsApi.updateFullNotificationPreferences(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['full-notification-preferences'] });
      toast(t('settings.notifications.preferences_saved'), 'success');
    },
    onError: () => {
      toast(t('settings.notifications.preferences_error'), 'error');
    },
  });

  const NOTIFICATION_TYPES = ['action', 'invitation', 'export', 'system'] as const;
  const CHANNELS: NotificationChannel[] = ['in_app', 'email', 'digest'];

  const handleChannelToggle = (notifType: string, channel: NotificationChannel) => {
    if (!fullPrefs) return;
    const updatedTypePrefs = fullPrefs.type_preferences.map((tp) => {
      if (tp.type !== notifType) return tp;
      const hasChannel = tp.channels.includes(channel);
      return {
        ...tp,
        channels: hasChannel ? tp.channels.filter((c) => c !== channel) : [...tp.channels, channel],
      };
    });
    updateFullPrefsMutation.mutate({ type_preferences: updatedTypePrefs });
  };

  const handleQuietHoursToggle = () => {
    if (!fullPrefs) return;
    updateFullPrefsMutation.mutate({
      quiet_hours: { ...fullPrefs.quiet_hours, enabled: !fullPrefs.quiet_hours.enabled },
    });
  };

  const handleQuietHourChange = (field: 'start_hour' | 'end_hour', value: number) => {
    if (!fullPrefs) return;
    updateFullPrefsMutation.mutate({
      quiet_hours: { ...fullPrefs.quiet_hours, [field]: value },
    });
  };

  const handleDigestFrequencyChange = (freq: DigestFrequency) => {
    updateFullPrefsMutation.mutate({ digest_frequency: freq });
  };

  const onLanguageChange = (code: string) => {
    setLocale(code as 'fr' | 'de' | 'it' | 'en');
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{t('settings.title')}</h1>
        <p className="text-sm text-gray-500 dark:text-slate-400 mt-1">{t('settings.general')}</p>
      </div>

      {/* Profile Section */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
          <User className="w-5 h-5 text-gray-400 dark:text-slate-500" />
          {t('nav.profile')}
        </h2>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">
              {t('user.first_name')}
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm dark:bg-slate-700 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">
              {t('user.email')}
            </label>
            <div className="relative">
              <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 dark:text-slate-500" />
              <input
                type="email"
                value={email}
                disabled
                className="w-full pl-9 pr-4 py-2 border border-gray-200 dark:border-slate-700 rounded-lg text-sm bg-gray-50 dark:bg-slate-700 text-gray-500 dark:text-slate-400 cursor-not-allowed"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">{t('user.role')}</label>
            <div className="flex items-center gap-2">
              <Shield className="w-4 h-4 text-gray-400 dark:text-slate-500" />
              <span className="px-3 py-1 text-sm font-medium bg-gray-100 dark:bg-slate-700 text-gray-700 dark:text-slate-200 rounded-full">
                {t(`role.${user?.role}`) || user?.role || '-'}
              </span>
            </div>
          </div>

          {/* Save profile */}
          <div className="flex items-center gap-3 pt-2">
            <button
              onClick={onProfileSave}
              disabled={profileLoading}
              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 disabled:bg-red-400 transition-colors"
            >
              {profileLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
              {t('settings.save')}
            </button>
            {profileSuccess && (
              <span className="text-sm text-green-600 flex items-center gap-1">
                <CheckCircle2 className="w-4 h-4" />
                {t('settings.saved')}
              </span>
            )}
            {profileError && (
              <span className="text-sm text-red-600 flex items-center gap-1">
                <AlertCircle className="w-4 h-4" />
                {profileError}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Language Section */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
          <Globe className="w-5 h-5 text-gray-400 dark:text-slate-500" />
          {t('settings.language')}
        </h2>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3" role="radiogroup" aria-label={t('settings.language')}>
          {LANGUAGES.map((lang) => (
            <label
              key={lang.code}
              className={cn(
                'flex items-center justify-center gap-2 p-3 rounded-xl border-2 cursor-pointer transition-all',
                locale === lang.code
                  ? 'border-red-500 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400'
                  : 'border-gray-200 dark:border-slate-700 hover:border-gray-300 dark:hover:border-slate-600 text-gray-700 dark:text-slate-200',
              )}
            >
              <input
                type="radio"
                name="language"
                value={lang.code}
                checked={locale === lang.code}
                onChange={() => onLanguageChange(lang.code)}
                className="sr-only"
              />
              <span className="text-lg font-bold">{lang.flag}</span>
              <span className="text-sm font-medium">{lang.label}</span>
            </label>
          ))}
        </div>
      </div>

      {/* Password Section */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
          <Lock className="w-5 h-5 text-gray-400 dark:text-slate-500" />
          {t('settings.security')}
        </h2>

        <form onSubmit={handleSubmit(onPasswordSubmit)} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">
              {t('settings.currentPassword')}
            </label>
            <input
              type="password"
              {...register('current_password')}
              className={cn(
                'w-full px-3 py-2 border rounded-lg text-sm dark:bg-slate-700 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500',
                errors.current_password ? 'border-red-300' : 'border-gray-300 dark:border-slate-600',
              )}
            />
            {errors.current_password && <p className="text-xs text-red-600 mt-1">{errors.current_password.message}</p>}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">
              {t('settings.newPassword')}
            </label>
            <input
              type="password"
              {...register('new_password')}
              className={cn(
                'w-full px-3 py-2 border rounded-lg text-sm dark:bg-slate-700 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500',
                errors.new_password ? 'border-red-300' : 'border-gray-300 dark:border-slate-600',
              )}
            />
            {errors.new_password && <p className="text-xs text-red-600 mt-1">{errors.new_password.message}</p>}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">
              {t('settings.confirmPassword')}
            </label>
            <input
              type="password"
              {...register('confirm_password')}
              className={cn(
                'w-full px-3 py-2 border rounded-lg text-sm dark:bg-slate-700 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500',
                errors.confirm_password ? 'border-red-300' : 'border-gray-300 dark:border-slate-600',
              )}
            />
            {errors.confirm_password && <p className="text-xs text-red-600 mt-1">{errors.confirm_password.message}</p>}
          </div>

          <div className="flex items-center gap-3 pt-2">
            <button
              type="submit"
              disabled={passwordLoading}
              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 disabled:bg-red-400 transition-colors"
            >
              {passwordLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Lock className="w-4 h-4" />}
              {t('settings.updatePassword')}
            </button>
            {passwordSuccess && (
              <span className="text-sm text-green-600 flex items-center gap-1">
                <CheckCircle2 className="w-4 h-4" />
                {t('settings.passwordUpdated')}
              </span>
            )}
            {passwordError && (
              <span className="text-sm text-red-600 flex items-center gap-1">
                <AlertCircle className="w-4 h-4" />
                {passwordError}
              </span>
            )}
          </div>
        </form>
      </div>

      {/* Notification Preferences Section */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
          <Bell className="w-5 h-5 text-gray-400 dark:text-slate-500" />
          {t('notification.preferences')}
        </h2>

        {notifPrefsLoading ? (
          <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-slate-400">
            <Loader2 className="w-4 h-4 animate-spin" />
            {t('app.loading')}
          </div>
        ) : notifPrefsError ? (
          <div className="flex items-center gap-2 text-sm text-red-600 dark:text-red-400">
            <AlertCircle className="w-4 h-4" />
            {t('app.error')}
          </div>
        ) : (
          <>
            <div className="space-y-4">
              {(
                [
                  { key: 'in_app_actions', label: t('notification.in_app_actions') },
                  { key: 'in_app_invitations', label: t('notification.in_app_invitations') },
                  { key: 'in_app_exports', label: t('notification.in_app_exports') },
                  { key: 'digest_enabled', label: t('notification.digest_enabled') },
                ] as const
              ).map(({ key, label }) => (
                <div key={key} className="flex items-center justify-between">
                  <span className="text-sm font-medium text-gray-700 dark:text-slate-200">{label}</span>
                  <button
                    type="button"
                    role="switch"
                    aria-checked={notifPrefs?.[key] ?? false}
                    onClick={() => handleTogglePref(key)}
                    disabled={!notifPrefs || updatePrefsMutation.isPending}
                    className={cn(
                      'relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 dark:focus:ring-offset-slate-800 disabled:opacity-50',
                      notifPrefs?.[key] ? 'bg-red-600' : 'bg-gray-300 dark:bg-slate-600',
                    )}
                  >
                    <span
                      className={cn(
                        'inline-block h-4 w-4 transform rounded-full bg-white transition-transform',
                        notifPrefs?.[key] ? 'translate-x-6' : 'translate-x-1',
                      )}
                    />
                  </button>
                </div>
              ))}
            </div>

            {/* Advanced Preferences */}
            <div className="mt-6 border-t border-gray-200 dark:border-slate-700 pt-4">
              <button
                type="button"
                onClick={() => setAdvancedOpen(!advancedOpen)}
                className="flex items-center gap-2 text-sm font-medium text-gray-700 dark:text-slate-200 hover:text-red-600 dark:hover:text-red-400 transition-colors"
              >
                {advancedOpen ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                {t('settings.notifications.advanced_preferences')}
              </button>

              {advancedOpen && (
                <div className="mt-4 space-y-6">
                  {fullPrefsLoading ? (
                    <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-slate-400">
                      <Loader2 className="w-4 h-4 animate-spin" />
                      {t('app.loading')}
                    </div>
                  ) : fullPrefs ? (
                    <>
                      {/* Per-type channel toggles */}
                      <div>
                        <h3 className="text-sm font-medium text-gray-700 dark:text-slate-200 mb-3">
                          {t('settings.notifications.per_type_channels')}
                        </h3>
                        <div className="overflow-x-auto">
                          <table className="w-full text-sm">
                            <thead>
                              <tr className="text-left text-gray-500 dark:text-slate-400">
                                <th className="pb-2 pr-4 font-medium">&nbsp;</th>
                                {CHANNELS.map((ch) => (
                                  <th key={ch} className="pb-2 px-3 font-medium text-center">
                                    {t(`settings.notifications.channel_${ch}`)}
                                  </th>
                                ))}
                              </tr>
                            </thead>
                            <tbody>
                              {NOTIFICATION_TYPES.map((notifType) => {
                                const typePref = fullPrefs.type_preferences.find((tp) => tp.type === notifType);
                                return (
                                  <tr key={notifType} className="border-t border-gray-100 dark:border-slate-700">
                                    <td className="py-2 pr-4 font-medium text-gray-700 dark:text-slate-200">
                                      {t(`settings.notifications.type_${notifType}`)}
                                    </td>
                                    {CHANNELS.map((ch) => (
                                      <td key={ch} className="py-2 px-3 text-center">
                                        <input
                                          type="checkbox"
                                          checked={typePref?.channels.includes(ch) ?? false}
                                          onChange={() => handleChannelToggle(notifType, ch)}
                                          disabled={updateFullPrefsMutation.isPending}
                                          className="h-4 w-4 rounded border-gray-300 dark:border-slate-600 text-red-600 focus:ring-red-500 dark:bg-slate-700 disabled:opacity-50"
                                        />
                                      </td>
                                    ))}
                                  </tr>
                                );
                              })}
                            </tbody>
                          </table>
                        </div>
                      </div>

                      {/* Quiet Hours */}
                      <div>
                        <div className="flex items-center justify-between mb-3">
                          <h3 className="text-sm font-medium text-gray-700 dark:text-slate-200">
                            {t('settings.notifications.quiet_hours')}
                          </h3>
                          <button
                            type="button"
                            role="switch"
                            aria-checked={fullPrefs.quiet_hours.enabled}
                            onClick={handleQuietHoursToggle}
                            disabled={updateFullPrefsMutation.isPending}
                            className={cn(
                              'relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 dark:focus:ring-offset-slate-800 disabled:opacity-50',
                              fullPrefs.quiet_hours.enabled ? 'bg-red-600' : 'bg-gray-300 dark:bg-slate-600',
                            )}
                          >
                            <span
                              className={cn(
                                'inline-block h-4 w-4 transform rounded-full bg-white transition-transform',
                                fullPrefs.quiet_hours.enabled ? 'translate-x-6' : 'translate-x-1',
                              )}
                            />
                          </button>
                        </div>
                        {fullPrefs.quiet_hours.enabled && (
                          <div className="flex items-center gap-4">
                            <div>
                              <label className="block text-xs text-gray-500 dark:text-slate-400 mb-1">
                                {t('settings.notifications.quiet_hours_start')}
                              </label>
                              <select
                                value={fullPrefs.quiet_hours.start_hour}
                                onChange={(e) => handleQuietHourChange('start_hour', Number(e.target.value))}
                                disabled={updateFullPrefsMutation.isPending}
                                className="px-3 py-1.5 border border-gray-300 dark:border-slate-600 rounded-lg text-sm dark:bg-slate-700 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500 disabled:opacity-50"
                              >
                                {Array.from({ length: 24 }, (_, i) => (
                                  <option key={i} value={i}>
                                    {String(i).padStart(2, '0')}:00
                                  </option>
                                ))}
                              </select>
                            </div>
                            <div>
                              <label className="block text-xs text-gray-500 dark:text-slate-400 mb-1">
                                {t('settings.notifications.quiet_hours_end')}
                              </label>
                              <select
                                value={fullPrefs.quiet_hours.end_hour}
                                onChange={(e) => handleQuietHourChange('end_hour', Number(e.target.value))}
                                disabled={updateFullPrefsMutation.isPending}
                                className="px-3 py-1.5 border border-gray-300 dark:border-slate-600 rounded-lg text-sm dark:bg-slate-700 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500 disabled:opacity-50"
                              >
                                {Array.from({ length: 24 }, (_, i) => (
                                  <option key={i} value={i}>
                                    {String(i).padStart(2, '0')}:00
                                  </option>
                                ))}
                              </select>
                            </div>
                          </div>
                        )}
                      </div>

                      {/* Digest Frequency */}
                      <div>
                        <h3 className="text-sm font-medium text-gray-700 dark:text-slate-200 mb-3">
                          {t('settings.notifications.digest_frequency')}
                        </h3>
                        <div className="flex gap-3">
                          {(['daily', 'weekly', 'never'] as DigestFrequency[]).map((freq) => (
                            <label
                              key={freq}
                              className={cn(
                                'flex items-center justify-center px-4 py-2 rounded-lg border-2 cursor-pointer transition-all text-sm font-medium',
                                fullPrefs.digest_frequency === freq
                                  ? 'border-red-500 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400'
                                  : 'border-gray-200 dark:border-slate-700 hover:border-gray-300 dark:hover:border-slate-600 text-gray-700 dark:text-slate-200',
                              )}
                            >
                              <input
                                type="radio"
                                name="digest_frequency"
                                value={freq}
                                checked={fullPrefs.digest_frequency === freq}
                                onChange={() => handleDigestFrequencyChange(freq)}
                                disabled={updateFullPrefsMutation.isPending}
                                className="sr-only"
                              />
                              {t(`settings.notifications.${freq}`)}
                            </label>
                          ))}
                        </div>
                      </div>
                    </>
                  ) : (
                    <div className="flex items-center gap-2 text-sm text-red-600 dark:text-red-400">
                      <AlertCircle className="w-4 h-4" />
                      {t('app.error')}
                    </div>
                  )}
                </div>
              )}
            </div>
          </>
        )}
      </div>

      {/* Admin Section */}
      <RoleGate allowedRoles={['admin']}>
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
            <Shield className="w-5 h-5 text-gray-400 dark:text-slate-500" />
            {t('settings.administration')}
          </h2>
          <div className="flex flex-wrap gap-3">
            <Link
              to="/admin/users"
              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-slate-700 dark:text-slate-200 bg-gray-100 dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg hover:bg-gray-200 dark:hover:bg-slate-600 transition-colors"
            >
              {t('admin.users')}
              <ExternalLink className="w-4 h-4" />
            </Link>
            <Link
              to="/admin/organizations"
              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-slate-700 dark:text-slate-200 bg-gray-100 dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg hover:bg-gray-200 dark:hover:bg-slate-600 transition-colors"
            >
              {t('admin.organizations')}
              <ExternalLink className="w-4 h-4" />
            </Link>
            <Link
              to="/admin/invitations"
              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-slate-700 dark:text-slate-200 bg-gray-100 dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg hover:bg-gray-200 dark:hover:bg-slate-600 transition-colors"
            >
              {t('admin.invitations')}
              <ExternalLink className="w-4 h-4" />
            </Link>
          </div>
        </div>
      </RoleGate>

      {/* Application Info */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
          <Info className="w-5 h-5 text-gray-400 dark:text-slate-500" />
          {t('settings.appInfo')}
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div className="bg-gray-50 dark:bg-slate-700 rounded-lg p-3">
            <p className="text-xs text-gray-500 dark:text-slate-400">{t('app.version')}</p>
            <p className="text-sm font-medium text-gray-900 dark:text-white mt-0.5">1.0.0</p>
          </div>
          <div className="bg-gray-50 dark:bg-slate-700 rounded-lg p-3">
            <p className="text-xs text-gray-500 dark:text-slate-400">{t('settings.lastUpdate')}</p>
            <p className="text-sm font-medium text-gray-900 dark:text-white mt-0.5">2026-03-07</p>
          </div>
          <div className="bg-gray-50 dark:bg-slate-700 rounded-lg p-3">
            <p className="text-xs text-gray-500 dark:text-slate-400">{t('settings.environment')}</p>
            <p className="text-sm font-medium text-gray-900 dark:text-white mt-0.5">
              {import.meta.env.MODE || 'production'}
            </p>
          </div>
          <div className="bg-gray-50 dark:bg-slate-700 rounded-lg p-3">
            <p className="text-xs text-gray-500 dark:text-slate-400">{t('settings.framework')}</p>
            <p className="text-sm font-medium text-gray-900 dark:text-white mt-0.5">React + Vite</p>
          </div>
        </div>
      </div>
    </div>
  );
}

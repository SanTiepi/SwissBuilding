import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useAuth } from '@/hooks/useAuth';
import { useTranslation } from '@/i18n';
import { cn } from '@/utils/formatters';
import { Building2, Globe, Loader2, AlertCircle, Lock, Mail } from 'lucide-react';

type LoginFormData = { email: string; password: string };

const LANGUAGES = [
  { code: 'fr', label: 'FR' },
  { code: 'de', label: 'DE' },
  { code: 'it', label: 'IT' },
  { code: 'en', label: 'EN' },
] as const;

const DEMO_EMAIL = import.meta.env.VITE_DEMO_ADMIN_EMAIL || 'admin@swissbuildingos.ch';
const DEMO_PASSWORD = import.meta.env.VITE_DEMO_ADMIN_PASSWORD || 'noob42';
const PRELIVE_NO_PASSWORD = import.meta.env.VITE_PRELIVE_AUTH_BYPASS === '1';

export default function Login() {
  const { t, setLocale, locale } = useTranslation();
  const navigate = useNavigate();
  const { login } = useAuth();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loginSchema = z.object({
    email: z.string().email(t('form.invalid_email')),
    password: z.string().min(6, t('form.min_length', { min: '6' })),
  });

  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: '', password: PRELIVE_NO_PASSWORD ? 'prelive' : '' },
  });

  const fillDemoCredentials = () => {
    setValue('email', DEMO_EMAIL, { shouldValidate: true });
    setValue('password', PRELIVE_NO_PASSWORD ? 'prelive' : DEMO_PASSWORD, { shouldValidate: true });
    setError(null);
  };

  const onSubmit = async (data: LoginFormData) => {
    setIsLoading(true);
    setError(null);
    try {
      await login.mutateAsync({
        email: data.email,
        password: PRELIVE_NO_PASSWORD ? 'prelive' : data.password,
      });
      navigate('/dashboard');
    } catch (err: any) {
      setError(err?.message || t('auth.error.invalid'));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-red-700 via-red-600 to-red-800 relative overflow-hidden">
      {/* Background decoration */}
      <div className="absolute inset-0 opacity-10">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-white rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 right-1/4 w-64 h-64 bg-white rounded-full blur-3xl" />
      </div>

      {/* Language selector */}
      <div className="absolute top-4 right-4 flex items-center gap-1 bg-white/10 backdrop-blur-sm rounded-lg p-1">
        <Globe className="w-4 h-4 text-white/70 mr-1" />
        {LANGUAGES.map((lang) => (
          <button
            key={lang.code}
            onClick={() => setLocale(lang.code)}
            className={cn(
              'px-2 py-1 text-xs font-medium rounded transition-colors',
              locale === lang.code ? 'bg-white text-red-700' : 'text-white/80 hover:text-white hover:bg-white/10',
            )}
          >
            {lang.label}
          </button>
        ))}
      </div>

      {/* Login card */}
      <div className="relative z-10 w-full max-w-md mx-4">
        <div className="bg-white rounded-2xl shadow-2xl p-8">
          {/* Logo / Title */}
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center w-16 h-16 bg-red-600 rounded-2xl mb-4 shadow-lg">
              <Building2 className="w-8 h-8 text-white" />
            </div>
            <h1 className="text-2xl font-bold text-gray-900">SwissBuildingOS</h1>
            <p className="text-sm text-gray-500 mt-1">{t('app.subtitle')}</p>
          </div>

          {/* Swiss cross decoration */}
          <div className="flex justify-center mb-6">
            <div className="w-8 h-8 relative">
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="w-full h-2 bg-red-600 rounded-sm" />
              </div>
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="w-2 h-full bg-red-600 rounded-sm" />
              </div>
            </div>
          </div>

          {/* Error message */}
          {error && (
            <div className="mb-6 flex items-center gap-2 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
            {/* Email */}
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1.5">
                {t('auth.email')}
              </label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  id="email"
                  type="email"
                  autoComplete="email"
                  aria-invalid={errors.email ? 'true' : undefined}
                  aria-describedby={errors.email ? 'email-error' : undefined}
                  {...register('email')}
                  className={cn(
                    'w-full pl-10 pr-4 py-2.5 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-transparent transition-shadow',
                    errors.email ? 'border-red-300 bg-red-50' : 'border-gray-300 bg-white',
                  )}
                  placeholder="name@company.ch"
                />
              </div>
              {errors.email && (
                <p id="email-error" className="mt-1 text-xs text-red-600" role="alert">
                  {errors.email.message}
                </p>
              )}
            </div>

            {/* Password */}
            {PRELIVE_NO_PASSWORD ? (
              <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800">
                Mode pre-live: authentification sans mot de passe activee.
              </div>
            ) : (
              <div>
                <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1.5">
                  {t('auth.password')}
                </label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                  <input
                    id="password"
                    type="password"
                    autoComplete="current-password"
                    aria-invalid={errors.password ? 'true' : undefined}
                    aria-describedby="password-requirements password-error"
                    {...register('password')}
                    className={cn(
                      'w-full pl-10 pr-4 py-2.5 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-transparent transition-shadow',
                      errors.password ? 'border-red-300 bg-red-50' : 'border-gray-300 bg-white',
                    )}
                    placeholder="********"
                  />
                </div>
                <p id="password-requirements" className="mt-1.5 text-xs text-slate-500">
                  {t('form.min_length', { min: '6' })}
                </p>
                {errors.password && (
                  <p id="password-error" className="mt-1 text-xs text-red-600" role="alert">
                    {errors.password.message}
                  </p>
                )}
              </div>
            )}

            {import.meta.env.DEV && (
              <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs text-slate-600">
                <div className="font-medium text-slate-700">Demo local</div>
                <div className="mt-1">
                  {PRELIVE_NO_PASSWORD ? `${DEMO_EMAIL} / sans mot de passe` : `${DEMO_EMAIL} / ${DEMO_PASSWORD}`}
                </div>
                <button
                  type="button"
                  onClick={fillDemoCredentials}
                  className="mt-2 text-red-700 hover:text-red-800 font-medium"
                >
                  Remplir automatiquement
                </button>
              </div>
            )}

            {/* Submit */}
            <button
              type="submit"
              disabled={isLoading}
              className="w-full flex items-center justify-center gap-2 py-2.5 px-4 bg-red-600 hover:bg-red-700 disabled:bg-red-400 text-white font-medium rounded-lg text-sm transition-colors shadow-sm"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  {t('app.loading')}
                </>
              ) : (
                t('auth.login_button')
              )}
            </button>
          </form>

          {/* Footer */}
          <p className="text-center text-xs text-gray-500 mt-6">{t('misc.copyright')}</p>
        </div>
      </div>
    </div>
  );
}

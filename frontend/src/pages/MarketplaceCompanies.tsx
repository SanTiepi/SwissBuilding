import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { marketplaceApi } from '@/api/marketplace';
import type { CompanyProfile } from '@/api/marketplace';
import { useTranslation } from '@/i18n';
import { cn } from '@/utils/formatters';
import { Building2, MapPin, Star, Search, ChevronRight, Shield, Users, Clock, X } from 'lucide-react';

const CANTONS = ['AG', 'AI', 'AR', 'BE', 'BL', 'BS', 'FR', 'GE', 'GL', 'GR', 'JU', 'LU', 'NE', 'NW', 'OW', 'SG', 'SH', 'SO', 'SZ', 'TG', 'TI', 'UR', 'VD', 'VS', 'ZG', 'ZH'];

const WORK_CATEGORIES = [
  'asbestos_removal',
  'pcb_remediation',
  'lead_abatement',
  'hap_treatment',
  'decontamination',
  'waste_management',
  'demolition',
];

function RatingBadge({ rating }: { rating: number | null }) {
  if (rating === null) return <span className="text-xs text-gray-400 dark:text-slate-500">--</span>;
  const color =
    rating >= 4 ? 'text-green-600 dark:text-green-400' : rating >= 3 ? 'text-amber-600 dark:text-amber-400' : 'text-red-600 dark:text-red-400';
  return (
    <span className={cn('flex items-center gap-1 text-sm font-semibold', color)}>
      <Star className="w-4 h-4 fill-current" />
      {rating.toFixed(1)}
    </span>
  );
}

function CompanyCard({
  company,
  onClick,
}: {
  company: CompanyProfile;
  onClick: () => void;
}) {
  const { t } = useTranslation();
  const { data: ratingSummary } = useQuery({
    queryKey: ['marketplace-rating', company.id],
    queryFn: () => marketplaceApi.getRatingSummary(company.id),
    staleTime: 60_000,
  });

  return (
    <button
      onClick={onClick}
      className="w-full text-left bg-white dark:bg-slate-800 rounded-lg border border-gray-200 dark:border-slate-700 p-4 hover:shadow-md transition-shadow"
    >
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-gray-900 dark:text-white truncate">{company.company_name}</h3>
          {company.city && (
            <p className="flex items-center gap-1 text-sm text-gray-500 dark:text-slate-400 mt-1">
              <MapPin className="w-3.5 h-3.5" />
              {company.city}
              {company.canton ? `, ${company.canton}` : ''}
            </p>
          )}
        </div>
        <div className="flex items-center gap-2 ml-2">
          <RatingBadge rating={ratingSummary?.average_rating ?? null} />
          <ChevronRight className="w-4 h-4 text-gray-400" />
        </div>
      </div>

      <div className="mt-3 flex flex-wrap gap-1.5">
        {company.work_categories.slice(0, 3).map((cat) => (
          <span
            key={cat}
            className="px-2 py-0.5 text-xs rounded-full bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300"
          >
            {t(`marketplace.work_category.${cat}`) || cat.replace(/_/g, ' ')}
          </span>
        ))}
        {company.work_categories.length > 3 && (
          <span className="px-2 py-0.5 text-xs rounded-full bg-gray-100 dark:bg-slate-700 text-gray-500 dark:text-slate-400">
            +{company.work_categories.length - 3}
          </span>
        )}
      </div>

      {company.regions_served && company.regions_served.length > 0 && (
        <p className="mt-2 text-xs text-gray-400 dark:text-slate-500">
          {t('marketplace.regions') || 'Regions'}: {company.regions_served.join(', ')}
        </p>
      )}
    </button>
  );
}

function CompanyDetail({
  company,
  onClose,
}: {
  company: CompanyProfile;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const { data: ratingSummary } = useQuery({
    queryKey: ['marketplace-rating', company.id],
    queryFn: () => marketplaceApi.getRatingSummary(company.id),
  });

  return (
    <div className="bg-white dark:bg-slate-800 rounded-lg border border-gray-200 dark:border-slate-700 p-6">
      <div className="flex items-start justify-between mb-4">
        <div>
          <h2 className="text-xl font-bold text-gray-900 dark:text-white">{company.company_name}</h2>
          {company.legal_form && (
            <p className="text-sm text-gray-500 dark:text-slate-400">{company.legal_form}</p>
          )}
        </div>
        <button
          onClick={onClose}
          className="p-1 rounded-lg hover:bg-gray-100 dark:hover:bg-slate-700"
        >
          <X className="w-5 h-5 text-gray-400" />
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        <div className="space-y-2">
          {company.address && (
            <p className="flex items-center gap-2 text-sm text-gray-600 dark:text-slate-300">
              <MapPin className="w-4 h-4 text-gray-400" />
              {company.address}, {company.postal_code} {company.city}
            </p>
          )}
          {company.employee_count && (
            <p className="flex items-center gap-2 text-sm text-gray-600 dark:text-slate-300">
              <Users className="w-4 h-4 text-gray-400" />
              {company.employee_count} {t('marketplace.employees') || 'employees'}
            </p>
          )}
          {company.years_experience && (
            <p className="flex items-center gap-2 text-sm text-gray-600 dark:text-slate-300">
              <Clock className="w-4 h-4 text-gray-400" />
              {company.years_experience} {t('marketplace.years_experience') || 'years experience'}
            </p>
          )}
        </div>
        <div>
          {ratingSummary && (
            <div className="bg-gray-50 dark:bg-slate-700/50 rounded-lg p-3">
              <div className="flex items-center gap-2 mb-2">
                <RatingBadge rating={ratingSummary.average_rating} />
                <span className="text-sm text-gray-500 dark:text-slate-400">
                  ({ratingSummary.total_reviews} {t('marketplace.reviews') || 'reviews'})
                </span>
              </div>
              <div className="space-y-1">
                {Object.entries(ratingSummary.rating_breakdown)
                  .sort(([a], [b]) => Number(b) - Number(a))
                  .map(([stars, count]) => (
                    <div key={stars} className="flex items-center gap-2 text-xs">
                      <span className="w-6 text-right text-gray-500 dark:text-slate-400">{stars}</span>
                      <Star className="w-3 h-3 text-amber-400 fill-amber-400" />
                      <div className="flex-1 bg-gray-200 dark:bg-slate-600 rounded-full h-1.5">
                        <div
                          className="bg-amber-400 h-1.5 rounded-full"
                          style={{
                            width: ratingSummary.total_reviews > 0 ? `${(count / ratingSummary.total_reviews) * 100}%` : '0%',
                          }}
                        />
                      </div>
                      <span className="w-4 text-gray-400 dark:text-slate-500">{count}</span>
                    </div>
                  ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {company.description && (
        <p className="text-sm text-gray-600 dark:text-slate-300 mb-4">{company.description}</p>
      )}

      <div className="space-y-3">
        <h3 className="text-sm font-medium text-gray-700 dark:text-slate-300">
          {t('marketplace.work_categories_title') || 'Work Categories'}
        </h3>
        <div className="flex flex-wrap gap-2">
          {company.work_categories.map((cat) => (
            <span
              key={cat}
              className="px-2.5 py-1 text-xs rounded-full bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300"
            >
              {t(`marketplace.work_category.${cat}`) || cat.replace(/_/g, ' ')}
            </span>
          ))}
        </div>
      </div>

      {company.certifications && company.certifications.length > 0 && (
        <div className="mt-4 space-y-2">
          <h3 className="text-sm font-medium text-gray-700 dark:text-slate-300">
            {t('marketplace.certifications') || 'Certifications'}
          </h3>
          <div className="space-y-1">
            {company.certifications.map((cert, i) => (
              <div key={i} className="flex items-center gap-2 text-sm">
                <Shield className="w-4 h-4 text-green-500" />
                <span className="text-gray-600 dark:text-slate-300">
                  {String(cert.name || cert.type || 'Certification')}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default function MarketplaceCompanies() {
  const { t } = useTranslation();
  const [canton, setCanton] = useState('');
  const [workCategory, setWorkCategory] = useState('');
  const [search, setSearch] = useState('');
  const [selectedCompany, setSelectedCompany] = useState<CompanyProfile | null>(null);

  const { data, isLoading, error } = useQuery({
    queryKey: ['marketplace-companies', canton, workCategory],
    queryFn: () =>
      marketplaceApi.listCompanies({
        canton: canton || undefined,
        work_category: workCategory || undefined,
        verified_only: true,
        size: 50,
      }),
  });

  const companies = (data?.items ?? []).filter((c) =>
    search ? c.company_name.toLowerCase().includes(search.toLowerCase()) : true,
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
          <Building2 className="w-6 h-6 text-red-600" />
          {t('marketplace.companies_title') || 'Remediation Companies'}
        </h1>
        <p className="text-sm text-gray-500 dark:text-slate-400 mt-1">
          {t('marketplace.companies_subtitle') || 'Verified remediation companies in the BatiConnect network'}
        </p>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder={t('marketplace.search_placeholder') || 'Search companies...'}
            className="w-full pl-9 pr-3 py-2 rounded-lg border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-800 text-sm text-gray-900 dark:text-white"
          />
        </div>
        <select
          value={canton}
          onChange={(e) => setCanton(e.target.value)}
          className="px-3 py-2 rounded-lg border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-800 text-sm text-gray-900 dark:text-white"
        >
          <option value="">{t('marketplace.all_cantons') || 'All cantons'}</option>
          {CANTONS.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
        <select
          value={workCategory}
          onChange={(e) => setWorkCategory(e.target.value)}
          className="px-3 py-2 rounded-lg border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-800 text-sm text-gray-900 dark:text-white"
        >
          <option value="">{t('marketplace.all_categories') || 'All categories'}</option>
          {WORK_CATEGORIES.map((wc) => (
            <option key={wc} value={wc}>
              {t(`marketplace.work_category.${wc}`) || wc.replace(/_/g, ' ')}
            </option>
          ))}
        </select>
      </div>

      {/* Content */}
      {isLoading && (
        <div className="flex items-center justify-center h-32">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-red-600" />
        </div>
      )}

      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 text-sm text-red-700 dark:text-red-300">
          {t('common.error') || 'An error occurred'}
        </div>
      )}

      {selectedCompany ? (
        <CompanyDetail company={selectedCompany} onClose={() => setSelectedCompany(null)} />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {companies.map((company) => (
            <CompanyCard key={company.id} company={company} onClick={() => setSelectedCompany(company)} />
          ))}
          {!isLoading && companies.length === 0 && (
            <div className="col-span-full text-center py-12 text-gray-400 dark:text-slate-500">
              {t('marketplace.no_companies') || 'No companies found'}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

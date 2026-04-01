/**
 * MIGRATION: KEEP BOUNDED
 * This page remains as a specialist view (org settings).
 * Not currently routed in App.tsx but used as component reference.
 * It must not own canonical truth — it is a projection.
 * Per ADR-006.
 */
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { useAuthStore } from '@/store/authStore';
import { organizationsApi } from '@/api/organizations';
import { invitationsApi } from '@/api/invitations';
import { usersApi } from '@/api/users';
import { cn } from '@/utils/formatters';
import { toast } from '@/store/toastStore';
import type { OrganizationType, User, UserRole } from '@/types';
import {
  Building2,
  Users,
  CreditCard,
  AlertTriangle,
  Loader2,
  Save,
  CheckCircle2,
  Mail,
  Phone,
  MapPin,
  UserPlus,
  Trash2,
  Lock,
  ArrowRightLeft,
  X,
  Info,
  ShieldCheck,
  Award,
  FileText,
  Database,
  ChevronDown,
} from 'lucide-react';

const orgTypeColors: Record<string, string> = {
  diagnostic_lab: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
  architecture_firm: 'bg-cyan-100 text-cyan-700 dark:bg-cyan-900/30 dark:text-cyan-400',
  property_management: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  authority: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
  contractor: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
};

const roleColors: Record<string, string> = {
  admin: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  owner: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  diagnostician: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
  architect: 'bg-cyan-100 text-cyan-700 dark:bg-cyan-900/30 dark:text-cyan-400',
  authority: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
  contractor: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
};

const ROLES: UserRole[] = ['admin', 'owner', 'diagnostician', 'architect', 'authority', 'contractor'];

interface OrgProfileForm {
  name: string;
  address: string;
  postal_code: string;
  city: string;
  canton: string;
  phone: string;
  email: string;
}

export default function OrganizationSettings() {
  const { t } = useTranslation();
  const { user } = useAuthStore();
  const queryClient = useQueryClient();

  const orgId = user?.organization_id;

  // Fetch organization
  const {
    data: org,
    isLoading: orgLoading,
    error: orgError,
  } = useQuery({
    queryKey: ['organization', orgId],
    queryFn: () => organizationsApi.get(orgId!),
    enabled: !!orgId,
  });

  // Fetch members
  const { data: members, isLoading: membersLoading } = useQuery({
    queryKey: ['organization-members', orgId],
    queryFn: () => organizationsApi.listMembers(orgId!),
    enabled: !!orgId,
  });

  // Profile edit state
  const [editing, setEditing] = useState(false);
  const [profileForm, setProfileForm] = useState<OrgProfileForm>({
    name: '',
    address: '',
    postal_code: '',
    city: '',
    canton: '',
    phone: '',
    email: '',
  });

  const startEditing = () => {
    if (org) {
      setProfileForm({
        name: org.name,
        address: org.address || '',
        postal_code: org.postal_code || '',
        city: org.city || '',
        canton: org.canton || '',
        phone: org.phone || '',
        email: org.email || '',
      });
      setEditing(true);
    }
  };

  const updateMutation = useMutation({
    mutationFn: (data: Partial<OrgProfileForm>) => organizationsApi.update(orgId!, data),
    onSuccess: (updated) => {
      queryClient.setQueryData(['organization', orgId], updated);
      queryClient.invalidateQueries({ queryKey: ['organization', orgId] });
      setEditing(false);
      toast(t('org_settings.profile_saved'), 'success');
    },
    onError: () => {
      toast(t('org_settings.profile_save_error'), 'error');
    },
  });

  const handleProfileSave = () => {
    updateMutation.mutate(profileForm);
  };

  // Invite modal
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState<UserRole>('diagnostician');

  const inviteMutation = useMutation({
    mutationFn: () =>
      invitationsApi.create({
        email: inviteEmail,
        role: inviteRole,
        organization_id: orgId!,
      }),
    onSuccess: () => {
      setShowInviteModal(false);
      setInviteEmail('');
      setInviteRole('diagnostician');
      queryClient.invalidateQueries({ queryKey: ['organization-members', orgId] });
      toast(t('org_settings.invite_sent'), 'success');
    },
    onError: () => {
      toast(t('org_settings.invite_error'), 'error');
    },
  });

  // Remove member
  const [removingMember, setRemovingMember] = useState<User | null>(null);

  const removeMemberMutation = useMutation({
    mutationFn: (memberId: string) => usersApi.update(memberId, { organization_id: null } as Partial<User>),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['organization-members', orgId] });
      queryClient.invalidateQueries({ queryKey: ['organization', orgId] });
      setRemovingMember(null);
      toast(t('org_settings.member_removed'), 'success');
    },
    onError: () => {
      toast(t('org_settings.member_remove_error'), 'error');
    },
  });

  // Role change
  const roleChangeMutation = useMutation({
    mutationFn: ({ memberId, role }: { memberId: string; role: string }) =>
      usersApi.update(memberId, { role } as Partial<User>),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['organization-members', orgId] });
      toast(t('org_settings.role_updated'), 'success');
    },
    onError: () => {
      toast(t('org_settings.role_update_error'), 'error');
    },
  });

  // No organization
  if (!orgId) {
    return (
      <div className="max-w-4xl mx-auto space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{t('org_settings.title')}</h1>
        </div>
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-12 text-center">
          <Building2 className="w-12 h-12 text-gray-300 dark:text-slate-600 mx-auto mb-3" />
          <p className="text-gray-500 dark:text-slate-400 text-sm">{t('org_settings.no_organization')}</p>
        </div>
      </div>
    );
  }

  if (orgLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-red-600" />
      </div>
    );
  }

  if (orgError || !org) {
    return (
      <div className="max-w-4xl mx-auto">
        <div className="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-xl p-8 text-center">
          <AlertTriangle className="w-8 h-8 text-red-500 dark:text-red-400 mx-auto mb-2" />
          <p className="text-red-700 dark:text-red-300">{t('app.error')}</p>
        </div>
      </div>
    );
  }

  const isAdmin = user?.role === 'admin';
  const isOwnerRole = user?.role === 'owner' || user?.role === 'admin';

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{t('org_settings.title')}</h1>
        <p className="text-sm text-gray-500 dark:text-slate-400 mt-1">{t('org_settings.subtitle')}</p>
      </div>

      {/* Organization Profile Section */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-6 shadow-sm">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
            <Building2 className="w-5 h-5 text-gray-400 dark:text-slate-500" />
            {t('org_settings.profile')}
          </h2>
          {isOwnerRole && !editing && (
            <button
              onClick={startEditing}
              className="text-sm text-red-600 dark:text-red-400 hover:text-red-700 dark:hover:text-red-300 font-medium"
            >
              {t('form.edit')}
            </button>
          )}
        </div>

        {editing ? (
          <div className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="sm:col-span-2">
                <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">
                  {t('org.name')} *
                </label>
                <input
                  type="text"
                  required
                  value={profileForm.name}
                  onChange={(e) => setProfileForm({ ...profileForm, name: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
                />
              </div>
              <div className="sm:col-span-2">
                <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">
                  {t('org.address')}
                </label>
                <input
                  type="text"
                  value={profileForm.address}
                  onChange={(e) => setProfileForm({ ...profileForm, address: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">
                  {t('org_settings.postal_code')}
                </label>
                <input
                  type="text"
                  value={profileForm.postal_code}
                  onChange={(e) => setProfileForm({ ...profileForm, postal_code: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">
                  {t('org.city')}
                </label>
                <input
                  type="text"
                  value={profileForm.city}
                  onChange={(e) => setProfileForm({ ...profileForm, city: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">
                  {t('org.canton')}
                </label>
                <input
                  type="text"
                  value={profileForm.canton}
                  onChange={(e) => setProfileForm({ ...profileForm, canton: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">
                  {t('org.phone')}
                </label>
                <input
                  type="tel"
                  value={profileForm.phone}
                  onChange={(e) => setProfileForm({ ...profileForm, phone: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
                />
              </div>
              <div className="sm:col-span-2">
                <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">
                  {t('org.email')}
                </label>
                <input
                  type="email"
                  value={profileForm.email}
                  onChange={(e) => setProfileForm({ ...profileForm, email: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
                />
              </div>
            </div>
            <div className="flex items-center gap-3 pt-2">
              <button
                onClick={handleProfileSave}
                disabled={updateMutation.isPending}
                className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 disabled:bg-red-400 transition-colors"
              >
                {updateMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                {t('settings.save')}
              </button>
              <button
                onClick={() => setEditing(false)}
                className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-slate-200 bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-700"
              >
                {t('form.cancel')}
              </button>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            {/* Logo placeholder + name + type */}
            <div className="flex items-start gap-4">
              <div className="w-16 h-16 rounded-xl bg-gray-100 dark:bg-slate-700 flex items-center justify-center flex-shrink-0">
                <Building2 className="w-8 h-8 text-gray-400 dark:text-slate-500" />
              </div>
              <div className="flex-1 min-w-0">
                <h3 className="text-xl font-bold text-gray-900 dark:text-white truncate">{org.name}</h3>
                <div className="flex items-center gap-2 mt-1">
                  <span
                    className={cn(
                      'px-2.5 py-0.5 text-xs font-medium rounded-full',
                      orgTypeColors[org.type] || 'bg-gray-100 text-gray-700 dark:bg-slate-700 dark:text-slate-300',
                    )}
                  >
                    {t(`org_type.${org.type}`) || org.type}
                  </span>
                  {org.suva_recognized && (
                    <span className="inline-flex items-center gap-1 px-1.5 py-0.5 text-xs font-medium bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400 rounded-full">
                      <ShieldCheck className="w-3 h-3" />
                      SUVA
                    </span>
                  )}
                  {org.fach_approved && (
                    <span className="inline-flex items-center gap-1 px-1.5 py-0.5 text-xs font-medium bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400 rounded-full">
                      <Award className="w-3 h-3" />
                      FACH
                    </span>
                  )}
                </div>
              </div>
            </div>

            {/* Contact info grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-4">
              {org.address && (
                <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-slate-300">
                  <MapPin className="w-4 h-4 text-gray-400 dark:text-slate-500 flex-shrink-0" />
                  <span>
                    {org.address}
                    {org.postal_code || org.city ? `, ${[org.postal_code, org.city].filter(Boolean).join(' ')}` : ''}
                    {org.canton ? ` (${org.canton})` : ''}
                  </span>
                </div>
              )}
              {org.phone && (
                <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-slate-300">
                  <Phone className="w-4 h-4 text-gray-400 dark:text-slate-500 flex-shrink-0" />
                  <span>{org.phone}</span>
                </div>
              )}
              {org.email && (
                <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-slate-300">
                  <Mail className="w-4 h-4 text-gray-400 dark:text-slate-500 flex-shrink-0" />
                  <span>{org.email}</span>
                </div>
              )}
              <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-slate-300">
                <Users className="w-4 h-4 text-gray-400 dark:text-slate-500 flex-shrink-0" />
                <span>
                  {org.member_count} {t('org.members').toLowerCase()}
                </span>
              </div>
            </div>

            {!org.address && !org.phone && !org.email && (
              <p className="text-sm text-gray-400 dark:text-slate-500 italic">{t('org_settings.no_contact_info')}</p>
            )}
          </div>
        )}
      </div>

      {/* Members Section */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-6 shadow-sm">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
            <Users className="w-5 h-5 text-gray-400 dark:text-slate-500" />
            {t('org_settings.members_title')}
            {members && (
              <span className="text-sm font-normal text-gray-500 dark:text-slate-400">({members.length})</span>
            )}
          </h2>
          {isOwnerRole && (
            <button
              onClick={() => setShowInviteModal(true)}
              className="inline-flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors"
            >
              <UserPlus className="w-4 h-4" />
              {t('org_settings.invite_member')}
            </button>
          )}
        </div>

        {membersLoading ? (
          <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-slate-400">
            <Loader2 className="w-4 h-4 animate-spin" />
            {t('app.loading')}
          </div>
        ) : !members || members.length === 0 ? (
          <div className="text-center py-8">
            <Users className="w-10 h-10 text-gray-300 dark:text-slate-600 mx-auto mb-2" />
            <p className="text-sm text-gray-500 dark:text-slate-400">{t('org_settings.no_members')}</p>
          </div>
        ) : (
          <div className="space-y-2">
            {members.map((member) => (
              <div
                key={member.id}
                className="flex items-center justify-between p-3 rounded-lg bg-gray-50 dark:bg-slate-700/50 hover:bg-gray-100 dark:hover:bg-slate-700 transition-colors"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-9 h-9 rounded-full bg-gray-200 dark:bg-slate-600 flex items-center justify-center flex-shrink-0">
                    <span className="text-sm font-medium text-gray-600 dark:text-slate-300">
                      {member.first_name?.[0]?.toUpperCase() || '?'}
                      {member.last_name?.[0]?.toUpperCase() || ''}
                    </span>
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                      {member.first_name} {member.last_name}
                      {member.id === user?.id && (
                        <span className="ml-1.5 text-xs text-gray-400 dark:text-slate-500">
                          ({t('org_settings.you')})
                        </span>
                      )}
                    </p>
                    <p className="text-xs text-gray-500 dark:text-slate-400 truncate">{member.email}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  {isAdmin && member.id !== user?.id ? (
                    <div className="relative">
                      <select
                        value={member.role}
                        onChange={(e) =>
                          roleChangeMutation.mutate({
                            memberId: member.id,
                            role: e.target.value,
                          })
                        }
                        disabled={roleChangeMutation.isPending}
                        className={cn(
                          'appearance-none pl-2 pr-6 py-1 text-xs font-medium rounded-full border-0 cursor-pointer focus:outline-none focus:ring-2 focus:ring-red-500',
                          roleColors[member.role] || 'bg-gray-100 text-gray-700 dark:bg-slate-700 dark:text-slate-300',
                        )}
                      >
                        {ROLES.map((r) => (
                          <option key={r} value={r}>
                            {t(`role.${r}`) || r}
                          </option>
                        ))}
                      </select>
                      <ChevronDown className="absolute right-1.5 top-1/2 -translate-y-1/2 w-3 h-3 pointer-events-none text-current opacity-60" />
                    </div>
                  ) : (
                    <span
                      className={cn(
                        'px-2 py-0.5 text-xs font-medium rounded-full',
                        roleColors[member.role] || 'bg-gray-100 text-gray-700 dark:bg-slate-700 dark:text-slate-300',
                      )}
                    >
                      {t(`role.${member.role}`) || member.role}
                    </span>
                  )}
                  {isOwnerRole && member.id !== user?.id && (
                    <button
                      onClick={() => setRemovingMember(member)}
                      title={t('org_settings.remove_member')}
                      className="p-1.5 text-gray-400 dark:text-slate-500 hover:text-red-600 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Billing Placeholder Section */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-6 flex items-center gap-2">
          <CreditCard className="w-5 h-5 text-gray-400 dark:text-slate-500" />
          {t('org_settings.billing_title')}
        </h2>

        {/* Current plan */}
        <div className="mb-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="px-3 py-1.5 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 text-sm font-semibold rounded-lg">
              {t('org_settings.plan_free')}
            </div>
            <span className="text-xs text-gray-400 dark:text-slate-500 italic">{t('org_settings.coming_soon')}</span>
          </div>

          {/* Plan options (disabled placeholders) */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {(['free', 'pro', 'enterprise'] as const).map((plan) => (
              <div
                key={plan}
                className={cn(
                  'rounded-xl border-2 p-4',
                  plan === 'free'
                    ? 'border-green-300 dark:border-green-700 bg-green-50/50 dark:bg-green-900/10'
                    : 'border-gray-200 dark:border-slate-700 opacity-60',
                )}
              >
                <p className="text-sm font-semibold text-gray-900 dark:text-white">{t(`org_settings.plan_${plan}`)}</p>
                <p className="text-xs text-gray-500 dark:text-slate-400 mt-1">{t(`org_settings.plan_${plan}_desc`)}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Usage stats placeholder */}
        <div className="border-t border-gray-200 dark:border-slate-700 pt-4">
          <h3 className="text-sm font-medium text-gray-700 dark:text-slate-200 mb-3">
            {t('org_settings.usage_title')}
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="bg-gray-50 dark:bg-slate-700/50 rounded-lg p-3">
              <div className="flex items-center gap-2 mb-1">
                <Building2 className="w-4 h-4 text-gray-400 dark:text-slate-500" />
                <span className="text-xs text-gray-500 dark:text-slate-400">{t('org_settings.usage_buildings')}</span>
              </div>
              <p className="text-lg font-semibold text-gray-900 dark:text-white">--</p>
            </div>
            <div className="bg-gray-50 dark:bg-slate-700/50 rounded-lg p-3">
              <div className="flex items-center gap-2 mb-1">
                <FileText className="w-4 h-4 text-gray-400 dark:text-slate-500" />
                <span className="text-xs text-gray-500 dark:text-slate-400">{t('org_settings.usage_diagnostics')}</span>
              </div>
              <p className="text-lg font-semibold text-gray-900 dark:text-white">--</p>
            </div>
            <div className="bg-gray-50 dark:bg-slate-700/50 rounded-lg p-3">
              <div className="flex items-center gap-2 mb-1">
                <Database className="w-4 h-4 text-gray-400 dark:text-slate-500" />
                <span className="text-xs text-gray-500 dark:text-slate-400">{t('org_settings.usage_storage')}</span>
              </div>
              <p className="text-lg font-semibold text-gray-900 dark:text-white">--</p>
            </div>
          </div>
        </div>
      </div>

      {/* Organization Type Info Section */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
          <Info className="w-5 h-5 text-gray-400 dark:text-slate-500" />
          {t('org_settings.type_info_title')}
        </h2>

        <div className="flex items-center gap-2 mb-4">
          <span
            className={cn(
              'px-2.5 py-0.5 text-xs font-medium rounded-full',
              orgTypeColors[org.type] || 'bg-gray-100 text-gray-700 dark:bg-slate-700 dark:text-slate-300',
            )}
          >
            {t(`org_type.${org.type}`) || org.type}
          </span>
        </div>

        <p className="text-sm text-gray-600 dark:text-slate-300 mb-4">{t(`org_settings.type_desc_${org.type}`)}</p>

        <div className="space-y-2">
          {getOrgTypeFeatures(org.type).map((feature, idx) => (
            <div key={idx} className="flex items-center gap-2 text-sm text-gray-600 dark:text-slate-300">
              <CheckCircle2 className="w-4 h-4 text-green-500 dark:text-green-400 flex-shrink-0" />
              <span>{t(feature)}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Danger Zone */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border-2 border-red-200 dark:border-red-900/50 p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-red-700 dark:text-red-400 mb-2 flex items-center gap-2">
          <AlertTriangle className="w-5 h-5" />
          {t('org_settings.danger_zone')}
        </h2>
        <p className="text-sm text-gray-500 dark:text-slate-400 mb-6">{t('org_settings.danger_zone_desc')}</p>

        <div className="space-y-4">
          {/* Transfer ownership */}
          <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-slate-700/50 rounded-lg">
            <div>
              <p className="text-sm font-medium text-gray-900 dark:text-white flex items-center gap-2">
                <ArrowRightLeft className="w-4 h-4" />
                {t('org_settings.transfer_ownership')}
              </p>
              <p className="text-xs text-gray-500 dark:text-slate-400 mt-0.5">
                {t('org_settings.transfer_ownership_desc')}
              </p>
            </div>
            <button
              disabled
              className="inline-flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-gray-400 dark:text-slate-500 bg-gray-100 dark:bg-slate-700 rounded-lg cursor-not-allowed"
            >
              <Lock className="w-3.5 h-3.5" />
              {t('org_settings.transfer')}
            </button>
          </div>

          {/* Delete organization */}
          <div className="flex items-center justify-between p-4 bg-red-50 dark:bg-red-900/10 rounded-lg">
            <div>
              <p className="text-sm font-medium text-red-700 dark:text-red-400 flex items-center gap-2">
                <Trash2 className="w-4 h-4" />
                {t('org_settings.delete_org')}
              </p>
              <p className="text-xs text-red-600/70 dark:text-red-400/60 mt-0.5">{t('org_settings.delete_org_desc')}</p>
            </div>
            <button
              disabled
              className="inline-flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-gray-400 dark:text-slate-500 bg-gray-100 dark:bg-slate-700 rounded-lg cursor-not-allowed"
            >
              <Lock className="w-3.5 h-3.5" />
              {t('form.delete')}
            </button>
          </div>
        </div>
      </div>

      {/* Invite Modal */}
      {showInviteModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl w-full max-w-md mx-4 p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-bold text-gray-900 dark:text-white">{t('org_settings.invite_member')}</h2>
              <button
                onClick={() => setShowInviteModal(false)}
                className="p-1 hover:bg-gray-100 dark:hover:bg-slate-600 rounded-lg"
                aria-label={t('form.close')}
              >
                <X className="w-5 h-5 text-gray-500 dark:text-slate-400" />
              </button>
            </div>

            <form
              onSubmit={(e) => {
                e.preventDefault();
                inviteMutation.mutate();
              }}
              className="space-y-4"
            >
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">
                  {t('org.email')} *
                </label>
                <input
                  type="email"
                  required
                  value={inviteEmail}
                  onChange={(e) => setInviteEmail(e.target.value)}
                  placeholder={t('org_settings.invite_email_placeholder')}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">
                  {t('user.role')} *
                </label>
                <select
                  required
                  value={inviteRole}
                  onChange={(e) => setInviteRole(e.target.value as UserRole)}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
                >
                  {ROLES.map((r) => (
                    <option key={r} value={r}>
                      {t(`role.${r}`) || r}
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowInviteModal(false)}
                  className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-slate-200 bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-700"
                >
                  {t('form.cancel')}
                </button>
                <button
                  type="submit"
                  disabled={inviteMutation.isPending}
                  className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 disabled:bg-red-400"
                >
                  {inviteMutation.isPending && <Loader2 className="w-4 h-4 animate-spin" />}
                  {t('invitation.send')}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Remove Member Confirmation */}
      {removingMember && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl w-full max-w-sm mx-4 p-6">
            <h2 className="text-lg font-bold text-gray-900 dark:text-white mb-2">{t('org_settings.remove_member')}</h2>
            <p className="text-sm text-gray-600 dark:text-slate-300 mb-6">
              {t('org_settings.remove_member_confirm')}{' '}
              <span className="font-semibold">
                {removingMember.first_name} {removingMember.last_name}
              </span>
              ?
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setRemovingMember(null)}
                className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-slate-200 bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-700"
              >
                {t('form.cancel')}
              </button>
              <button
                onClick={() => removeMemberMutation.mutate(removingMember.id)}
                disabled={removeMemberMutation.isPending}
                className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 disabled:bg-red-400"
              >
                {removeMemberMutation.isPending && <Loader2 className="w-4 h-4 animate-spin" />}
                {t('org_settings.remove')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * Returns i18n keys for features associated with each org type.
 */
function getOrgTypeFeatures(orgType: OrganizationType): string[] {
  const featureMap: Record<OrganizationType, string[]> = {
    diagnostic_lab: [
      'org_settings.feature_create_diagnostics',
      'org_settings.feature_manage_samples',
      'org_settings.feature_generate_reports',
      'org_settings.feature_suva_notifications',
    ],
    architecture_firm: [
      'org_settings.feature_view_buildings',
      'org_settings.feature_manage_interventions',
      'org_settings.feature_plan_renovations',
      'org_settings.feature_view_diagnostics',
    ],
    property_management: [
      'org_settings.feature_manage_buildings',
      'org_settings.feature_portfolio_overview',
      'org_settings.feature_assign_diagnostics',
      'org_settings.feature_export_dossiers',
    ],
    authority: [
      'org_settings.feature_review_compliance',
      'org_settings.feature_view_authority_packs',
      'org_settings.feature_regulatory_oversight',
      'org_settings.feature_audit_trail',
    ],
    contractor: [
      'org_settings.feature_view_interventions',
      'org_settings.feature_update_progress',
      'org_settings.feature_document_works',
      'org_settings.feature_safety_compliance',
    ],
  };
  return featureMap[orgType] || [];
}

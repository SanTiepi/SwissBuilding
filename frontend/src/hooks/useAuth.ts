import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { authApi } from '@/api/auth';
import { useAuthStore } from '@/store/authStore';
import type { LoginRequest } from '@/types';

export function useAuth() {
  const queryClient = useQueryClient();
  const { token, user, isAuthenticated, setAuth, logout: storeLogout } = useAuthStore();

  const { isLoading: isMeLoading } = useQuery({
    queryKey: ['auth', 'me'],
    queryFn: () => authApi.getMe(),
    enabled: !!token && !user,
    retry: false,
    select: (data) => {
      useAuthStore.getState().updateUser(data);
      return data;
    },
  });

  const loginMutation = useMutation({
    mutationFn: (data: LoginRequest) => authApi.login(data),
    onSuccess: (response) => {
      setAuth(response.access_token, response.user);
    },
  });

  const registerMutation = useMutation({
    mutationFn: (data: {
      email: string;
      password: string;
      first_name: string;
      last_name: string;
      role?: string;
      language?: string;
    }) => authApi.register(data),
  });

  const logout = () => {
    storeLogout();
    queryClient.clear();
  };

  return {
    user,
    token,
    isAuthenticated,
    login: loginMutation,
    register: registerMutation,
    logout,
    isLoading: isMeLoading,
  };
}

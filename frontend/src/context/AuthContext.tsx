import React, { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { useAuth as useClerkAuth, useClerk, useUser } from '@clerk/react';
import { toast } from 'sonner';

export interface AuthUser {
  id: string;
  email: string;
  full_name?: string;
  timezone?: string;
  preferred_persona?: string;
}

interface AuthContextType {
  user: AuthUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  isLoginModalOpen: boolean;
  openLoginModal: () => void;
  closeLoginModal: () => void;
  logout: () => Promise<void>;
  getAuthHeaders: () => Promise<Record<string, string>>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const { isLoaded, isSignedIn, getToken } = useClerkAuth();
  const { user: clerkUser } = useUser();
  const { signOut } = useClerk();
  const [isLoginModalOpen, setIsLoginModalOpen] = useState(false);

  // Clerk completes sign-in asynchronously. Close our surrounding modal as
  // soon as its authoritative session state changes, otherwise the completed
  // form stays over the application and blocks Connections and Voice actions.
  useEffect(() => {
    if (isSignedIn) setIsLoginModalOpen(false);
  }, [isSignedIn]);

  const user = useMemo<AuthUser | null>(() => {
    if (!isSignedIn || !clerkUser) return null;
    return {
      id: clerkUser.id,
      email: clerkUser.primaryEmailAddress?.emailAddress || '',
      full_name: clerkUser.fullName || clerkUser.username || 'User',
    };
  }, [clerkUser, isSignedIn]);

  const getAuthHeaders = useCallback(async (): Promise<Record<string, string>> => {
    const token = await getToken();
    return token ? { Authorization: `Bearer ${token}` } : {};
  }, [getToken]);

  const logout = useCallback(async () => {
    await signOut();
    toast.info('Signed Out', { description: 'You have been disconnected from your Shinra session.' });
  }, [signOut]);

  const value = useMemo<AuthContextType>(() => ({
    user,
    isAuthenticated: Boolean(isLoaded && isSignedIn),
    isLoading: !isLoaded,
    isLoginModalOpen,
    openLoginModal: () => setIsLoginModalOpen(true),
    closeLoginModal: () => setIsLoginModalOpen(false),
    logout,
    getAuthHeaders,
  }), [getAuthHeaders, isLoaded, isLoginModalOpen, isSignedIn, logout, user]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within an AuthProvider');
  return context;
};

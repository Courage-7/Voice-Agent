import React from 'react';
import { SignIn } from '@clerk/react';
import { X } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';

/** Clerk owns the email-code flow; this shell only keeps it in Shinra's UI. */
export const LoginModal: React.FC = () => {
  const { isLoginModalOpen, closeLoginModal } = useAuth();
  if (!isLoginModalOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#1d1d1b]/40 backdrop-blur-[2px]">
      <section className="relative max-h-full overflow-y-auto rounded-2xl" aria-label="Sign in to Shinra">
        <button
          type="button"
          onClick={closeLoginModal}
          aria-label="Close sign-in dialog"
          className="absolute z-10 top-3 right-3 p-1.5 rounded-md text-[var(--color-muted)] hover:text-[var(--color-ink)] hover:bg-[var(--color-surface-muted)]"
        >
          <X className="w-4 h-4" />
        </button>
        <SignIn
          routing="hash"
          fallbackRedirectUrl="/"
          signUpFallbackRedirectUrl="/"
          withSignUp
        />
      </section>
    </div>
  );
};

export default LoginModal;

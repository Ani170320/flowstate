'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { authService } from '@/services/authService';
import { Button } from '@/components/ui/Button';
import { Mail, ArrowLeft, CheckCircle2, ShieldCheck } from 'lucide-react';

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) return;

    setIsLoading(true);
    try {
      await authService.requestPasswordReset(email);
      setIsSubmitted(true);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="w-full max-w-md mx-auto relative z-10 animate-in fade-in duration-300">
      <div className="bg-[#151922]/90 backdrop-blur-2xl border border-[#252B36] rounded-3xl p-6 sm:p-8 shadow-2xl shadow-black/80 animate-border-glow space-y-6">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-[#F5F7FA]">Reset Password</h2>
          <p className="text-xs text-[#929AAA] mt-1">
            Enter your registered email to receive secure recovery credentials.
          </p>
        </div>

        {isSubmitted ? (
          <div className="text-center py-6 space-y-4">
            <div className="w-12 h-12 rounded-full bg-emerald-500/15 border border-emerald-500/30 text-emerald-400 mx-auto flex items-center justify-center">
              <CheckCircle2 className="w-6 h-6" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-[#F5F7FA]">Check your inbox</h3>
              <p className="text-xs text-[#929AAA] mt-1">
                We sent password reset instructions to{' '}
                <span className="text-[var(--accent)] font-medium">{email}</span>.
              </p>
            </div>
            <Link href="/login" className="inline-block pt-2">
              <Button variant="secondary" size="sm" className="gap-1.5">
                <ArrowLeft className="w-3.5 h-3.5" />
                <span>Back to Sign In</span>
              </Button>
            </Link>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <label className="block text-xs font-medium text-[#929AAA]">Email Address</label>
              <div className="relative">
                <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-[#929AAA] pointer-events-none" />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="alex@flowstate.dev"
                  className="w-full h-10 pl-10 pr-3.5 rounded-xl bg-[#10131A] border border-[#252B36] text-xs text-[#F5F7FA] placeholder-[#929AAA]/60 focus:outline-none focus:border-[var(--accent)] focus:ring-2 focus:ring-[var(--accent-subtle)] transition-all"
                  autoFocus
                />
              </div>
            </div>

            <Button
              type="submit"
              variant="primary"
              size="lg"
              className="w-full mt-2"
              isLoading={isLoading}
            >
              Send Reset Link
            </Button>

            <div className="pt-2 text-center">
              <Link
                href="/login"
                className="inline-flex items-center gap-1.5 text-xs text-[#929AAA] hover:text-[#F5F7FA] transition-colors"
              >
                <ArrowLeft className="w-3.5 h-3.5" />
                <span>Back to Sign In</span>
              </Link>
            </div>
          </form>
        )}
      </div>

      <div className="mt-4 flex items-center justify-center gap-2 text-xs text-[#929AAA]">
        <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
        <span>Self-service cryptographic password recovery</span>
      </div>
    </div>
  );
}

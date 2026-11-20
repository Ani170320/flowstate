import type { Metadata } from 'next';
import { Geist, Geist_Mono } from 'next/font/google';
import './globals.css';
import { ToastProvider } from '@/context/ToastContext';
import { AuthProvider } from '@/context/AuthContext';
import { WorkspaceProvider } from '@/context/WorkspaceContext';
import { ThemeProvider } from '@/context/ThemeContext';

const geistSans = Geist({
  variable: '--font-geist-sans',
  subsets: ['latin'],
});

const geistMono = Geist_Mono({
  variable: '--font-geist-mono',
  subsets: ['latin'],
});

export const metadata: Metadata = {
  title: 'FLOWSTATE – Full-Stack Project & Team Management SaaS',
  description: 'A modern, high-craft project management and team collaboration platform built for high-velocity teams.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable} dark`} suppressHydrationWarning>
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `
              (function() {
                try {
                  var theme = localStorage.getItem('flowstate_theme') || 'dark';
                  var accent = localStorage.getItem('flowstate_accent_color') || '#8B7CFF';
                  var root = document.documentElement;
                  root.setAttribute('data-theme', theme);
                  if (theme === 'midnight') {
                    root.style.setProperty('--bg-primary', '#000000');
                    root.style.setProperty('--bg-sidebar', '#050608');
                    root.style.setProperty('--bg-card', '#090C11');
                    root.style.setProperty('--bg-card-hover', '#121620');
                    root.style.setProperty('--border-color', '#1A1F2B');
                    root.style.setProperty('--border-light', '#252B36');
                  }
                  root.style.setProperty('--accent', accent);
                  root.style.setProperty('--color-brand-accent', accent);
                  
                  new MutationObserver(function(mutations) {
                    for (var i = 0; i < mutations.length; i++) {
                      var m = mutations[i];
                      if (m.type === 'attributes' && m.attributeName === 'fdprocessedid' && m.target) {
                        m.target.removeAttribute('fdprocessedid');
                      }
                    }
                  }).observe(document.documentElement, {
                    attributes: true,
                    subtree: true,
                    attributeFilter: ['fdprocessedid']
                  });
                } catch (e) {}
              })();
            `,
          }}
        />
      </head>
      <body className="min-h-screen bg-[var(--bg-primary)] text-[#F5F7FA] antialiased" suppressHydrationWarning>
        <ToastProvider>
          <AuthProvider>
            <ThemeProvider>
              <WorkspaceProvider>{children}</WorkspaceProvider>
            </ThemeProvider>
          </AuthProvider>
        </ToastProvider>
      </body>
    </html>
  );
}

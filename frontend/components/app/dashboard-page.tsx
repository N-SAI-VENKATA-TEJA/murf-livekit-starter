'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { DashboardView } from '@/components/app/dashboard-view';

export function DashboardPage() {
  const router = useRouter();

  // Guard: if not authenticated, redirect back to home
  useEffect(() => {
    fetch('/api/auth/me')
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (!data?.authenticated) {
          router.replace('/');
        }
      })
      .catch(() => {
        router.replace('/');
      });
  }, [router]);

  const handleBack = () => {
    router.push('/');
  };

  return <DashboardView onBack={handleBack} />;
}


import LandingPage from '@/src/components/LandingPage';
import ErrorBoundary from '@/src/components/ErrorBoundary';

export default function Home() {
  return (
    <ErrorBoundary>
      <LandingPage />
    </ErrorBoundary>
  );
}

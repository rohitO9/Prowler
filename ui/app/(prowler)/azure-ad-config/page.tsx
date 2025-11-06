import { ContentLayout } from '@/components/ui/content-layout/content-layout';
import { AzureADConfigClient } from './azure-ad-config-client.tsx';

export default function AzureADConfigPage() {
  return (
    <ContentLayout title="Azure AD Configuration" icon="🔒">
      <AzureADConfigClient />
    </ContentLayout>
  );
}
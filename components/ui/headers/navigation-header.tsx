import React, { Suspense, use } from "react";

import { getUserInfo } from "@/actions/users/users";
import { ContentLayout } from "@/components/ui/content-layout/content-layout";
import { SkeletonContentLayout } from "@/components/ui/content-layout/skeleton-content-layout";

interface NavigationHeaderProps {
  title: string;
  icon: string | React.ReactNode;
  children: React.ReactNode;
}

export const NavigationHeader: React.FC<NavigationHeaderProps> = ({
  title,
  icon,
  children,
}) => {
  return (
    <Suspense fallback={<SkeletonContentLayout />}>
      <ContentLayout title={title} icon={icon}>
        {children}
      </ContentLayout>
    </Suspense>
  );
};

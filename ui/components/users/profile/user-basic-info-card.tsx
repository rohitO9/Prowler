"use client";

import { Card, CardBody, Chip } from "@nextui-org/react";
import { Calendar, Building2, Mail, User as UserIcon, Shield, CheckCircle2 } from "lucide-react";
import { DateWithTime, InfoField, SnippetChip } from "@/components/ui/entities";
import { UserDataWithRoles } from "@/types/users";

const TenantIdCopy = ({ id }: { id: string }) => {
  return (
    <div className="flex items-center gap-2">
      <SnippetChip value={id} />
    </div>
  );
};

export const UserBasicInfoCard = ({
  user,
  tenantId,
}: {
  user: UserDataWithRoles;
  tenantId?: string;
}) => {
  // Handle double-nested data structure
  // Type assertion needed because data is typed as 'any' in UserDataWithRoles
  const attributes = 
    (user as any)?.data?.data?.attributes || 
    (user as any)?.data?.attributes || 
    user?.attributes;
  
  if (!attributes) {
    return (
      <Card className="shadow-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 w-full">
        <CardBody>
          <div className="flex items-center justify-center min-h-32">
            <p className="text-muted-foreground">Unable to load user information</p>
          </div>
        </CardBody>
      </Card>
    );
  }

  const { name, email, company_name, date_joined } = attributes;
  
  // Get initials for avatar
  const getInitials = (name: string) => {
    return name
      .split(' ')
      .map(n => n[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);
  };

  return (
    <Card className="shadow-xl border-0 bg-gradient-to-br from-white to-gray-50 dark:from-gray-900 dark:to-gray-800 w-full overflow-hidden">
      <CardBody className="p-8">
        {/* Hero Section */}
        <div className="flex flex-col md:flex-row items-start md:items-center gap-6 mb-8">
          {/* Avatar Section */}
          <div className="relative">
            <div className="relative w-24 h-24 rounded-2xl bg-gradient-to-br from-indigo-500 to-blue-600 flex items-center justify-center shadow-lg ring-4 ring-white dark:ring-gray-800">
              <span className="text-3xl font-bold text-white">
                {getInitials(name)}
              </span>
            </div>
            <div className="absolute -bottom-1 -right-1 w-8 h-8 bg-green-500 rounded-full border-4 border-white dark:border-gray-800 flex items-center justify-center">
              <CheckCircle2 className="w-4 h-4 text-white" />
            </div>
          </div>

          {/* User Info Section */}
          <div className="flex-1">
            <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
              <div>
                <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
                  {name}
                </h1>
                <div className="flex flex-wrap items-center gap-3">
                  <div className="flex items-center gap-2 text-gray-600 dark:text-gray-300">
                    <Mail className="w-4 h-4" />
                    <span className="text-sm font-medium">{email}</span>
                  </div>
                  {company_name && (
                    <>
                      <span className="text-gray-300 dark:text-gray-600">•</span>
                      <div className="flex items-center gap-2 text-gray-600 dark:text-gray-300">
                        <Building2 className="w-4 h-4" />
                        <span className="text-sm font-medium">{company_name}</span>
                      </div>
                    </>
                  )}
                </div>
              </div>
              
              {/* Role Badge */}
              <div className="flex items-center gap-2">
                <Chip
                  startContent={<Shield className="w-4 h-4" />}
                  variant="flat"
                  color="primary"
                  className="bg-indigo-100 dark:bg-indigo-900 text-indigo-700 dark:text-indigo-200 font-semibold"
                >
                  Active User
                </Chip>
              </div>
            </div>
          </div>
        </div>

        {/* Info Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-6 border-t border-gray-200 dark:border-gray-700">
          {/* Date Joined */}
          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-2 text-gray-500 dark:text-gray-400">
              <Calendar className="w-4 h-4" />
              <span className="text-xs font-semibold uppercase tracking-wide">Member Since</span>
            </div>
            <p className="text-sm font-medium text-gray-900 dark:text-white">
              <DateWithTime inline dateTime={date_joined} showTime={false} />
            </p>
          </div>

          {/* Organization ID */}
          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-2 text-gray-500 dark:text-gray-400">
              <Building2 className="w-4 h-4" />
              <span className="text-xs font-semibold uppercase tracking-wide">Organization ID</span>
            </div>
            {tenantId ? (
              <TenantIdCopy id={tenantId} />
            ) : (
              <p className="text-sm text-gray-400 dark:text-gray-500">Not available</p>
            )}
          </div>

          {/* Status */}
          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-2 text-gray-500 dark:text-gray-400">
              <CheckCircle2 className="w-4 h-4" />
              <span className="text-xs font-semibold uppercase tracking-wide">Status</span>
            </div>
            <Chip
              size="sm"
              variant="flat"
              color="success"
              className="w-fit"
            >
              Verified
            </Chip>
          </div>
        </div>
      </CardBody>
    </Card>
  );
};
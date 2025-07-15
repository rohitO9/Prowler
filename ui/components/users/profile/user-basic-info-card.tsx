"use client";

import { Card, CardBody, Divider, Button, Chip } from "@nextui-org/react";
import { Calendar, Building2, Copy, User as UserIcon, Mail } from "lucide-react";
import { DateWithTime, InfoField, SnippetChip } from "@/components/ui/entities";
import { UserDataWithRoles } from "@/types/users";
import { ProwlerShort } from "../../icons";

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
  tenantId: string;
}) => {
  const { name, email, company_name, date_joined } = user.attributes;

  return (
    <Card className="shadow-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-prowler-blue-400 w-full">
      <CardBody>
        {/* Horizontal layout: left (icon, name, email), right (date joined, org id) */}
        <div className="flex flex-row items-center justify-between gap-6 mt-4  w-full">
          {/* Left: Date Joined */}
          <div className="flex flex-1 justify-start">
            <div className="flex items-center gap-2">
              <Calendar size={18} className="text-gray-400" />
              <InfoField label="Date Joined" variant="simple">
                <DateWithTime inline dateTime={date_joined} />
              </InfoField>
            </div>
          </div>

          {/* Center: Icon, Name, Organization ID */}
          <div className="flex flex-col items-center justify-center gap-2 min-w-[120px]">
            <div className="relative">
              <div className="rounded-full border-4 border-white dark:border-prowler-blue-400 shadow-md bg-gray-50 dark:bg-prowler-blue-200 w-20 h-20 flex items-center justify-center">
                <UserIcon size={48} className="text-indigo-400" />
              </div>
            </div>
            <span className="text-2xl font-extrabold bg-gradient-to-r from-indigo-500 to-purple-600 bg-clip-text text-transparent">
              {name}
            </span>
            <span className="text-xs font-semibold text-gray-500 dark:text-gray-300 text-center">Organization ID</span>
            <div className="flex items-center gap-2">
              <Building2 size={18} className="text-gray-400" />
              <TenantIdCopy id={tenantId} />
            </div>
          </div>

          {/* Right: Email */}
          <div className="flex flex-1 justify-end">
            <div className="flex items-center gap-2">
              <InfoField label="Email" variant="transparent">
                <span className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-100">
                  <Mail size={18} className="text-gray-400" />
                  {email}
                </span>
              </InfoField>
            </div>
          </div>
        </div>
      </CardBody>
    </Card>
  );
};

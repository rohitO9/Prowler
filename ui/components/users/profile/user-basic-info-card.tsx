"use client";

import { Card, CardBody, Divider, Button, Chip } from "@nextui-org/react";
import { Calendar, Building2, Copy, User as UserIcon } from "lucide-react";
import { DateWithTime, InfoField, SnippetChip } from "@/components/ui/entities";
import { UserDataWithRoles } from "@/types/users";
import { ProwlerShort } from "../../icons";

const TenantIdCopy = ({ id }: { id: string }) => {
  return (
    <div className="flex items-center gap-2">
      <SnippetChip value={id} />
      <Copy size={16} className="text-gray-400 cursor-pointer" />
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
    <Card className="shadow-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-prowler-blue-400 max-w-xl mx-auto">
      <CardBody>
        {/* Banner/cover image placeholder */}
       
        <div className="flex flex-col items-center mt-5 mb-4">
          <div className="relative">
            <div className="rounded-full border-4 border-white dark:border-prowler-blue-400 shadow-md bg-gray-50 dark:bg-prowler-blue-200 w-20 h-20 flex items-center justify-center">
              <UserIcon size={48} className="text-indigo-400" />
            </div>
          </div>
          <span className="mt-3 text-2xl font-extrabold bg-gradient-to-r from-indigo-500 to-purple-600 bg-clip-text text-transparent">
            {name}
          </span>
         
          <span className="mt-1 text-sm text-gray-500 dark:text-gray-300">{email}</span>
        </div>
        <Divider className="my-4" />
        <div className="flex flex-col md:flex-row gap-4 justify-center items-center">
          <div className="flex items-center gap-2">
            <Calendar size={18} className="text-gray-400" />
            <InfoField label="Date Joined" variant="simple">
              <DateWithTime inline dateTime={date_joined} />
            </InfoField>
          </div>
          <div className="flex items-center gap-2">
            <Building2 size={18} className="text-gray-400" />
            <InfoField label="Organization ID" variant="transparent">
              <TenantIdCopy id={tenantId} />
            </InfoField>
          </div>
        </div>
      
      </CardBody>
    </Card>
  );
};

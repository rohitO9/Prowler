"use client";

import { Chip } from "@nextui-org/react";
import { useState } from "react";
import { Building2, Calendar, Edit2, Shield } from "lucide-react";

import { CustomAlertModal, CustomButton } from "@/components/ui/custom";
import { DateWithTime } from "@/components/ui/entities";
import { MembershipDetailData } from "@/types/users";

import { EditTenantForm } from "../forms";
import { RolesCard } from "./roles-card";

export const MembershipItem = ({
  membership,
  tenantName,
  tenantId,
  isOwner,
  roles,
  roleDetails,
}: {
  membership: MembershipDetailData;
  tenantName: string;
  tenantId: string;
  isOwner: boolean;
  roles: any[];
  roleDetails: Record<string, any>;
}) => {
  const [isEditOpen, setIsEditOpen] = useState(false);

  return (
    <>
      <CustomAlertModal
        isOpen={isEditOpen}
        onOpenChange={setIsEditOpen}
        title=""
        className="max-w-lg"
      >
        <EditTenantForm
          tenantId={tenantId}
          tenantName={tenantName}
          setIsOpen={setIsEditOpen}
        />
      </CustomAlertModal>

      <div className="group relative rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-5 hover:shadow-lg transition-all duration-200 hover:border-indigo-300 dark:hover:border-indigo-600">
        <div className="flex flex-col md:flex-row md:items-center gap-4">
          {/* Organization Icon */}
          <div className="flex-shrink-0">
            <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-indigo-500 to-blue-600 flex items-center justify-center shadow-md">
              <Building2 className="w-6 h-6 text-white" />
            </div>
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
              <div className="flex-1 min-w-0">
                <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-1 truncate">
                  {tenantName}
                </h3>
                <div className="flex flex-wrap items-center gap-3">
                  <Chip
                    startContent={<Shield className="w-3 h-3" />}
                    size="sm"
                    variant="flat"
                    color="secondary"
                    className="bg-indigo-100 dark:bg-indigo-900 text-indigo-700 dark:text-indigo-200 font-medium"
                  >
                    {membership.attributes.role}
                  </Chip>
                  <div className="flex items-center gap-1.5 text-sm text-gray-600 dark:text-gray-400">
                    <Calendar className="w-4 h-4" />
                    <span className="font-medium">Joined</span>
                    <DateWithTime
                      inline
                      showTime={false}
                      dateTime={membership.attributes.date_joined}
                    />
                  </div>
                </div>
              </div>

              {/* Actions */}
              {isOwner && (
                <CustomButton
                  type="button"
                  ariaLabel="Edit organization name"
                  className="flex-shrink-0 text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 dark:hover:text-indigo-300 hover:bg-indigo-50 dark:hover:bg-indigo-900/20"
                  variant="flat"
                  color="transparent"
                  size="sm"
                  onPress={() => setIsEditOpen(true)}
                  startContent={<Edit2 className="w-4 h-4" />}
                >
                  Edit
                </CustomButton>
              )}
            </div>
          </div>
        </div>
      </div>
    </>
  );
};

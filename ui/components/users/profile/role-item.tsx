"use client";

import { Chip } from "@nextui-org/react";
import { Ban, Check, ChevronDown, ChevronUp, Shield } from "lucide-react";
import { useState } from "react";

import { CustomButton } from "@/components/ui/custom/custom-button";
import { getRolePermissions } from "@/lib/permissions";
import { RoleData, RoleDetail } from "@/types/users";

interface PermissionItemProps {
  enabled: boolean;
  label: string;
}

export const PermissionIcon = ({ enabled }: { enabled: boolean }) => (
  <span
    className={`inline-flex h-5 w-5 items-center justify-center rounded-full ${enabled ? "bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300" : "bg-red-100 dark:bg-red-900 text-red-600 dark:text-red-300"}`}
  >
    {enabled ? <Check className="w-3 h-3" /> : <Ban className="w-3 h-3" />}
  </span>
);

const PermissionItem = ({ enabled, label }: PermissionItemProps) => (
  <div className="flex items-center gap-2 whitespace-nowrap">
    <PermissionIcon enabled={enabled} />
    <span className="text-sm font-medium text-gray-700 dark:text-gray-300">{label}</span>
  </div>
);

export const RoleItem = ({
  role,
  roleDetail,
}: {
  role: RoleData;
  roleDetail?: RoleDetail;
}) => {
  const [isExpanded, setIsExpanded] = useState(false);

  if (!roleDetail) {
    return (
      <Chip key={role.id} size="sm" variant="flat" color="primary">
        {role.id}
      </Chip>
    );
  }

  const { attributes } = roleDetail;
  const roleName = attributes?.name || role.id;
  const permissionState = attributes?.permission_state || "";
  const detailsId = `role-details-${role.id}`;

  const permissions = getRolePermissions(attributes);

  return (
    <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4 hover:shadow-md transition-all duration-200">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-indigo-100 dark:bg-indigo-900">
            <Shield className="w-4 h-4 text-indigo-600 dark:text-indigo-300" />
          </div>
          <div>
            <Chip
              size="sm"
              variant="flat"
              color="primary"
              className="bg-indigo-100 dark:bg-indigo-900 text-indigo-700 dark:text-indigo-200 font-semibold mb-1"
            >
              {roleName}
            </Chip>
            {permissionState && (
              <p className="text-xs text-gray-500 dark:text-gray-400 capitalize mt-1">
                {permissionState}
              </p>
            )}
          </div>
        </div>

        <CustomButton
          ariaLabel={isExpanded ? "Hide Details" : "Show Details"}
          onPress={() => setIsExpanded(!isExpanded)}
          className="text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 dark:hover:text-indigo-300"
          color="transparent"
          size="sm"
          endContent={isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        >
          {isExpanded ? "Hide" : "Details"}
        </CustomButton>
      </div>

      {isExpanded && (
        <div
          id={detailsId}
          className="animate-fadeIn mt-4 pt-4 border-t border-gray-200 dark:border-gray-700"
          role="region"
          aria-label={`Details for role ${roleName}`}
        >
          <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">Permissions</h4>
          <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
            {permissions.map(({ key, label, enabled }) => (
              <PermissionItem key={key} label={label} enabled={enabled} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

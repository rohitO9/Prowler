import { Card, CardBody, CardHeader } from "@nextui-org/react";
import { Shield } from "lucide-react";

import { RoleData, RoleDetail } from "@/types/users";

import { RoleItem } from "./role-item";

export const RolesCard = ({
  roles,
  roleDetails,
}: {
  roles: RoleData[];
  roleDetails: Record<string, RoleDetail>;
}) => {
  return (
    <Card className="shadow-xl border-0 bg-white dark:bg-gray-900">
      <CardHeader className="pb-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-indigo-100 dark:bg-indigo-900">
            <Shield className="w-5 h-5 text-indigo-600 dark:text-indigo-300" />
          </div>
          <div className="flex flex-col">
            <h4 className="text-xl font-bold text-gray-900 dark:text-white">Active Roles</h4>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Roles and permissions assigned to this user account
            </p>
          </div>
        </div>
      </CardHeader>
      <CardBody className="pt-6">
        {roles.length === 0 ? (
          <div className="text-center py-12 bg-gray-50 dark:bg-gray-800 rounded-xl border-2 border-dashed border-gray-300 dark:border-gray-700">
            <Shield className="w-12 h-12 text-gray-400 dark:text-gray-500 mx-auto mb-3" />
            <p className="text-sm font-medium text-gray-600 dark:text-gray-400">No roles assigned</p>
            <p className="text-xs text-gray-500 dark:text-gray-500 mt-1">This user doesn't have any roles yet</p>
          </div>
        ) : (
          <div className="space-y-3">
            {roles.map((role) => (
              <RoleItem
                key={role.id}
                role={role}
                roleDetail={roleDetails[role.id]}
              />
            ))}
          </div>
        )}
      </CardBody>
    </Card>
  );
};

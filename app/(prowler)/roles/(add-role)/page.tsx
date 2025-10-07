import { Suspense } from "react";

import { WorkflowAddEditRole } from "@/components/roles/workflow/workflow-add-edit-role";
import { SkeletonRoleForm } from "@/components/roles/workflow";

export default function RoleManagementPage() {
  return (
    <div className="container mx-auto px-4 py-8">
      <Suspense fallback={<SkeletonRoleForm />}>
        <WorkflowAddEditRole />
      </Suspense>
    </div>
  );
} 
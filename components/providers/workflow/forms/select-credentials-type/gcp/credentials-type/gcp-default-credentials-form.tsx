import { Control } from "react-hook-form";

import { CustomInput } from "@/components/ui/custom";
import { GCPDefaultCredentials } from "@/types";

export const GCPDefaultCredentialsForm = ({
  control,
}: {
  control: Control<GCPDefaultCredentials>;
}) => {
  return (
    <>
      <div className="flex flex-col">
        <div className="text-md font-bold leading-9 text-default-foreground 
         bg-gradient-to-r from-indigo-500 to-purple-500 bg-clip-text text-transparent">
          Connect via Credentials
        </div>
        <div className="text-sm text-default-500">
          Please provide the information for your GCP credentials.
        </div>
      </div>
      <label className="text-sm font-medium text-default-700 mb-1" htmlFor="client_id">Client ID *</label>
      <CustomInput
        control={control}
        name="client_id"
        type="text"
        label=""
        labelPlacement="outside"
        placeholder="Enter the Client ID"
        variant="bordered"
        isRequired
        isInvalid={!!control._formState.errors.client_id}
      />
      <label className="text-sm font-medium text-default-700 mb-1" htmlFor="client_secret">Client Secret *</label>
      <CustomInput
        control={control}
        name="client_secret"
        type="password"
        label=""
        labelPlacement="outside"
        placeholder="Enter the Client Secret"
        variant="bordered"
        isRequired
        isInvalid={!!control._formState.errors.client_secret}
      />
      <label className="text-sm font-medium text-default-700 mb-1" htmlFor="refresh_token">Refresh Token *</label>
      <CustomInput
        control={control}
        name="refresh_token"
        type="password"
        label=""
        labelPlacement="outside"
        placeholder="Enter the Refresh Token"
        variant="bordered"
        isRequired
        isInvalid={!!control._formState.errors.refresh_token}
      />
    </>
  );
};

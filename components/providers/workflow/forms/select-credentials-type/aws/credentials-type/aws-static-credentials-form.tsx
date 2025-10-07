import { Control } from "react-hook-form";

import { CustomInput } from "@/components/ui/custom";
import { AWSCredentials } from "@/types";

export const AWSStaticCredentialsForm = ({
  control,
}: {
  control: Control<AWSCredentials>;
}) => {
  return (
    <>
      <div className="flex flex-col">
        <div className="text-md font-bold leading-9 bg-gradient-to-r from-indigo-500 to-purple-500 bg-clip-text text-transparent">
          Connect via Credentials
        </div>
        <div className="text-sm text-default-500">
          Please provide the information for your AWS credentials.
        </div>
      </div>
      <label className="text-sm font-medium text-default-700 mb-1" htmlFor="aws_access_key_id">AWS Access Key ID *</label>
      <CustomInput
        control={control}
        name="aws_access_key_id"
        type="password"
        label=""
        labelPlacement="outside"
        placeholder="Enter the AWS Access Key ID"
        variant="bordered"
        isRequired
        isInvalid={!!control._formState.errors.aws_access_key_id}
      />
      <label className="text-sm font-medium text-default-700 mb-1" htmlFor="aws_secret_access_key">AWS Secret Access Key *</label>
      <CustomInput
        control={control}
        name="aws_secret_access_key"
        type="password"
        label=""
        labelPlacement="outside"
        placeholder="Enter the AWS Secret Access Key"
        variant="bordered"
        isRequired
        isInvalid={!!control._formState.errors.aws_secret_access_key}
      />
      <label className="text-sm font-medium text-default-700 mb-1" htmlFor="aws_session_token">AWS Session Token</label>
      <CustomInput
        control={control}
        name="aws_session_token"
        type="password"
        label=""
        labelPlacement="outside"
        placeholder="Enter the AWS Session Token"
        variant="bordered"
        isRequired={false}
        isInvalid={!!control._formState.errors.aws_session_token}
      />
    </>
  );
};

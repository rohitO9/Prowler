import { Radio, RadioGroup } from "@nextui-org/react";
import { Control, UseFormSetValue, useWatch } from "react-hook-form";

import { CredentialsRoleHelper } from "@/components/providers/workflow";
import { CustomInput } from "@/components/ui/custom";
import { AWSCredentialsRole } from "@/types";

export const AWSRoleCredentialsForm = ({
  control,
  setValue,
  externalId,
}: {
  control: Control<AWSCredentialsRole>;
  setValue: UseFormSetValue<AWSCredentialsRole>;
  externalId: string;
}) => {
  const credentialsType = useWatch({
    control,
    name: "credentials_type" as const,
    defaultValue: "access-secret-key",
  });

  return (
    <div className="w-full">
      <div className="flex flex-col items-center text-center mb-6">
        <div className="text-2xl font-bold leading-9 mb-1 bg-gradient-to-r from-indigo-500 to-purple-500 bg-clip-text text-transparent">
          Connect assuming IAM Role
        </div>
        <div className="text-base text-default-500 mb-2">
          Please provide the information for your AWS credentials.
        </div>
      </div>
      <div className="flex flex-col md:flex-row w-full bg-prowler-blue-50 dark:bg-prowler-blue-900 rounded-xl p-0 items-start">
        {/* Left Column */}
        <div className="md:w-1/2 w-full p-8 flex flex-col gap-6 border-r border-default-200">
          <label className="text-xs font-bold text-default-500 uppercase tracking-wide mb-1">Authentication Method</label>
          <RadioGroup
            orientation="vertical"
            value={credentialsType}
            onValueChange={(val) => setValue("credentials_type", val as "aws-sdk-default" | "access-secret-key")}
            className="mb-4"
          >
            <Radio value="aws-sdk-default" description="Recommended for most users.">
              AWS SDK default
            </Radio>
            <Radio value="access-secret-key" description="Use only if you have direct credentials.">
              Access & secret key
            </Radio>
          </RadioGroup>
          {credentialsType === "access-secret-key" && (
            <>
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
              <label className="text-sm font-medium text-default-700 mb-1" htmlFor="aws_session_token">AWS Session Token (optional)</label>
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
          )}
        </div>
        {/* Right Column */}
        <div className="md:w-1/2 w-full p-8 flex flex-col gap-4 justify-start">
          {/* Add heading to right section */}
        
          <span className="text-xs font-bold text-default-500 uppercase tracking-wide">Assume Role</span>
          <CredentialsRoleHelper />
          {/* Remove labels for Role ARN and External ID, use placeholders and add * in input */}
          <CustomInput
            control={control}
            name="role_arn"
            type="text"
            label=""
            labelPlacement="outside"
            placeholder="Role ARN *"
            variant="bordered"
            isRequired
            isInvalid={!!control._formState.errors.role_arn}
          />
          <CustomInput
            control={control}
            name="external_id"
            type="text"
            label=""
            labelPlacement="outside"
            placeholder={`External ID *${externalId ? ` (${externalId})` : ''}`}
            variant="bordered"
            defaultValue={externalId}
            isDisabled
            isRequired
            isInvalid={!!control._formState.errors.external_id}
          />
          <span className="text-xs text-default-500 mt-4">Optional fields</span>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <label className="text-sm font-medium text-default-700 mt-2" htmlFor="role_session_name">Role Session Name</label>
            <CustomInput
              control={control}
              name="role_session_name"
              type="text"
              label=""
              labelPlacement="outside"
              placeholder="Enter the Role Session Name"
              variant="bordered"
              isRequired={false}
              isInvalid={!!control._formState.errors.role_session_name}
            />
            <label className="text-sm font-medium text-default-700 mt-2" htmlFor="session_duration">Session Duration (seconds)</label>
            <CustomInput
              control={control}
              name="session_duration"
              type="number"
              label=""
              labelPlacement="outside"
              placeholder="Enter the session duration (default: 3600)"
              variant="bordered"
              isRequired={false}
              isInvalid={!!control._formState.errors.session_duration}
            />
          </div>
        </div>
      </div>
    </div>
  );
};

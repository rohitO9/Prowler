import Link from "next/link";
import { FaAws, FaGoogle, FaWindows, FaMicrosoft } from "react-icons/fa";
import { SiKubernetes } from "react-icons/si";

import { getProviderName } from "@/components/ui/entities/get-provider-logo";
import { getProviderLogo } from "@/components/ui/entities/get-provider-logo";
import { getProviderHelpText } from "@/lib";
import { ProviderType } from "@/types";

export const ProviderTitleDocs = ({
  providerType,
}: {
  providerType: ProviderType;
}) => {
  return (
    <div className="flex flex-col gap-y-2">
      <div className="flex space-x-4">
        <span className="mr-2">
          {providerType === "aws" && <FaAws size={28} color="#FF9900" />}
          {providerType === "gcp" && <FaGoogle size={28} color="#4285F4" />}
          {providerType === "azure" && <FaWindows size={28} color="#0078D4" />}
          {providerType === "m365" && <FaMicrosoft size={28} color="#F25022" />}
          {providerType === "kubernetes" && <SiKubernetes size={28} color="#326CE5" />}
        </span>
        <span className="text-lg font-semibold">
          {providerType
            ? getProviderName(providerType as ProviderType)
            : "Unknown Provider"}
        </span>
      </div>
      <div className="flex items-end gap-x-2">
        <p className="text-sm text-default-500">
          {getProviderHelpText(providerType as string).text}
        </p>
        <Link
          href={getProviderHelpText(providerType as string).link}
          target="_blank"
          className="text-sm font-medium text-[#4F46E5]"
        >
          Read the docs
        </Link>
      </div>
    </div>
  );
};

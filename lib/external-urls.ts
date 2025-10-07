export const getProviderHelpText = (provider: string) => {
  switch (provider) {
    case "aws":
      return {
        text: "Need help connecting your AWS account?",
        link: "#",
      };
    case "azure":
      return {
        text: "Need help connecting your Azure subscription?",
        link: "#",
      };
    case "m365":
      return {
        text: "Need help connecting your Microsoft 365 account?",
        link: "#",
      };
    case "gcp":
      return {
        text: "Need help connecting your GCP project?",
        link: "#",
      };
    case "kubernetes":
      return {
        text: "Need help connecting your Kubernetes cluster?",
        link: "#",
      };
    default:
      return {
        text: "How to setup a provider?",
        link: "#",
      };
  }
};

export const getAWSCredentialsTemplateLinks = () => {
  return {
    cloudformation:
      "#",
    cloudformationQuickLink:
      "#",
    terraform:
      "#",
  };
};

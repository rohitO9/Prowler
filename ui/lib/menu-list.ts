"use client";

import {
  ActivitySquare,
  BookOpen,
  Cloud,
  Users2,
  Layout,
  MailOpen,
  Sliders,
  Shield,
  BarChart2,
  Edit2,
  Tag,
  TimerReset,
  User2,
  UsersRound,
  HelpCircle,
  FileText,
  BookCopy,
  LifeBuoy,
  Settings,
} from "lucide-react";

import {
  APIdocIcon,
  AWSIcon,
  AzureIcon,
  CircleHelpIcon,
  DocIcon,
  GCPIcon,
  KubernetesIcon,
  M365Icon,
  SupportIcon,
} from "@/components/icons/Icons";
import { GroupProps } from "@/types";

export const getMenuList = (pathname: string): GroupProps[] => {
  return [
    {
      groupLabel: "",
      menus: [
        {
          href: "", // Parent menu does not navigate
          label: "Dashboard",
          icon: Layout,
          submenus: [
            {
              href: "/overview",
              label: "Overview",
              icon: BarChart2,
              active: pathname === "/overview",
            },
            {
              href: "/compliance",
              label: "Compliance Reports",
              icon: Shield,
              active: pathname === "/compliance",
            },
          ],
          defaultOpen: true,
        },
      ],
    },

    {
      groupLabel: "Findings",
      menus: [
        {
          href: "",
          label: "Failed Checks",
          icon: BookCopy,
          submenus: [
            {
              href: "/findings?filter[status__in]=FAIL&sort=severity,-inserted_at",
              label: "Misconfigurations",
              icon: ActivitySquare,
            },
            {
              href: "/findings?filter[status__in]=FAIL&filter[severity__in]=critical%2Chigh%2Cmedium&filter[provider_type__in]=aws%2Cazure%2Cgcp%2Ckubernetes&filter[service__in]=iam%2Crbac&sort=-inserted_at",
              label: "IAM Issues",
              icon: Shield,
            },
          ],
        },
        {
          href: "",
          label: "Critical Risks",
          icon: Edit2,
          submenus: [
            {
              href: "/findings?filter[status__in]=FAIL&filter[severity__in]=critical%2Chigh%2Cmedium&filter[provider_type__in]=aws&sort=severity,-inserted_at",
              label: "Amazon Web Services",
              icon: Cloud,
            },
            {
              href: "/findings?filter[status__in]=FAIL&filter[severity__in]=critical%2Chigh%2Cmedium&filter[provider_type__in]=azure&sort=severity,-inserted_at",
              label: "Microsoft Azure",
              icon: Cloud,
            },
            {
              href: "/findings?filter[status__in]=FAIL&filter[severity__in]=critical%2Chigh%2Cmedium&filter[provider_type__in]=m365&sort=severity,-inserted_at",
              label: "Microsoft 365",
              icon: Users2,
            },
            {
              href: "/findings?filter[status__in]=FAIL&filter[severity__in]=critical%2Chigh%2Cmedium&filter[provider_type__in]=gcp&sort=severity,-inserted_at",
              label: "Google Cloud",
              icon: Cloud,
            },
            {
              href: "/findings?filter[status__in]=FAIL&filter[severity__in]=critical%2Chigh%2Cmedium&filter[provider_type__in]=kubernetes&sort=severity,-inserted_at",
              label: "Kubernetes",
              icon: Cloud,
            },
          ],
        },
        {
          href: "/findings",
          label: "All Findings",
          icon: Tag,
        },
      ],
    },

    {
      groupLabel: "Settings",
      menus: [
        {
          href: "",
          label: "Configuration",
          icon: Sliders,
          submenus: [
            { href: "/providers", label: "Cloud Providers", icon: Cloud },
            { href: "/manage-groups", label: "Provider Groups", icon: UsersRound },
            { href: "/scans", label: "Scan Jobs", icon: TimerReset },
            { href: "/roles", label: "Roles", icon: Settings },
          ],
        },
      ],
    },

    {
      groupLabel: "User Management",
      menus: [
        {
          href: "",
          label: "Access Control",
          icon: Users2,
          submenus: [
            { href: "/users", label: "Users", icon: User2 },
            { href: "/invitations", label: "Invitations", icon: MailOpen },
          ],
        },
      ],
    },

    {
      groupLabel: "",
      menus: [
        {
          href: "",
          label: "Support",
          icon: LifeBuoy,
          submenus: [
            {
              href: "https://docs.prowler.com/",
              target: "_blank",
              label: "Documentation",
              icon: BookOpen,
            },
            {
              href:
                process.env.NEXT_PUBLIC_IS_CLOUD_ENV === "true"
                  ? "https://api.prowler.com/api/v1/docs"
                  : `${process.env.NEXT_PUBLIC_API_DOCS_URL}`,
              target: "_blank",
              label: "API Reference",
              icon: FileText,
            },
            {
              href: "https://github.com/prowler-cloud/prowler/issues",
              target: "_blank",
              label: "Support Portal",
              icon: HelpCircle,
            },
          ],
        },
      ],
    },
  ];
};

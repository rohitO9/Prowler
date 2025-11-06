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
  KeyRound,
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

export const getMenuList = (pathname: string): Omit<GroupProps, 'groupLabel'>[] => {
  return [
    {
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
          
        },
      ],
    },

    {
      menus: [
        {
          href: "",
          label: "Security Assessment",
          icon: Shield,
          submenus: [
            {
              href: "/findings",
              label: "All Findings",
              icon: Tag,
            },
            {
              href: "/findings?filter[status__in]=FAIL&sort=severity,-inserted_at",
              label: "Failed Findings",
              icon: ActivitySquare,
            },
          
            {
              href: "/findings?filter[severity__in]=critical&filter[provider_type__in]=aws%2Cgcp%2Ckubernetes&sort=severity,-inserted_at",
              label: "Critical Findings",
              icon: Cloud,
            },
            {
              href: "/findings?filter[severity__in]=high&filter[provider_type__in]=aws%2Cgcp%2Ckubernetes&sort=severity,-inserted_at",
              label: "High Findings",
              icon: Tag,
            },
            {
              href: "/findings?filter[severity__in]=low&filter[provider_type__in]=aws%2Cgcp%2Ckubernetes&sort=severity,-inserted_at",
              label: "Low Findings",
              icon: BookOpen,
            },
              {
              href: "/findings?filter[status__in]=FAIL&filter[severity__in]=critical%2Chigh%2Cmedium&filter[provider_type__in]=aws%2Cazure%2Cgcp%2Ckubernetes&filter[service__in]=iam%2Crbac&sort=-inserted_at",
              label: "IAM Issues",
              icon: Shield,
            },
            
          ],
        },
        
        
      ],
    },
    {
      menus: [
        {
          href: "",
          label: "Settings",
          icon: Settings,
          submenus: [
            { href: "/providers", label: "Cloud Providers", icon: Cloud },
            { href: "/manage-groups", label: "Provider Groups", icon: UsersRound },
            { href: "/azure-ad-config", label: "Azure AD Configuration", icon: KeyRound },
            { href: "/roles", label: "Roles", icon: Settings },
          ],
        },
      ],
    },

    {
      menus: [
        {
          href: "",
          label: "User Management",
          icon: Users2,
          submenus: [
            { href: "/users", label: "Users", icon: User2 },
            { href: "/invitations", label: "Invitations", icon: MailOpen },
          ],
        },
      ],
    },

    {
      menus: [
        {
          href: "",
          label: "Support",
          icon: HelpCircle,
          submenus: [
            { href: "#", label: "Documentation", icon: BookOpen },
            { href: "#", label: "Help", icon: HelpCircle },
          ],
        },
      ],
    },
  ];
};
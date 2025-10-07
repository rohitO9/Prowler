import { Button, CircularProgress } from "@nextui-org/react";
import type { PressEvent } from "@react-types/shared";
import clsx from "clsx";
import Link from "next/link";
import React from "react";

import { NextUIColors, NextUIVariants } from "@/types";

export const buttonClasses = {
  base: "px-4 inline-flex items-center justify-center relative z-0 text-center whitespace-nowrap",
  primary:
    "bg-gradient-to-r from-indigo-600 to-blue-600 hover:from-indigo-700 hover:to-blue-700 text-white",
  secondary: "bg-prowler-grey-light dark:bg-prowler-grey-medium text-white",
  action: "bg-gradient-to-r from-indigo-600 to-blue-600 hover:from-indigo-700 hover:to-blue-700 text-white",
  dashed:
    "border border-default border-dashed bg-transparent  justify-center whitespace-nowrap font-medium shadow-sm hover:border-solid hover:bg-default-100 active:bg-default-200 active:border-solid",
  transparent: "border-0 border-transparent bg-transparent",
  disabled: "pointer-events-none opacity-40",
  hover: "hover:shadow-md",
};

interface CustomButtonProps {
  type?: "button" | "submit" | "reset";
  target?: "_self" | "_blank";
  ariaLabel: string;
  ariaDisabled?: boolean;
  className?: string;
  variant?:
    | "solid"
    | "faded"
    | "bordered"
    | "light"
    | "flat"
    | "ghost"
    | "dashed"
    | "shadow";
  color?:
    | "primary"
    | "secondary"
    | "action"
    | "success"
    | "warning"
    | "danger"
    | "transparent";
  onPress?: (e: PressEvent) => void;
  children?: React.ReactNode;
  startContent?: React.ReactNode;
  endContent?: React.ReactNode;
  size?: "sm" | "md" | "lg";
  radius?: "none" | "sm" | "md" | "lg" | "full";
  dashed?: boolean;
  isDisabled?: boolean;
  isLoading?: boolean;
  isIconOnly?: boolean;
  ref?: React.RefObject<HTMLButtonElement>;
  asLink?: string;
  style?: React.CSSProperties;
}

export const CustomButton = React.forwardRef<
  HTMLButtonElement,
  CustomButtonProps
>(
  (
    {
      type = "button",
      target = "_self",
      ariaLabel,
      ariaDisabled,
      className,
      variant = "solid",
      color = "primary",
      onPress,
      children,
      startContent,
      endContent,
      size = "md",
      radius = "sm",
      isDisabled = false,
      isLoading = false,
      isIconOnly,
      asLink,
      style,
      ...props
    },
    ref,
  ) => (
    <Button
      as={asLink ? Link : undefined}
      href={asLink}
      target={target}
      type={type}
      aria-label={ariaLabel}
      aria-disabled={ariaDisabled}
      onPress={onPress}
      variant={variant as NextUIVariants}
      color={color as NextUIColors}
      className={clsx(
        buttonClasses.base,
        {
          [buttonClasses.primary]: color === "primary",
          [buttonClasses.secondary]: color === "secondary",
          [buttonClasses.action]: color === "action",
          [buttonClasses.dashed]: variant === "dashed",
          [buttonClasses.transparent]: color === "transparent",
          [buttonClasses.disabled]: isDisabled,
          [buttonClasses.hover]: color !== "transparent" && !isDisabled,
        },
        className,
      )}
      style={style}
      startContent={startContent}
      endContent={endContent}
      size={size}
      radius={radius}
      spinner={
        <CircularProgress
          classNames={{
            svg: "w-6 h-6 drop-shadow-md",
            indicator: "stroke-white",
            track: "stroke-white/10",
          }}
          aria-label="Loading..."
        />
      }
      ref={ref}
      isDisabled={isDisabled}
      isLoading={isLoading}
      isIconOnly={isIconOnly}
      {...props}
    >
      {children}
    </Button>
  ),
);

CustomButton.displayName = "CustomButton";

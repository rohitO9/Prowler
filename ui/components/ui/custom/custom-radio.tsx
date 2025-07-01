import { cn, useRadio, VisuallyHidden } from "@nextui-org/react";
import React from "react";

interface CustomRadioProps {
  description?: string;
  value?: string;
  children?: React.ReactNode;
  className?: string;
}

export const CustomRadio: React.FC<CustomRadioProps> = (props) => {
  const {
    Component,
    children,
    // description,
    getBaseProps,
    getWrapperProps,
    getInputProps,
    getLabelProps,
    getLabelWrapperProps,
    getControlProps,
  } = useRadio({ ...props, value: props.value || "" });

  return (
    <Component
      {...getBaseProps()}
      className={cn(
        "group inline-flex flex-row-reverse items-center justify-between tap-highlight-transparent hover:opacity-70 active:opacity-50",
        "max-w-full cursor-pointer gap-4 rounded-lg border-2 border-default p-4",
        "w-full hover:border-[#4d43a8] data-[selected=true]:border-[#4039bd] focus-visible:ring-2 focus-visible:ring-[#4F46E5]",
        props.className
      )}
    >
      <VisuallyHidden>
        <input {...getInputProps()} />
      </VisuallyHidden>
      <span {...getWrapperProps()} className="hidden">
        <span {...getControlProps()} />
      </span>
      <div {...getLabelWrapperProps()}>
        {children && <span {...getLabelProps()}>{children}</span>}
        {/* {description && (
            <span className="text-small text-foreground opacity-70">
              {description}
            </span>
          )} */}
      </div>
    </Component>
  );
};

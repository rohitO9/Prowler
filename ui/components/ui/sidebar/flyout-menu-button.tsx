import React, { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { createPortal } from "react-dom";

interface SubmenuItem {
  href: string;
  label: string;
  icon: React.ElementType;
  active?: boolean;
}

interface FlyoutMenuButtonProps {
  icon: React.ElementType;
  label: string;
  submenus: SubmenuItem[];
  isOpen: boolean;
  defaultOpen?: boolean;
}

export const FlyoutMenuButton: React.FC<FlyoutMenuButtonProps> = ({
  icon: Icon,
  label,
  submenus,
  isOpen,
  defaultOpen = false,
}) => {
  const [open, setOpen] = useState(defaultOpen);
  const [isClient, setIsClient] = useState(false);
  const buttonRef = useRef<HTMLDivElement>(null);
  const [flyoutPos, setFlyoutPos] = useState({ top: 0, left: 0 });
  const closeTimeout = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    setIsClient(true);
  }, []);

  const handleMouseEnter = () => {
    if (closeTimeout.current) {
      clearTimeout(closeTimeout.current);
    }
    if (buttonRef.current) {
      const rect = buttonRef.current.getBoundingClientRect();
      setFlyoutPos({ top: rect.top, left: rect.right });
    }
    setOpen(true);
  };

  const handleMouseLeave = () => {
    closeTimeout.current = setTimeout(() => {
      setOpen(false);
    }, 160); //
  };

  const handleFlyoutEnter = () => {
    if (closeTimeout.current) {
      clearTimeout(closeTimeout.current);
    }
    setOpen(true);
  };

  const handleFlyoutLeave = () => {
    closeTimeout.current = setTimeout(() => {
      setOpen(false);
    }, 100
);
  };

  return (
    <div
      className="relative w-full"
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      ref={buttonRef}
    >
      <button
        className={cn(
          "flex items-center w-full px-2 py-2 rounded-md transition-colors",
          open ? "bg-gray-200 dark:bg-gray-800" : "hover:bg-gray-100 dark:hover:bg-gray-800"
        )}
        tabIndex={0}
        aria-haspopup="true"
        aria-expanded={open}
      >
        <Icon size={18} className="mr-3" />
        {isOpen && <span className="truncate">{label}</span>}
        <span className="ml-auto">&gt;</span>
      </button>
      {isClient && open && createPortal(
        <div
          className="z-50 min-w-[180px] bg-gray-100 dark:bg-gray-900 shadow-lg rounded-md py-2 border border-gray-200 dark:border-gray-700 animate-fade-in"
          style={{
            position: "fixed",
            top: flyoutPos.top,
            left: flyoutPos.left + 8, // 8px margin
          }}
          role="menu"
          onMouseEnter={handleFlyoutEnter}
          onMouseLeave={handleFlyoutLeave}
        >
          {submenus.map((submenu, idx) => (
            <Link
              href={submenu.href}
              key={idx}
              className={cn(
                "flex items-center px-4 py-2 text-sm text-gray-700 dark:text-gray-200 transition-colors",
                submenu.active ? "font-semibold bg-gray-200 dark:bg-gray-800" : "",
                "hover:bg-gray-200 hover:font-semibold dark:hover:bg-gray-800"
              )}
              role="menuitem"
            >
              <submenu.icon size={16} className="mr-2" />
              <span>{submenu.label}</span>
            </Link>
          ))}
        </div>,
        document.body
      )}
    </div>
  );
}; 
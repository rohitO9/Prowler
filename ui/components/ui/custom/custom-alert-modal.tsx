import { Modal, ModalBody, ModalContent, ModalHeader } from "@nextui-org/react";
import React, { ReactNode } from "react";

interface CustomAlertModalProps {
  isOpen: boolean;
  onOpenChange: (isOpen: boolean) => void;
  title?: React.ReactNode;
  description?: React.ReactNode;
  children: ReactNode;
}

export const CustomAlertModal: React.FC<CustomAlertModalProps> = ({
  isOpen,
  onOpenChange,
  title,
  description,
  children,
}) => {
  return (
    <Modal
      isOpen={isOpen}
      onOpenChange={onOpenChange}
      size="5xl"
      classNames={{
        base: "dark:bg-prowler-blue-800 max-w-[90vw] w-full",
        closeButton: "rounded-md",
      }}
      backdrop="blur"
      placement="center"
    >
      <ModalContent
        className="mx-6 max-w-[90vw] w-full max-h-[90vh] overflow-hidden rounded-2xl shadow-2xl bg-white dark:bg-prowler-blue-800 pt-2 pb-4"
      >
        {(_onClose) => (
          <>
            <div className="sticky top-0 z-10 bg-white dark:bg-prowler-blue-800">
              <button
                onClick={() => onOpenChange(false)}
                className="absolute top-3 right-4 text-2xl text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
                aria-label="Close"
                type="button"
              >
                &times;
              </button>
              <ModalHeader className="flex flex-col py-0">{title}</ModalHeader>
              <div className="px-2">
                <p className="text-small text-gray-600 dark:text-gray-300">{description}</p>
              </div>
              <div className="border-b border-gray-200 dark:border-gray-700 my-2" />
            </div>
            <ModalBody className="overflow-y-auto max-h-[calc(90vh-64px)]">
              {children}
            </ModalBody>
          </>
        )}
      </ModalContent>
    </Modal>
  );
};

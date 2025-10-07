"use client";

import { Card, CardBody } from "@nextui-org/react";
import React from "react";

import { InfoIcon } from "../icons/Icons";
import { CustomButton } from "../ui/custom";

export const NoProvidersAdded = () => {
  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-100 dark:bg-gray-900">
      <div className="mx-auto w-full max-w-2xl px-4">
        <Card className="mx-auto w-full max-w-xl rounded-md border border-gray-200 bg-white shadow-md dark:border-gray-700 dark:bg-gray-800">
          <CardBody className="flex flex-col items-center space-y-6 p-8 text-center">
            <div className="flex flex-col items-center space-y-2">
              <InfoIcon className="h-8 w-8 text-blue-600 dark:text-blue-400" />
              <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
                Cloud Provider Setup Required
              </h2>
            </div>
            <p className="text-base text-gray-700 dark:text-gray-300">
              To begin, please connect your first cloud provider.<br />
              No providers are currently linked to your account.
            </p>
            <CustomButton
              asLink="/providers/connect-account"
              ariaLabel="Go to Add Cloud Provider page"
              className="w-full max-w-xs justify-center rounded-xl"
              variant="solid"
              color="action"
              size="lg"
            >
              Set Up Cloud Provider
            </CustomButton>
          </CardBody>
        </Card>
      </div>
    </div>
  );
};

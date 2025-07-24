import { ContentLayout } from "@/components/ui";
import Image from "next/image";
import { Button } from "@/components/ui/button/button";
import React from "react";

export default function Welcome() {
  return (
    <ContentLayout title="Welcome" icon="solar:pie-chart-2-outline">
      <div className="relative h-full py-16 mt-2 flex justify-center items-center overflow-hidden bg-gradient-to-br from-[#f5f7fa] to-[#e4ecf4] dark:from-[#0a0f2c] dark:to-[#050a1f] transition-colors duration-300">
        {/* Background Image (light/dark opacity adjusted) */}
        <Image
          src="/saas-concept-collage.png"
          alt="Cloud Security Background"
          layout="fill"
          objectFit="cover"
          className="absolute inset-0 opacity-10 dark:opacity-20 blur-sm pointer-events-none z-0 transition-opacity duration-300"
        />

        {/* Main Card Content */}
        <div className="relative z-10 bg-white/80 dark:bg-gray-900/90 backdrop-blur-xl border border-gray-200 dark:border-gray-800 rounded-2xl shadow-2xl w-full max-w-4xl p-10 flex flex-col md:flex-row items-center">
          {/* Left Text Section */}
          <div className="md:w-1/2 w-full px-6 py-6 space-y-6">
            <h1 className="text-4xl font-bold text-gray-900 dark:text-white">
              Welcome to <span className="text-blue-600 dark:text-blue-400">SecureStack</span>
            </h1>
            <p className="text-lg text-gray-700 dark:text-gray-300">
              Your unified cloud security and compliance platform.
            </p>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Get started by generating your first security report or explore the platform using the sidebar.
            </p>
            <Button size="lg" className="bg-gradient-to-r from-indigo-600 to-blue-600 hover:from-indigo-700 hover:to-blue-700 text-white text-lg font-semibold">
              Generate Report
            </Button>
          </div>

          {/* Right Image Section */}
          <div className="md:w-1/2 w-full flex justify-center items-center p-4">
            <Image
              src="/saas-concept-collage.png"
              alt="Cloud Security Collage"
              width={420}
              height={420}
              className="rounded-xl shadow-xl object-contain"
              priority
            />
          </div>
        </div>
      </div>
    </ContentLayout>
  );
}

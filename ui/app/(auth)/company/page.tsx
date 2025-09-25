"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";

type CompanyForm = {
  company: string;
};

export default function CompanyPage() {
  const router = useRouter();
  const { register, handleSubmit, setValue } = useForm<CompanyForm>({
    defaultValues: { company: "" },
  });

  useEffect(() => {
    const saved = typeof window !== "undefined" ? localStorage.getItem("company") : null;
    if (saved) setValue("company", saved);
  }, [setValue]);

  const onSubmit = (data: CompanyForm) => {
    if (typeof window !== "undefined") {
      localStorage.setItem("company", data.company.trim());
    }
    router.push("/sign-in");
  };

  return (
    <div className="flex min-h-screen items-center justify-center p-6">
      <form onSubmit={handleSubmit(onSubmit)} className="w-full max-w-md space-y-4">
        <h1 className="text-2xl font-semibold">Select your Organization</h1>
        <input
          {...register("company")}
          placeholder="Organization name"
          className="w-full rounded border px-3 py-2"
          required
        />
        <button type="submit" className="w-full rounded bg-blue-600 px-3 py-2 text-white">Continue</button>
      </form>
    </div>
  );
}



"use client";
import { AuthForm } from "@/components/auth/oss";
import {
  getAuthUrl,
  isGithubOAuthEnabled,
  isGoogleOAuthEnabled,
  isAzureOAuthEnabled,
} from "@/lib/helper";
<<<<<<< Updated upstream
import { useEffect, useState } from "react";
import { apiBaseUrl } from "@/lib";
=======
import { useEffect } from "react";
import { getSubdomain } from "../../../src/utils/subdomain";
>>>>>>> Stashed changes

const SignIn = () => {
  const GOOGLE_AUTH_URL = getAuthUrl("google");
  const GITHUB_AUTH_URL = getAuthUrl("github");
  const AZURE_AUTH_URL = getAuthUrl("azure");

<<<<<<< Updated upstream
  const [step, setStep] = useState<number>(1);
  const [tenants, setTenants] = useState<Array<{ id: string; name: string }>>([]);
  const [selected, setSelected] = useState<string>("");

  useEffect(() => {
    const saved = typeof window !== "undefined" ? localStorage.getItem("company") : null;
    if (saved) setSelected(saved || "");
    (async () => {
      try {
        const res = await fetch(`${apiBaseUrl}/tenants/public`);
        const data = await res.json();
        setTenants(data.tenants || []);
      } catch (e) {
        // eslint-disable-next-line no-console
        console.error(e);
      }
    })();
  }, []);

  const onChoose = (e: React.FormEvent) => {
    e.preventDefault();
    const value = selected?.trim();
    if (!value) return;
    if (typeof window !== "undefined") localStorage.setItem("company", value);
    setStep(2);
  };

  const onGoToSignup = (e: React.MouseEvent) => {
    e.preventDefault();
    const value = selected?.trim();
    if (!value) return;
    if (typeof window !== "undefined") localStorage.setItem("company", value);
    window.location.href = "/sign-up";
  };

  if (step === 1) {
    return (
      <div className="flex min-h-screen items-center justify-center p-6">
        <form onSubmit={onChoose} className="w-full max-w-md space-y-4">
          <h1 className="text-2xl font-semibold">Select your Organization</h1>
          <input
            list="tenantOptions"
            value={selected}
            onChange={(e) => setSelected(e.target.value)}
            placeholder="Enter your organization"
            className="w-full rounded border px-3 py-2"
            required
          />
          <datalist id="tenantOptions">
            {tenants.map((t) => (
              <option key={t.id} value={t.name} />
            ))}
          </datalist>
          <div className="flex gap-3">
            <button type="submit" className="flex-1 rounded bg-blue-600 px-3 py-2 text-white">
              Continue to Sign In
            </button>
            <button onClick={onGoToSignup} className="flex-1 rounded border px-3 py-2">
              Continue to Sign Up
            </button>
          </div>
        </form>
      </div>
    );
  }

=======
  useEffect(() => {
    // Auto-detect organization from subdomain
    const subdomain = getSubdomain();
    if (subdomain && typeof window !== "undefined") {
      localStorage.setItem("company", subdomain);
    }
  }, []);

>>>>>>> Stashed changes
  return (
    <AuthForm
      type="sign-in"
      googleAuthUrl={GOOGLE_AUTH_URL}
      githubAuthUrl={GITHUB_AUTH_URL}
      isGoogleOAuthEnabled={isGoogleOAuthEnabled}
      isGithubOAuthEnabled={isGithubOAuthEnabled}
      azureAuthUrl={AZURE_AUTH_URL}
<<<<<<< Updated upstream
      // isAzureOAuthEnabled={isAzureOAuthEnabled}
=======
>>>>>>> Stashed changes
    />
  );
};

export default SignIn;

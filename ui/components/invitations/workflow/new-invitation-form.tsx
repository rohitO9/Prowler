"use client";

import { Button, Input, Select, SelectItem } from "@nextui-org/react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { createInvitation } from "@/lib/api/invitations";
import { useToast } from "@/components/ui/toast";
import { useTenant } from "@/hooks/use-tenant"; // Add this hook to get current tenant

export const NewInvitationForm = () => {
  const router = useRouter();
  const { toast } = useToast();
  const { currentTenant } = useTenant(); // Get current tenant
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    email: '',
    role: 'member',
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    if (!currentTenant?.id) {
      toast({
        title: "Error",
        description: "No tenant selected",
        variant: "destructive",
      });
      setLoading(false);
      return;
    }

    try {
      await createInvitation({
        data: {
          type: 'invitations',
          attributes: {
            email: formData.email,
            role: formData.role,
          },
          relationships: {
            tenant: {
              data: {
                type: 'tenants',
                id: currentTenant.id
              }
            }
          }
        }
      });

      toast({
        title: "Success",
        description: "Invitation sent successfully",
      });
      router.push('/invitations/check-details');
    } catch (error) {
      console.error('Invitation error:', error);
      toast({
        title: "Error",
        description: "Failed to send invitation",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <Input
        label="Email Address"
        type="email"
        value={formData.email}
        onChange={(e) => setFormData({ ...formData, email: e.target.value })}
        required
      />

      <Select
        label="Role"
        value={formData.role}
        onChange={(e) => setFormData({ ...formData, role: e.target.value })}
        required
      >
        <SelectItem key="member" value="member">Member</SelectItem>
        <SelectItem key="admin" value="admin">Admin</SelectItem>
      </Select>

      <Button
        type="submit"
        color="primary"
        isLoading={loading}
        disabled={!currentTenant?.id}
        className="w-full"
      >
        Send Invitation
      </Button>
    </form>
  );
};
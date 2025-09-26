export const apiBaseUrl = process.env.API_BASE_URL || "http://127.0.0.1:8080/api/v1";

interface InvitationAttributes {
  email: string;
  role: string;
}

interface InvitationRelationships {
  tenant: {
    data: {
      type: 'tenants';
      id: string;
    };
  };
}

interface InvitationRequest {
  data: {
    type: 'invitations';
    attributes: InvitationAttributes;
    relationships: InvitationRelationships;
  };
}

export const createInvitation = async (data: InvitationRequest): Promise<any> => {
    const response = await fetch(`${apiBaseUrl}/tenants/invitations`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/vnd.api+json',
            'Accept': 'application/vnd.api+json',
            'X-Tenant-ID': data.data.relationships.tenant.data.id,
            'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify(data)
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.errors?.[0]?.detail || 'Failed to create invitation');
    }

    return response.json();
};
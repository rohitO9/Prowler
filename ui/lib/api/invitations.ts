import { getAuthToken } from '../auth';

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

interface APIError {
    errors: Array<{
        detail: string;
        status: string;
        title?: string;
    }>;
}

export const createInvitation = async (data: InvitationRequest): Promise<any> => {
    // Validate tenant ID is present
    const tenantId = data.data.relationships.tenant.data.id;
    if (!tenantId) {
        throw new Error('Tenant ID is required');
    }

    const token = await getAuthToken();
    if (!token) {
        throw new Error('Authentication token is required');
    }

    try {
        const response = await fetch(`${apiBaseUrl}/tenants/invitations`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/vnd.api+json',
                'Accept': 'application/vnd.api+json',
                'X-Tenant-ID': tenantId,
                'Authorization': `Bearer ${token}`,
            },
            credentials: 'include', // Add this to include cookies
            body: JSON.stringify({
                data: {
                    type: 'invitations',
                    attributes: {
                        email: data.data.attributes.email,
                        role: data.data.attributes.role
                    },
                    relationships: {
                        tenant: {
                            data: {
                                type: 'tenants',
                                id: tenantId
                            }
                        }
                    }
                }
            })
        });

        if (!response.ok) {
            const errorData = await response.json() as APIError;
            console.error('API Error:', {
                status: response.status,
                headers: Object.fromEntries(response.headers.entries()),
                error: errorData
            });
            throw new Error(
                errorData.errors?.[0]?.detail || 
                `Failed to create invitation: ${response.status}`
            );
        }

        return response.json();
    } catch (error) {
        console.error('Invitation creation error:', {
            error,
            request: {
                tenantId,
                hasToken: !!token,
                url: `${apiBaseUrl}/tenants/invitations`
            }
        });
        throw error instanceof Error ? error : new Error('Failed to create invitation');
    }
};

// Helper function to validate invitation request
export const validateInvitationRequest = (data: InvitationRequest): string | null => {
    if (!data.data?.attributes?.email) {
        return 'Email is required';
    }
    if (!data.data?.attributes?.role) {
        return 'Role is required';
    }
    if (!data.data?.relationships?.tenant?.data?.id) {
        return 'Tenant ID is required';
    }
    return null;
};

// Add helper to get current tenant
export const getCurrentTenant = (): string | null => {
    try {
        const tenant = localStorage.getItem('currentTenant');
        return tenant ? JSON.parse(tenant).id : null;
    } catch {
        return null;
    }
};
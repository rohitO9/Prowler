/**
 * Comprehensive tenant security utilities for frontend applications.
 * Provides tenant-aware error handling, security validation, and context management.
 */

import { NextRequest, NextResponse } from 'next/server';
import { getToken } from 'next-auth/jwt';

export interface TenantContext {
  tenantId: string;
  tenantName: string;
  tenantSubdomain: string;
  userId: string;
  userEmail: string;
  userName: string;
  isSuperuser: boolean;
  isVerified: boolean;
  twoFactorEnabled: boolean;
  permissions: {
    role: string;
    canInviteUsers: boolean;
    canManageSettings: boolean;
    canViewAnalytics: boolean;
    isOwnerOrAdmin: boolean;
  };
  securityLevel: 'low' | 'medium' | 'high' | 'critical';
}

export interface SecurityError {
  code: string;
  message: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  tenantSpecific: boolean;
  requiresInvestigation: boolean;
}

export interface TenantSecurityConfig {
  enableStrictMode: boolean;
  maxRetryAttempts: number;
  sessionTimeoutMinutes: number;
  enableAuditLogging: boolean;
  enableRateLimiting: boolean;
  allowedDomains: string[];
}

/**
 * Tenant Security Manager for frontend applications.
 */
export class TenantSecurityManager {
  private config: TenantSecurityConfig;
  private retryCount: Map<string, number> = new Map();
  private lastActivity: Map<string, number> = new Map();

  constructor(config: Partial<TenantSecurityConfig> = {}) {
    this.config = {
      enableStrictMode: true,
      maxRetryAttempts: 3,
      sessionTimeoutMinutes: 480,
      enableAuditLogging: true,
      enableRateLimiting: true,
      allowedDomains: [],
      ...config
    };
  }

  /**
   * Extract tenant context from JWT token.
   */
  async getTenantContext(request: NextRequest): Promise<TenantContext | null> {
    try {
      const token = await getToken({ req: request });
      
      if (!token) {
        return null;
      }

      // Validate token structure
      if (!this.isValidTokenStructure(token)) {
        this.logSecurityViolation('Invalid token structure', 'high');
        return null;
      }

      // Extract tenant context
      const context: TenantContext = {
        tenantId: token.tenant_id as string,
        tenantName: token.tenant_name as string,
        tenantSubdomain: token.tenant_subdomain as string,
        userId: token.user_id as string,
        userEmail: token.email as string,
        userName: token.name as string,
        isSuperuser: token.is_superuser as boolean || false,
        isVerified: token.is_verified as boolean || false,
        twoFactorEnabled: token.two_factor_enabled as boolean || false,
        permissions: {
          role: token.role as string || 'member',
          canInviteUsers: token.can_invite_users as boolean || false,
          canManageSettings: token.can_manage_settings as boolean || false,
          canViewAnalytics: token.can_view_analytics as boolean || false,
          isOwnerOrAdmin: token.is_owner_or_admin as boolean || false
        },
        securityLevel: this.determineSecurityLevel(token)
      };

      // Validate tenant context
      if (!this.validateTenantContext(context)) {
        this.logSecurityViolation('Invalid tenant context', 'high');
        return null;
      }

      // Update activity tracking
      this.updateActivityTracking(context.userId);

      return context;

    } catch (error) {
      console.error('Error extracting tenant context:', error);
      this.logSecurityViolation('Token extraction error', 'medium');
      return null;
    }
  }

  /**
   * Validate tenant access for a specific resource.
   */
  validateTenantAccess(context: TenantContext, resourceTenantId: string): boolean {
    // Superusers can access any tenant
    if (context.isSuperuser) {
      return true;
    }

    // Check if resource belongs to user's tenant
    if (context.tenantId !== resourceTenantId) {
      this.logSecurityViolation(
        `Cross-tenant access attempt: ${context.tenantId} -> ${resourceTenantId}`,
        'critical'
      );
      return false;
    }

    return true;
  }

  /**
   * Check if user has required permission.
   */
  hasPermission(context: TenantContext, permission: string): boolean {
    const permissionMap: Record<string, boolean> = {
      'invite_users': context.permissions.canInviteUsers,
      'manage_settings': context.permissions.canManageSettings,
      'view_analytics': context.permissions.canViewAnalytics,
      'admin_access': context.permissions.isOwnerOrAdmin
    };

    return permissionMap[permission] || false;
  }

  /**
   * Validate request security and return appropriate response.
   */
  async validateRequestSecurity(
    request: NextRequest,
    requiredPermissions: string[] = [],
    requireTenantIsolation: boolean = true
  ): Promise<{ context: TenantContext; response?: NextResponse }> {
    try {
      // Get tenant context
      const context = await this.getTenantContext(request);
      
      if (!context) {
        return {
          context: null as any,
          response: this.createErrorResponse('Authentication required', 401)
        };
      }

      // Check session timeout
      if (this.isSessionExpired(context.userId)) {
        this.logSecurityViolation('Session expired', 'medium');
        return {
          context: null as any,
          response: this.createErrorResponse('Session expired', 401)
        };
      }

      // Check rate limiting
      if (this.config.enableRateLimiting && this.isRateLimited(context.userId)) {
        this.logSecurityViolation('Rate limit exceeded', 'medium');
        return {
          context: null as any,
          response: this.createErrorResponse('Rate limit exceeded', 429)
        };
      }

      // Check permissions
      for (const permission of requiredPermissions) {
        if (!this.hasPermission(context, permission)) {
          this.logSecurityViolation(`Permission denied: ${permission}`, 'high');
          return {
            context: null as any,
            response: this.createErrorResponse(`Permission denied: ${permission}`, 403)
          };
        }
      }

      // Validate tenant isolation if required
      if (requireTenantIsolation) {
        const resourceTenantId = this.extractResourceTenantId(request);
        if (resourceTenantId && !this.validateTenantAccess(context, resourceTenantId)) {
          this.logSecurityViolation('Tenant isolation violation', 'critical');
          return {
            context: null as any,
            response: this.createErrorResponse('Access denied', 403)
          };
        }
      }

      return { context };

    } catch (error) {
      console.error('Security validation error:', error);
      this.logSecurityViolation('Security validation error', 'high');
      return {
        context: null as any,
        response: this.createErrorResponse('Security validation failed', 500)
      };
    }
  }

  /**
   * Create tenant-specific error response.
   */
  createTenantErrorResponse(error: SecurityError, tenantContext?: TenantContext): NextResponse {
    const response = {
      error: error.code,
      message: error.message,
      severity: error.severity,
      tenantId: tenantContext?.tenantId,
      timestamp: new Date().toISOString(),
      ...(error.requiresInvestigation && { requiresInvestigation: true })
    };

    // Log security violation
    if (this.config.enableAuditLogging) {
      this.logSecurityViolation(error.message, error.severity);
    }

    // Determine HTTP status based on severity
    let status = 400;
    switch (error.severity) {
      case 'critical':
        status = 403;
        break;
      case 'high':
        status = 401;
        break;
      case 'medium':
        status = 400;
        break;
      case 'low':
        status = 200;
        break;
    }

    return NextResponse.json(response, { status });
  }

  /**
   * Handle tenant-specific errors with appropriate messaging.
   */
  handleTenantError(error: any, tenantContext?: TenantContext): SecurityError {
    // Determine error type and create appropriate response
    if (error.code === 'TENANT_ACCESS_DENIED') {
      return {
        code: 'TENANT_ACCESS_DENIED',
        message: tenantContext 
          ? `Access denied to tenant ${tenantContext.tenantName}`
          : 'Access denied to tenant',
        severity: 'critical',
        tenantSpecific: true,
        requiresInvestigation: true
      };
    }

    if (error.code === 'PERMISSION_DENIED') {
      return {
        code: 'PERMISSION_DENIED',
        message: 'Insufficient permissions for this action',
        severity: 'high',
        tenantSpecific: true,
        requiresInvestigation: false
      };
    }

    if (error.code === 'RATE_LIMIT_EXCEEDED') {
      return {
        code: 'RATE_LIMIT_EXCEEDED',
        message: 'Too many requests. Please try again later.',
        severity: 'medium',
        tenantSpecific: false,
        requiresInvestigation: false
      };
    }

    if (error.code === 'SESSION_EXPIRED') {
      return {
        code: 'SESSION_EXPIRED',
        message: 'Your session has expired. Please log in again.',
        severity: 'medium',
        tenantSpecific: false,
        requiresInvestigation: false
      };
    }

    // Default error
    return {
      code: 'UNKNOWN_ERROR',
      message: 'An unexpected error occurred',
      severity: 'medium',
      tenantSpecific: false,
      requiresInvestigation: true
    };
  }

  /**
   * Validate tenant subdomain from request.
   */
  validateTenantSubdomain(request: NextRequest): string | null {
    const host = request.headers.get('host') || '';
    
    // Handle localhost development
    if (host.includes('localhost') || host.includes('127.0.0.1')) {
      const parts = host.split('.');
      if (parts.length > 1) {
        return parts[0];
      }
    }
    
    // Handle production domains
    const parts = host.split('.');
    if (parts.length >= 3) {
      return parts[0];
    }
    
    return null;
  }

  /**
   * Get tenant-specific configuration.
   */
  async getTenantConfig(tenantId: string): Promise<Partial<TenantSecurityConfig>> {
    try {
      // This would typically fetch from your API
      const response = await fetch(`/api/tenants/${tenantId}/config`);
      if (!response.ok) {
        throw new Error('Failed to fetch tenant config');
      }
      
      return await response.json();
    } catch (error) {
      console.error('Error fetching tenant config:', error);
      return {};
    }
  }

  // Private helper methods

  private isValidTokenStructure(token: any): boolean {
    return !!(
      token &&
      token.tenant_id &&
      token.tenant_name &&
      token.user_id &&
      token.email
    );
  }

  private validateTenantContext(context: TenantContext): boolean {
    return !!(
      context.tenantId &&
      context.tenantName &&
      context.userId &&
      context.userEmail
    );
  }

  private determineSecurityLevel(token: any): 'low' | 'medium' | 'high' | 'critical' {
    if (token.is_superuser) {
      return 'critical';
    }
    
    if (token.is_verified && token.tenant_verified) {
      return 'high';
    }
    
    if (token.is_verified || token.tenant_verified) {
      return 'medium';
    }
    
    return 'low';
  }

  private updateActivityTracking(userId: string): void {
    this.lastActivity.set(userId, Date.now());
  }

  private isSessionExpired(userId: string): boolean {
    const lastActivity = this.lastActivity.get(userId);
    if (!lastActivity) {
      return false;
    }
    
    const sessionTimeout = this.config.sessionTimeoutMinutes * 60 * 1000;
    return Date.now() - lastActivity > sessionTimeout;
  }

  private isRateLimited(userId: string): boolean {
    const retryCount = this.retryCount.get(userId) || 0;
    return retryCount >= this.config.maxRetryAttempts;
  }

  private extractResourceTenantId(request: NextRequest): string | null {
    // Extract tenant ID from URL path or headers
    const pathname = request.nextUrl.pathname;
    const tenantMatch = pathname.match(/\/api\/tenants\/([^\/]+)/);
    
    if (tenantMatch) {
      return tenantMatch[1];
    }
    
    return request.headers.get('X-Tenant-ID');
  }

  private createErrorResponse(message: string, status: number): NextResponse {
    return NextResponse.json(
      { error: message, status },
      { status }
    );
  }

  private logSecurityViolation(message: string, severity: string): void {
    if (this.config.enableAuditLogging) {
      console.warn(`[SECURITY] ${severity.toUpperCase()}: ${message}`);
      
      // In a real application, you would send this to your logging service
      // Example: sendToLoggingService({ message, severity, timestamp: new Date() });
    }
  }
}

// Global instance
export const tenantSecurityManager = new TenantSecurityManager();

// Utility functions for easy use

/**
 * Extract tenant context from request.
 */
export async function getTenantContext(request: NextRequest): Promise<TenantContext | null> {
  return await tenantSecurityManager.getTenantContext(request);
}

/**
 * Validate tenant access for a resource.
 */
export function validateTenantAccess(context: TenantContext, resourceTenantId: string): boolean {
  return tenantSecurityManager.validateTenantAccess(context, resourceTenantId);
}

/**
 * Check if user has required permission.
 */
export function hasPermission(context: TenantContext, permission: string): boolean {
  return tenantSecurityManager.hasPermission(context, permission);
}

/**
 * Create tenant-specific error response.
 */
export function createTenantErrorResponse(error: SecurityError, tenantContext?: TenantContext): NextResponse {
  return tenantSecurityManager.createTenantErrorResponse(error, tenantContext);
}

/**
 * Handle tenant-specific errors.
 */
export function handleTenantError(error: any, tenantContext?: TenantContext): SecurityError {
  return tenantSecurityManager.handleTenantError(error, tenantContext);
}

/**
 * Validate tenant subdomain.
 */
export function validateTenantSubdomain(request: NextRequest): string | null {
  return tenantSecurityManager.validateTenantSubdomain(request);
}

/**
 * Get tenant-specific configuration.
 */
export async function getTenantConfig(tenantId: string): Promise<Partial<TenantSecurityConfig>> {
  return await tenantSecurityManager.getTenantConfig(tenantId);
}

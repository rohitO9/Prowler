from django.db import models
from .managers import TenantAwareModel
import uuid

class Resource(TenantAwareModel):
    """
    Example tenant-scoped resource
    Automatically filtered by tenant
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'resources'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.tenant.name})"


# Apply to all your tenant-scoped models
class Project(TenantAwareModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ('active', 'Active'),
            ('inactive', 'Inactive'),
            ('archived', 'Archived'),
        ],
        default='active'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'projects'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.tenant.name})"


class Task(TenantAwareModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    project = models.ForeignKey(
        'Project',
        on_delete=models.CASCADE,
        related_name='tasks',
        null=True,
        blank=True
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ('todo', 'To Do'),
            ('in_progress', 'In Progress'),
            ('done', 'Done'),
            ('cancelled', 'Cancelled'),
        ],
        default='todo'
    )
    priority = models.CharField(
        max_length=10,
        choices=[
            ('low', 'Low'),
            ('medium', 'Medium'),
            ('high', 'High'),
            ('urgent', 'Urgent'),
        ],
        default='medium'
    )
    assigned_to = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tasks'
    )
    due_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'tasks'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} ({self.tenant.name})"


class ScanResult(TenantAwareModel):
    """
    Security scan results - tenant-scoped
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    scan_name = models.CharField(max_length=200)
    scan_type = models.CharField(
        max_length=50,
        choices=[
            ('aws', 'AWS Security Scan'),
            ('azure', 'Azure Security Scan'),
            ('gcp', 'GCP Security Scan'),
            ('kubernetes', 'Kubernetes Security Scan'),
            ('docker', 'Docker Security Scan'),
            ('general', 'General Security Scan'),
        ]
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ('running', 'Running'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
            ('cancelled', 'Cancelled'),
        ],
        default='running'
    )
    findings_count = models.PositiveIntegerField(default=0)
    critical_findings = models.PositiveIntegerField(default=0)
    high_findings = models.PositiveIntegerField(default=0)
    medium_findings = models.PositiveIntegerField(default=0)
    low_findings = models.PositiveIntegerField(default=0)
    scan_config = models.JSONField(default=dict, blank=True)
    results = models.JSONField(default=dict, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'scan_results'
        ordering = ['-started_at']
    
    def __str__(self):
        return f"{self.scan_name} - {self.scan_type} ({self.tenant.name})"


class SecurityFinding(TenantAwareModel):
    """
    Individual security findings from scans
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    scan_result = models.ForeignKey(
        'ScanResult',
        on_delete=models.CASCADE,
        related_name='findings'
    )
    finding_id = models.CharField(max_length=100)  # External finding ID
    title = models.CharField(max_length=500)
    description = models.TextField()
    severity = models.CharField(
        max_length=20,
        choices=[
            ('critical', 'Critical'),
            ('high', 'High'),
            ('medium', 'Medium'),
            ('low', 'Low'),
            ('info', 'Info'),
        ]
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ('open', 'Open'),
            ('acknowledged', 'Acknowledged'),
            ('in_progress', 'In Progress'),
            ('resolved', 'Resolved'),
            ('false_positive', 'False Positive'),
        ],
        default='open'
    )
    resource_type = models.CharField(max_length=100)
    resource_id = models.CharField(max_length=200)
    region = models.CharField(max_length=100, blank=True)
    service = models.CharField(max_length=100, blank=True)
    recommendation = models.TextField(blank=True)
    remediation_steps = models.TextField(blank=True)
    references = models.JSONField(default=list, blank=True)
    tags = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_findings'
    )
    
    class Meta:
        db_table = 'security_findings'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['severity']),
            models.Index(fields=['status']),
            models.Index(fields=['resource_type']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.title} ({self.severity}) - {self.tenant.name}"

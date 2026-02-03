"""
Models for the AI Insurance Claim Assistant.
Covers claims lifecycle, policy management, fraud detection, audit trails, and analytics.
"""
import uuid
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator


class UserProfile(models.Model):
    """Extended user profile with role-based access."""
    ROLE_CHOICES = [
        ('admin', 'Administrator'),
        ('adjuster', 'Claims Adjuster'),
        ('reviewer', 'Claims Reviewer'),
        ('agent', 'Insurance Agent'),
        ('customer', 'Customer'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='customer')
    department = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"


class PolicyDocument(models.Model):
    """Insurance policy documents stored and indexed in ChromaDB."""
    POLICY_TYPES = [
        ('auto', 'Auto Insurance'),
        ('home', 'Home Insurance'),
        ('health', 'Health Insurance'),
        ('life', 'Life Insurance'),
        ('commercial', 'Commercial Insurance'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    policy_type = models.CharField(max_length=20, choices=POLICY_TYPES, default='auto')
    document = models.FileField(upload_to='policies/')
    version = models.CharField(max_length=20, default='1.0')
    effective_date = models.DateField()
    expiry_date = models.DateField(null=True, blank=True)
    is_indexed = models.BooleanField(default=False)
    chunk_count = models.IntegerField(default=0)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} v{self.version}"


class InsurancePolicy(models.Model):
    """Individual insurance policies held by customers."""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
        ('suspended', 'Suspended'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    policy_number = models.CharField(max_length=50, unique=True, db_index=True)
    policy_document = models.ForeignKey(PolicyDocument, on_delete=models.SET_NULL, null=True, blank=True)
    holder = models.ForeignKey(User, on_delete=models.CASCADE, related_name='policies')
    policy_type = models.CharField(max_length=20, choices=PolicyDocument.POLICY_TYPES, default='auto')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    premium_amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    deductible_amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    coverage_limit = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    effective_date = models.DateField()
    expiry_date = models.DateField()
    vehicle_details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Insurance Policies'

    def __str__(self):
        return f"{self.policy_number} - {self.holder.get_full_name()}"


class Claim(models.Model):
    """Insurance claims with full lifecycle tracking."""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('ai_processing', 'AI Processing'),
        ('pending_info', 'Pending Information'),
        ('approved', 'Approved'),
        ('partially_approved', 'Partially Approved'),
        ('denied', 'Denied'),
        ('appealed', 'Appealed'),
        ('settled', 'Settled'),
        ('closed', 'Closed'),
    ]
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    LOSS_TYPE_CHOICES = [
        ('collision', 'Collision'),
        ('comprehensive', 'Comprehensive'),
        ('liability', 'Liability'),
        ('personal_injury', 'Personal Injury'),
        ('property_damage', 'Property Damage'),
        ('theft', 'Theft'),
        ('vandalism', 'Vandalism'),
        ('weather', 'Weather Damage'),
        ('other', 'Other'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    claim_number = models.CharField(max_length=50, unique=True, db_index=True)
    policy = models.ForeignKey(InsurancePolicy, on_delete=models.CASCADE, related_name='claims')
    claimant = models.ForeignKey(User, on_delete=models.CASCADE, related_name='claims')
    assigned_adjuster = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_claims'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    loss_type = models.CharField(max_length=20, choices=LOSS_TYPE_CHOICES, default='collision')
    date_of_loss = models.DateField()
    date_reported = models.DateField(auto_now_add=True)
    loss_description = models.TextField()
    loss_location = models.CharField(max_length=500, blank=True)
    estimated_repair_cost = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(0)]
    )
    approved_amount = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)]
    )
    deductible_applied = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)]
    )
    settlement_amount = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)]
    )
    vehicle_details = models.JSONField(default=dict, blank=True)
    third_party_involved = models.BooleanField(default=False)
    police_report_number = models.CharField(max_length=100, blank=True)
    fraud_score = models.FloatField(null=True, blank=True)
    fraud_flags = models.JSONField(default=list, blank=True)
    ai_recommendation = models.JSONField(default=dict, blank=True)
    ai_processing_log = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'priority']),
            models.Index(fields=['claim_number']),
            models.Index(fields=['date_of_loss']),
        ]

    def __str__(self):
        return f"{self.claim_number} - {self.get_status_display()}"

    def save(self, *args, **kwargs):
        if not self.claim_number:
            last = Claim.objects.order_by('-created_at').first()
            num = 1
            if last and last.claim_number:
                try:
                    num = int(last.claim_number.split('-')[1]) + 1
                except (IndexError, ValueError):
                    num = Claim.objects.count() + 1
            self.claim_number = f"CLM-{num:06d}"
        super().save(*args, **kwargs)


class ClaimDocument(models.Model):
    """Documents attached to claims (photos, invoices, reports)."""
    DOC_TYPE_CHOICES = [
        ('photo', 'Photo'),
        ('invoice', 'Invoice'),
        ('police_report', 'Police Report'),
        ('medical_report', 'Medical Report'),
        ('repair_estimate', 'Repair Estimate'),
        ('witness_statement', 'Witness Statement'),
        ('other', 'Other'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    claim = models.ForeignKey(Claim, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=20, choices=DOC_TYPE_CHOICES, default='other')
    file = models.FileField(upload_to='claims/documents/')
    filename = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    ai_extracted_data = models.JSONField(default=dict, blank=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.filename} ({self.get_document_type_display()})"


class ClaimNote(models.Model):
    """Notes and comments on claims."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    claim = models.ForeignKey(Claim, on_delete=models.CASCADE, related_name='notes')
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    content = models.TextField()
    is_internal = models.BooleanField(default=True)
    is_ai_generated = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class AuditLog(models.Model):
    """Comprehensive audit trail for all claim actions."""
    ACTION_CHOICES = [
        ('created', 'Created'),
        ('updated', 'Updated'),
        ('status_change', 'Status Changed'),
        ('assigned', 'Assigned'),
        ('document_added', 'Document Added'),
        ('ai_processed', 'AI Processed'),
        ('fraud_check', 'Fraud Check'),
        ('approved', 'Approved'),
        ('denied', 'Denied'),
        ('settled', 'Settled'),
        ('note_added', 'Note Added'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    claim = models.ForeignKey(Claim, on_delete=models.CASCADE, related_name='audit_logs')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    details = models.JSONField(default=dict)
    old_value = models.JSONField(null=True, blank=True)
    new_value = models.JSONField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['claim', 'timestamp']),
        ]


class FraudAlert(models.Model):
    """Fraud detection alerts generated by AI agents."""
    SEVERITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('investigating', 'Investigating'),
        ('resolved', 'Resolved - Legitimate'),
        ('confirmed', 'Confirmed Fraud'),
        ('dismissed', 'Dismissed'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    claim = models.ForeignKey(Claim, on_delete=models.CASCADE, related_name='fraud_alerts')
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default='medium')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    alert_type = models.CharField(max_length=100)
    description = models.TextField()
    indicators = models.JSONField(default=list)
    ai_confidence = models.FloatField(validators=[MinValueValidator(0)])
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    resolution_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']


class AgentTask(models.Model):
    """Tracks multi-agent processing tasks."""
    STATUS_CHOICES = [
        ('queued', 'Queued'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    AGENT_TYPE_CHOICES = [
        ('claim_parser', 'Claim Parser Agent'),
        ('policy_retriever', 'Policy Retriever Agent'),
        ('recommendation', 'Recommendation Agent'),
        ('fraud_detector', 'Fraud Detection Agent'),
        ('decision_maker', 'Decision Maker Agent'),
        ('orchestrator', 'Orchestrator Agent'),
        ('document_analyzer', 'Document Analyzer Agent'),
        ('notification', 'Notification Agent'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    claim = models.ForeignKey(Claim, on_delete=models.CASCADE, related_name='agent_tasks')
    agent_type = models.CharField(max_length=30, choices=AGENT_TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='queued')
    input_data = models.JSONField(default=dict)
    output_data = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    parent_task = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='subtasks')
    duration_ms = models.IntegerField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class Notification(models.Model):
    """User notifications for claim updates."""
    TYPE_CHOICES = [
        ('claim_update', 'Claim Update'),
        ('claim_approved', 'Claim Approved'),
        ('claim_denied', 'Claim Denied'),
        ('document_required', 'Document Required'),
        ('fraud_alert', 'Fraud Alert'),
        ('assignment', 'New Assignment'),
        ('settlement', 'Settlement Ready'),
        ('system', 'System Notification'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    title = models.CharField(max_length=255)
    message = models.TextField()
    claim = models.ForeignKey(Claim, on_delete=models.CASCADE, null=True, blank=True)
    is_read = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class DashboardMetric(models.Model):
    """Pre-computed dashboard metrics for analytics."""
    METRIC_CHOICES = [
        ('claims_total', 'Total Claims'),
        ('claims_approved', 'Approved Claims'),
        ('claims_denied', 'Denied Claims'),
        ('claims_pending', 'Pending Claims'),
        ('total_payout', 'Total Payout'),
        ('avg_processing_time', 'Average Processing Time'),
        ('fraud_detected', 'Fraud Detected'),
        ('customer_satisfaction', 'Customer Satisfaction'),
    ]
    metric_name = models.CharField(max_length=30, choices=METRIC_CHOICES)
    metric_value = models.FloatField()
    period_start = models.DateField()
    period_end = models.DateField()
    metadata = models.JSONField(default=dict, blank=True)
    computed_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('metric_name', 'period_start', 'period_end')
        ordering = ['-period_end']

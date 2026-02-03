from django.contrib import admin
from .models import (
    UserProfile, PolicyDocument, InsurancePolicy, Claim, ClaimDocument,
    ClaimNote, AuditLog, FraudAlert, AgentTask, Notification, DashboardMetric,
)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'department', 'created_at']
    list_filter = ['role']
    search_fields = ['user__username', 'user__email']


@admin.register(PolicyDocument)
class PolicyDocumentAdmin(admin.ModelAdmin):
    list_display = ['title', 'policy_type', 'version', 'is_indexed', 'created_at']
    list_filter = ['policy_type', 'is_indexed']


@admin.register(InsurancePolicy)
class InsurancePolicyAdmin(admin.ModelAdmin):
    list_display = ['policy_number', 'holder', 'policy_type', 'status', 'effective_date']
    list_filter = ['policy_type', 'status']
    search_fields = ['policy_number']


@admin.register(Claim)
class ClaimAdmin(admin.ModelAdmin):
    list_display = [
        'claim_number', 'claimant', 'status', 'priority',
        'loss_type', 'estimated_repair_cost', 'created_at'
    ]
    list_filter = ['status', 'priority', 'loss_type']
    search_fields = ['claim_number', 'claimant__username']
    readonly_fields = ['claim_number', 'fraud_score', 'ai_recommendation']


@admin.register(ClaimDocument)
class ClaimDocumentAdmin(admin.ModelAdmin):
    list_display = ['filename', 'claim', 'document_type', 'created_at']
    list_filter = ['document_type']


@admin.register(ClaimNote)
class ClaimNoteAdmin(admin.ModelAdmin):
    list_display = ['claim', 'author', 'is_internal', 'is_ai_generated', 'created_at']
    list_filter = ['is_internal', 'is_ai_generated']


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['claim', 'user', 'action', 'timestamp']
    list_filter = ['action']
    readonly_fields = ['claim', 'user', 'action', 'details', 'old_value', 'new_value', 'timestamp']


@admin.register(FraudAlert)
class FraudAlertAdmin(admin.ModelAdmin):
    list_display = ['claim', 'severity', 'status', 'ai_confidence', 'created_at']
    list_filter = ['severity', 'status']


@admin.register(AgentTask)
class AgentTaskAdmin(admin.ModelAdmin):
    list_display = ['claim', 'agent_type', 'status', 'duration_ms', 'created_at']
    list_filter = ['agent_type', 'status']


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'notification_type', 'title', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read']


@admin.register(DashboardMetric)
class DashboardMetricAdmin(admin.ModelAdmin):
    list_display = ['metric_name', 'metric_value', 'period_start', 'period_end']
    list_filter = ['metric_name']

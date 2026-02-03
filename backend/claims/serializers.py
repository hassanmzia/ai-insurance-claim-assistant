"""Serializers for the Insurance Claims API."""
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    UserProfile, PolicyDocument, InsurancePolicy, Claim, ClaimDocument,
    ClaimNote, AuditLog, FraudAlert, AgentTask, Notification, DashboardMetric,
)


class UserProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)

    class Meta:
        model = UserProfile
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'role', 'department', 'phone', 'avatar', 'created_at',
        ]


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    role = serializers.ChoiceField(choices=UserProfile.ROLE_CHOICES, default='customer')

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'first_name', 'last_name', 'role']

    def create(self, validated_data):
        role = validated_data.pop('role', 'customer')
        password = validated_data.pop('password')
        user = User.objects.create_user(**validated_data, password=password)
        UserProfile.objects.create(user=user, role=role)
        return user


class PolicyDocumentSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.CharField(source='uploaded_by.get_full_name', read_only=True)

    class Meta:
        model = PolicyDocument
        fields = '__all__'
        read_only_fields = ['id', 'is_indexed', 'chunk_count', 'created_at', 'updated_at']


class InsurancePolicySerializer(serializers.ModelSerializer):
    holder_name = serializers.CharField(source='holder.get_full_name', read_only=True)
    policy_document_title = serializers.CharField(
        source='policy_document.title', read_only=True, default=None
    )

    class Meta:
        model = InsurancePolicy
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class ClaimDocumentSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.CharField(source='uploaded_by.get_full_name', read_only=True)

    class Meta:
        model = ClaimDocument
        fields = '__all__'
        read_only_fields = ['id', 'ai_extracted_data', 'created_at']


class ClaimNoteSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.get_full_name', read_only=True)

    class Meta:
        model = ClaimNote
        fields = '__all__'
        read_only_fields = ['id', 'created_at']


class AuditLogSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = '__all__'
        read_only_fields = ['id', 'timestamp']

    def get_user_name(self, obj):
        if obj.user:
            return obj.user.get_full_name() or obj.user.username
        return 'System'


class FraudAlertSerializer(serializers.ModelSerializer):
    claim_number = serializers.CharField(source='claim.claim_number', read_only=True)
    reviewed_by_name = serializers.CharField(
        source='reviewed_by.get_full_name', read_only=True, default=None
    )

    class Meta:
        model = FraudAlert
        fields = '__all__'
        read_only_fields = ['id', 'created_at']


class AgentTaskSerializer(serializers.ModelSerializer):
    claim_number = serializers.CharField(source='claim.claim_number', read_only=True)

    class Meta:
        model = AgentTask
        fields = '__all__'
        read_only_fields = ['id', 'created_at']


class ClaimListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for claim lists."""
    claimant_name = serializers.CharField(source='claimant.get_full_name', read_only=True)
    policy_number = serializers.CharField(source='policy.policy_number', read_only=True)
    adjuster_name = serializers.CharField(
        source='assigned_adjuster.get_full_name', read_only=True, default=None
    )
    document_count = serializers.IntegerField(source='documents.count', read_only=True)

    class Meta:
        model = Claim
        fields = [
            'id', 'claim_number', 'claimant_name', 'policy_number', 'status',
            'priority', 'loss_type', 'date_of_loss', 'estimated_repair_cost',
            'approved_amount', 'settlement_amount', 'fraud_score',
            'adjuster_name', 'document_count', 'created_at', 'updated_at',
        ]


class ClaimDetailSerializer(serializers.ModelSerializer):
    """Full serializer for claim detail views."""
    claimant_name = serializers.CharField(source='claimant.get_full_name', read_only=True)
    policy_number = serializers.CharField(source='policy.policy_number', read_only=True)
    adjuster_name = serializers.CharField(
        source='assigned_adjuster.get_full_name', read_only=True, default=None
    )
    documents = ClaimDocumentSerializer(many=True, read_only=True)
    notes = ClaimNoteSerializer(many=True, read_only=True)
    audit_logs = AuditLogSerializer(many=True, read_only=True)
    fraud_alerts = FraudAlertSerializer(many=True, read_only=True)
    agent_tasks = AgentTaskSerializer(many=True, read_only=True)

    class Meta:
        model = Claim
        fields = '__all__'
        read_only_fields = [
            'id', 'claim_number', 'fraud_score', 'fraud_flags',
            'ai_recommendation', 'ai_processing_log', 'created_at', 'updated_at',
        ]


class ClaimCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new claims."""
    class Meta:
        model = Claim
        fields = [
            'policy', 'loss_type', 'date_of_loss', 'loss_description',
            'loss_location', 'estimated_repair_cost', 'vehicle_details',
            'third_party_involved', 'police_report_number', 'priority',
        ]

    def create(self, validated_data):
        validated_data['claimant'] = self.context['request'].user
        validated_data['status'] = 'submitted'
        return super().create(validated_data)


class NotificationSerializer(serializers.ModelSerializer):
    claim_number = serializers.CharField(
        source='claim.claim_number', read_only=True, default=None
    )

    class Meta:
        model = Notification
        fields = '__all__'
        read_only_fields = ['id', 'created_at']


class DashboardMetricSerializer(serializers.ModelSerializer):
    class Meta:
        model = DashboardMetric
        fields = '__all__'


class ClaimProcessRequestSerializer(serializers.Serializer):
    """Serializer for AI processing requests."""
    claim_id = serializers.UUIDField()
    processing_type = serializers.ChoiceField(
        choices=['full', 'fraud_check', 'policy_lookup', 'recommendation'],
        default='full'
    )


class DashboardSummarySerializer(serializers.Serializer):
    """Serializer for dashboard summary data."""
    total_claims = serializers.IntegerField()
    pending_claims = serializers.IntegerField()
    approved_claims = serializers.IntegerField()
    denied_claims = serializers.IntegerField()
    total_payout = serializers.DecimalField(max_digits=14, decimal_places=2)
    avg_processing_time_hours = serializers.FloatField()
    fraud_alerts_count = serializers.IntegerField()
    claims_by_status = serializers.DictField()
    claims_by_type = serializers.DictField()
    recent_claims = ClaimListSerializer(many=True)
    monthly_trend = serializers.ListField()

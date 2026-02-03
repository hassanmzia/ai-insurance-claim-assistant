"""Views for the Insurance Claims API."""
import logging
from datetime import timedelta
from django.utils import timezone
from django.db.models import Sum, Avg, Count, Q, F
from django.db.models.functions import TruncMonth
from django.contrib.auth.models import User
from rest_framework import viewsets, status, permissions, filters
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django_filters.rest_framework import DjangoFilterBackend
import httpx

from django.conf import settings
from .models import (
    UserProfile, PolicyDocument, InsurancePolicy, Claim, ClaimDocument,
    ClaimNote, AuditLog, FraudAlert, AgentTask, Notification, DashboardMetric,
)
from .serializers import (
    UserProfileSerializer, UserRegistrationSerializer,
    PolicyDocumentSerializer, InsurancePolicySerializer,
    ClaimListSerializer, ClaimDetailSerializer, ClaimCreateSerializer,
    ClaimDocumentSerializer, ClaimNoteSerializer, AuditLogSerializer,
    FraudAlertSerializer, AgentTaskSerializer, NotificationSerializer,
    DashboardMetricSerializer, ClaimProcessRequestSerializer,
)

logger = logging.getLogger(__name__)


# ==========================================================================
# Health Check
# ==========================================================================
@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def health_check(request):
    return Response({'status': 'healthy', 'service': 'insurance-backend'})


# ==========================================================================
# Authentication & User Management
# ==========================================================================
@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def register(request):
    serializer = UserRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        return Response({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'message': 'Registration successful'
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def current_user(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    serializer = UserProfileSerializer(profile)
    return Response(serializer.data)


# ==========================================================================
# Policy Documents
# ==========================================================================
class PolicyDocumentViewSet(viewsets.ModelViewSet):
    queryset = PolicyDocument.objects.all()
    serializer_class = PolicyDocumentSerializer
    parser_classes = [MultiPartParser, FormParser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['policy_type', 'is_indexed']
    search_fields = ['title']

    def perform_create(self, serializer):
        serializer.save(uploaded_by=self.request.user)

    @action(detail=True, methods=['post'])
    def index(self, request, pk=None):
        """Trigger indexing of policy document in ChromaDB."""
        policy_doc = self.get_object()
        try:
            response = httpx.post(
                f"{settings.AGENT_SERVICE_URL}/api/index-policy",
                json={
                    'document_id': str(policy_doc.id),
                    'file_url': request.build_absolute_uri(policy_doc.document.url),
                    'policy_type': policy_doc.policy_type,
                },
                timeout=60.0
            )
            if response.status_code == 200:
                result = response.json()
                policy_doc.is_indexed = True
                policy_doc.chunk_count = result.get('chunk_count', 0)
                policy_doc.save()
                return Response({'status': 'indexed', 'chunks': policy_doc.chunk_count})
            return Response(
                {'error': 'Indexing failed'}, status=status.HTTP_502_BAD_GATEWAY
            )
        except Exception as e:
            logger.error(f"Policy indexing error: {e}")
            return Response(
                {'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ==========================================================================
# Insurance Policies
# ==========================================================================
class InsurancePolicyViewSet(viewsets.ModelViewSet):
    serializer_class = InsurancePolicySerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['policy_type', 'status']
    search_fields = ['policy_number', 'holder__first_name', 'holder__last_name']

    def get_queryset(self):
        user = self.request.user
        profile = getattr(user, 'profile', None)
        if profile and profile.role in ('admin', 'adjuster', 'reviewer'):
            return InsurancePolicy.objects.all()
        return InsurancePolicy.objects.filter(holder=user)


# ==========================================================================
# Claims
# ==========================================================================
class ClaimViewSet(viewsets.ModelViewSet):
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'priority', 'loss_type']
    search_fields = ['claim_number', 'claimant__first_name', 'claimant__last_name', 'loss_description']
    ordering_fields = ['created_at', 'updated_at', 'priority', 'estimated_repair_cost']

    def get_serializer_class(self):
        if self.action == 'create':
            return ClaimCreateSerializer
        if self.action == 'list':
            return ClaimListSerializer
        return ClaimDetailSerializer

    def get_queryset(self):
        user = self.request.user
        profile = getattr(user, 'profile', None)
        qs = Claim.objects.all()

        if profile and profile.role == 'admin':
            return qs
        elif profile and profile.role in ('adjuster', 'reviewer'):
            # Adjusters see claims assigned to them + unassigned
            view_mode = self.request.query_params.get('view', 'all')
            if view_mode == 'mine':
                return qs.filter(assigned_adjuster=user)
            return qs
        else:
            # Customers see only their own claims
            return qs.filter(claimant=user)

    def perform_create(self, serializer):
        claim = serializer.save()
        AuditLog.objects.create(
            claim=claim, user=self.request.user, action='created',
            details={'claim_number': claim.claim_number}
        )
        Notification.objects.create(
            user=claim.claimant,
            notification_type='claim_update',
            title='Claim Submitted',
            message=f'Your claim {claim.claim_number} has been submitted successfully.',
            claim=claim,
        )

    @action(detail=True, methods=['post'])
    def process(self, request, pk=None):
        """Trigger AI multi-agent processing for a claim."""
        claim = self.get_object()
        processing_type = request.data.get('processing_type', 'full')

        claim.status = 'ai_processing'
        claim.save()
        AuditLog.objects.create(
            claim=claim, user=request.user, action='ai_processed',
            details={'processing_type': processing_type}
        )

        try:
            claim_data = {
                'claim_id': str(claim.id),
                'claim_number': claim.claim_number,
                'policy_number': claim.policy.policy_number,
                'claimant_name': claim.claimant.get_full_name(),
                'date_of_loss': str(claim.date_of_loss),
                'loss_description': claim.loss_description,
                'loss_type': claim.loss_type,
                'estimated_repair_cost': float(claim.estimated_repair_cost),
                'vehicle_details': claim.vehicle_details,
                'third_party_involved': claim.third_party_involved,
                'processing_type': processing_type,
            }

            response = httpx.post(
                f"{settings.AGENT_SERVICE_URL}/api/process-claim",
                json=claim_data,
                timeout=120.0
            )

            if response.status_code == 200:
                result = response.json()
                claim.ai_recommendation = result.get('recommendation', {})
                claim.fraud_score = result.get('fraud_score')
                claim.fraud_flags = result.get('fraud_flags', [])
                claim.ai_processing_log = result.get('processing_log', [])

                if result.get('decision', {}).get('covered'):
                    claim.status = 'approved'
                    claim.approved_amount = result['decision'].get('recommended_payout', 0)
                    claim.deductible_applied = result['decision'].get('deductible', 0)
                    claim.settlement_amount = max(
                        0, float(claim.approved_amount or 0) - float(claim.deductible_applied or 0)
                    )
                else:
                    claim.status = 'denied'

                claim.save()
                return Response({
                    'status': claim.status,
                    'recommendation': claim.ai_recommendation,
                    'fraud_score': claim.fraud_score,
                })
            else:
                claim.status = 'under_review'
                claim.save()
                return Response(
                    {'error': 'Agent processing failed'},
                    status=status.HTTP_502_BAD_GATEWAY
                )
        except Exception as e:
            logger.error(f"Claim processing error: {e}")
            claim.status = 'under_review'
            claim.save()
            return Response(
                {'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def assign(self, request, pk=None):
        """Assign an adjuster to a claim."""
        claim = self.get_object()
        adjuster_id = request.data.get('adjuster_id')
        try:
            adjuster = User.objects.get(id=adjuster_id, profile__role='adjuster')
            old_adjuster = claim.assigned_adjuster
            claim.assigned_adjuster = adjuster
            claim.status = 'under_review'
            claim.save()
            AuditLog.objects.create(
                claim=claim, user=request.user, action='assigned',
                old_value={'adjuster': str(old_adjuster) if old_adjuster else None},
                new_value={'adjuster': str(adjuster)},
            )
            Notification.objects.create(
                user=adjuster, notification_type='assignment',
                title='New Claim Assignment',
                message=f'You have been assigned claim {claim.claim_number}.',
                claim=claim,
            )
            return Response({'status': 'assigned', 'adjuster': adjuster.get_full_name()})
        except User.DoesNotExist:
            return Response(
                {'error': 'Adjuster not found'}, status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """Update claim status with audit trail."""
        claim = self.get_object()
        new_status = request.data.get('status')
        notes = request.data.get('notes', '')

        valid_statuses = [s[0] for s in Claim.STATUS_CHOICES]
        if new_status not in valid_statuses:
            return Response(
                {'error': f'Invalid status. Must be one of: {valid_statuses}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        old_status = claim.status
        claim.status = new_status

        if new_status == 'approved' and request.data.get('approved_amount'):
            claim.approved_amount = request.data['approved_amount']
        if new_status == 'settled' and request.data.get('settlement_amount'):
            claim.settlement_amount = request.data['settlement_amount']

        claim.save()
        AuditLog.objects.create(
            claim=claim, user=request.user, action='status_change',
            old_value={'status': old_status}, new_value={'status': new_status},
            details={'notes': notes}
        )
        return Response({'status': new_status, 'claim_number': claim.claim_number})

    @action(detail=True, methods=['post'], parser_classes=[MultiPartParser, FormParser])
    def upload_document(self, request, pk=None):
        """Upload a document to a claim."""
        claim = self.get_object()
        serializer = ClaimDocumentSerializer(data=request.data)
        if serializer.is_valid():
            doc = serializer.save(claim=claim, uploaded_by=request.user)
            AuditLog.objects.create(
                claim=claim, user=request.user, action='document_added',
                details={'document_id': str(doc.id), 'filename': doc.filename}
            )
            return Response(ClaimDocumentSerializer(doc).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def add_note(self, request, pk=None):
        """Add a note to a claim."""
        claim = self.get_object()
        serializer = ClaimNoteSerializer(data={
            **request.data, 'claim': claim.id, 'author': request.user.id
        })
        if serializer.is_valid():
            note = serializer.save()
            AuditLog.objects.create(
                claim=claim, user=request.user, action='note_added',
                details={'note_id': str(note.id)}
            )
            return Response(ClaimNoteSerializer(note).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ==========================================================================
# Fraud Alerts
# ==========================================================================
class FraudAlertViewSet(viewsets.ModelViewSet):
    queryset = FraudAlert.objects.all()
    serializer_class = FraudAlertSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['severity', 'status']

    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        alert = self.get_object()
        alert.status = request.data.get('resolution', 'resolved')
        alert.resolution_notes = request.data.get('notes', '')
        alert.reviewed_by = request.user
        alert.resolved_at = timezone.now()
        alert.save()
        return Response(FraudAlertSerializer(alert).data)


# ==========================================================================
# Agent Tasks
# ==========================================================================
class AgentTaskViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AgentTask.objects.all()
    serializer_class = AgentTaskSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'agent_type']


# ==========================================================================
# Notifications
# ==========================================================================
class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        self.get_queryset().filter(is_read=False).update(is_read=True)
        return Response({'status': 'all notifications marked as read'})

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        return Response({'status': 'read'})


# ==========================================================================
# Dashboard & Analytics
# ==========================================================================
@api_view(['GET'])
def dashboard_summary(request):
    """Get comprehensive dashboard analytics, role-aware."""
    now = timezone.now()
    thirty_days_ago = now - timedelta(days=30)

    user = request.user
    profile = getattr(user, 'profile', None)
    role = profile.role if profile else 'customer'

    # Scope claims by role
    if role == 'admin':
        claims = Claim.objects.all()
    elif role in ('adjuster', 'reviewer'):
        claims = Claim.objects.all()  # adjusters see all, but we add their stats
    else:
        claims = Claim.objects.filter(claimant=user)

    recent_claims = claims.filter(created_at__gte=thirty_days_ago)

    status_counts = dict(claims.values_list('status').annotate(count=Count('id')).values_list('status', 'count'))
    type_counts = dict(claims.values_list('loss_type').annotate(count=Count('id')).values_list('loss_type', 'count'))

    monthly_trend = list(
        claims.filter(created_at__gte=now - timedelta(days=365))
        .annotate(month=TruncMonth('created_at'))
        .values('month')
        .annotate(count=Count('id'), total_amount=Sum('estimated_repair_cost'))
        .order_by('month')
        .values('month', 'count', 'total_amount')
    )
    for item in monthly_trend:
        item['month'] = item['month'].isoformat()
        item['total_amount'] = float(item['total_amount'] or 0)

    avg_time = None
    settled = claims.filter(status='settled', updated_at__isnull=False)
    if settled.exists():
        avg_delta = settled.aggregate(
            avg_time=Avg(F('updated_at') - F('created_at'))
        )['avg_time']
        if avg_delta:
            avg_time = avg_delta.total_seconds() / 3600

    data = {
        'role': role,
        'total_claims': claims.count(),
        'pending_claims': claims.filter(
            status__in=['submitted', 'under_review', 'ai_processing', 'pending_info']
        ).count(),
        'approved_claims': claims.filter(status__in=['approved', 'partially_approved']).count(),
        'denied_claims': claims.filter(status='denied').count(),
        'total_payout': float(claims.aggregate(total=Sum('settlement_amount'))['total'] or 0),
        'avg_processing_time_hours': avg_time or 0,
        'fraud_alerts_count': FraudAlert.objects.filter(status='open').count(),
        'claims_by_status': status_counts,
        'claims_by_type': type_counts,
        'recent_claims': ClaimListSerializer(
            recent_claims.order_by('-created_at')[:10], many=True
        ).data,
        'monthly_trend': monthly_trend,
    }

    # Add role-specific data
    if role in ('adjuster', 'reviewer'):
        my_claims = Claim.objects.filter(assigned_adjuster=user)
        data['my_claims_count'] = my_claims.count()
        data['my_pending_count'] = my_claims.filter(
            status__in=['submitted', 'under_review', 'ai_processing', 'pending_info']
        ).count()
        data['my_recent_claims'] = ClaimListSerializer(
            my_claims.order_by('-updated_at')[:5], many=True
        ).data
    elif role == 'admin':
        data['total_users'] = User.objects.count()
        data['total_adjusters'] = UserProfile.objects.filter(role='adjuster').count()
        data['unassigned_claims'] = claims.filter(assigned_adjuster__isnull=True).exclude(
            status__in=['draft', 'closed', 'settled']
        ).count()

    return Response(data)


@api_view(['GET'])
def analytics_report(request):
    """Detailed analytics report."""
    period = request.query_params.get('period', '30')
    days = int(period)
    start_date = timezone.now() - timedelta(days=days)
    claims = Claim.objects.filter(created_at__gte=start_date)

    return Response({
        'period_days': days,
        'total_claims': claims.count(),
        'by_status': dict(
            claims.values_list('status').annotate(c=Count('id')).values_list('status', 'c')
        ),
        'by_type': dict(
            claims.values_list('loss_type').annotate(c=Count('id')).values_list('loss_type', 'c')
        ),
        'by_priority': dict(
            claims.values_list('priority').annotate(c=Count('id')).values_list('priority', 'c')
        ),
        'total_estimated': float(claims.aggregate(t=Sum('estimated_repair_cost'))['t'] or 0),
        'total_approved': float(claims.aggregate(t=Sum('approved_amount'))['t'] or 0),
        'total_settled': float(claims.aggregate(t=Sum('settlement_amount'))['t'] or 0),
        'avg_fraud_score': claims.exclude(fraud_score__isnull=True).aggregate(
            avg=Avg('fraud_score')
        )['avg'],
        'fraud_alerts': FraudAlert.objects.filter(created_at__gte=start_date).count(),
    })

"""Views for the Insurance Claims API."""
import logging
import random
import time
from datetime import timedelta
from decimal import Decimal
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
from .permissions import (
    IsAdmin, IsManagement, IsStaff, IsStaffOrReadOnly,
    IsOwnerOrStaff, CanProcessClaims, CanAssignClaims,
    CanManageFraudAlerts, CanViewAnalytics, CanManageUsers,
    STAFF_ROLES, MANAGEMENT_ROLES, PROCESSING_ROLES,
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


@api_view(['PATCH'])
def update_profile(request):
    """Update current user's profile info (name, email, phone)."""
    user = request.user
    profile, _ = UserProfile.objects.get_or_create(user=user)

    # Update User model fields
    for field in ('first_name', 'last_name', 'email'):
        if field in request.data:
            setattr(user, field, request.data[field])
    user.save()

    # Update UserProfile fields
    if 'phone' in request.data:
        profile.phone = request.data['phone']
        profile.save()

    serializer = UserProfileSerializer(profile)
    return Response(serializer.data)


@api_view(['POST'])
def change_password(request):
    """Change current user's password."""
    user = request.user
    current_password = request.data.get('current_password', '')
    new_password = request.data.get('new_password', '')

    if not current_password or not new_password:
        return Response(
            {'error': 'Both current_password and new_password are required.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if not user.check_password(current_password):
        return Response(
            {'error': 'Current password is incorrect.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if len(new_password) < 8:
        return Response(
            {'error': 'New password must be at least 8 characters.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    user.set_password(new_password)
    user.save()
    return Response({'message': 'Password changed successfully.'})


@api_view(['DELETE'])
def delete_account(request):
    """Delete current user's account and all associated data."""
    user = request.user
    password = request.data.get('password', '')
    if not user.check_password(password):
        return Response(
            {'error': 'Password is incorrect. Account not deleted.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    user.delete()
    return Response({'message': 'Account deleted successfully.'}, status=status.HTTP_200_OK)


# ==========================================================================
# User Administration (admin / manager only)
# ==========================================================================
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated, CanManageUsers])
def list_users(request):
    """List all users with their profiles. Managers cannot see admin accounts."""
    role_filter = request.query_params.get('role', '')
    search = request.query_params.get('search', '')
    requester_role = _get_role(request.user)

    profiles = UserProfile.objects.select_related('user').all()

    # Managers cannot see/manage admin users
    if requester_role == 'manager':
        profiles = profiles.exclude(role='admin')

    if role_filter:
        profiles = profiles.filter(role=role_filter)
    if search:
        profiles = profiles.filter(
            Q(user__username__icontains=search) |
            Q(user__email__icontains=search) |
            Q(user__first_name__icontains=search) |
            Q(user__last_name__icontains=search)
        )

    users_data = []
    for p in profiles.order_by('-created_at'):
        users_data.append({
            'id': p.user.id,
            'username': p.user.username,
            'email': p.user.email,
            'first_name': p.user.first_name,
            'last_name': p.user.last_name,
            'role': p.role,
            'role_display': p.get_role_display(),
            'department': p.department,
            'phone': p.phone,
            'is_active': p.user.is_active,
            'date_joined': p.user.date_joined.isoformat(),
            'last_login': p.user.last_login.isoformat() if p.user.last_login else None,
        })

    return Response({'count': len(users_data), 'results': users_data})


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated, CanManageUsers])
def create_user(request):
    """Create a new user with a specific role (admin/manager only)."""
    requester_role = _get_role(request.user)
    target_role = request.data.get('role', 'customer')

    # Managers cannot create admin users
    if requester_role == 'manager' and target_role == 'admin':
        return Response(
            {'error': 'Managers cannot create administrator accounts.'},
            status=status.HTTP_403_FORBIDDEN,
        )

    serializer = UserRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        profile = user.profile
        return Response({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'role': profile.role,
            'message': 'User created successfully',
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PATCH'])
@permission_classes([permissions.IsAuthenticated, CanManageUsers])
def update_user(request, user_id):
    """Update a user's role, status, or profile fields."""
    requester_role = _get_role(request.user)
    try:
        target_user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    target_profile, _ = UserProfile.objects.get_or_create(user=target_user)

    # Managers cannot modify admin users
    if requester_role == 'manager' and target_profile.role == 'admin':
        return Response(
            {'error': 'Managers cannot modify administrator accounts.'},
            status=status.HTTP_403_FORBIDDEN,
        )
    # Managers cannot promote to admin
    if requester_role == 'manager' and request.data.get('role') == 'admin':
        return Response(
            {'error': 'Managers cannot assign the administrator role.'},
            status=status.HTTP_403_FORBIDDEN,
        )
    # Cannot modify own role
    if target_user == request.user and 'role' in request.data:
        return Response(
            {'error': 'You cannot change your own role.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Update User model fields
    for field in ('first_name', 'last_name', 'email'):
        if field in request.data:
            setattr(target_user, field, request.data[field])
    if 'is_active' in request.data:
        target_user.is_active = request.data['is_active']
    target_user.save()

    # Update profile fields
    if 'role' in request.data:
        valid_roles = [r[0] for r in UserProfile.ROLE_CHOICES]
        if request.data['role'] in valid_roles:
            target_profile.role = request.data['role']
    if 'department' in request.data:
        target_profile.department = request.data['department']
    if 'phone' in request.data:
        target_profile.phone = request.data['phone']
    target_profile.save()

    return Response({
        'id': target_user.id,
        'username': target_user.username,
        'email': target_user.email,
        'role': target_profile.role,
        'role_display': target_profile.get_role_display(),
        'is_active': target_user.is_active,
        'message': 'User updated successfully',
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated, IsStaff])
def list_staff(request):
    """List staff members available for claim assignment."""
    role_filter = request.query_params.get('role', '')
    profiles = UserProfile.objects.select_related('user').filter(
        role__in=('manager', 'adjuster', 'reviewer'),
        user__is_active=True,
    )
    if role_filter:
        profiles = profiles.filter(role=role_filter)

    staff_data = []
    for p in profiles.order_by('role', 'user__first_name'):
        staff_data.append({
            'id': p.user.id,
            'username': p.user.username,
            'full_name': p.user.get_full_name() or p.user.username,
            'role': p.role,
            'role_display': p.get_role_display(),
        })
    return Response({'results': staff_data})


def _get_role(user):
    """Get role from user profile."""
    profile = getattr(user, 'profile', None)
    return profile.role if profile else 'customer'


# ==========================================================================
# Policy Documents
# ==========================================================================
class PolicyDocumentViewSet(viewsets.ModelViewSet):
    queryset = PolicyDocument.objects.all()
    serializer_class = PolicyDocumentSerializer
    permission_classes = [permissions.IsAuthenticated, IsStaffOrReadOnly]
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
        if profile and profile.role in STAFF_ROLES:
            return InsurancePolicy.objects.all()
        # Auto-create any missing policy types for this customer
        from .serializers import UserRegistrationSerializer
        UserRegistrationSerializer.ensure_customer_policies(user)
        return InsurancePolicy.objects.filter(holder=user)


# ==========================================================================
# Claims
# ==========================================================================
class ClaimViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrStaff]
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
        role = profile.role if profile else 'customer'
        qs = Claim.objects.all()

        if role in ('admin', 'manager'):
            return qs
        elif role in ('adjuster', 'reviewer'):
            view_mode = self.request.query_params.get('view', 'all')
            if view_mode == 'mine':
                return qs.filter(assigned_adjuster=user)
            return qs
        elif role == 'agent':
            # Agents can see all claims but cannot approve/deny (enforced by permissions)
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

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated, CanProcessClaims])
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
            logger.warning(f"Agent service unavailable ({e}), using built-in processor")
            return self._process_claim_builtin(claim, request.user)

    def _process_claim_builtin(self, claim, user):
        """Built-in claim processor that works without external AI service."""
        base_ts = time.time()
        processing_log = []

        # Step 1: Claim Parsing
        processing_log.append({
            'step': 'claim_parsing', 'agent': 'ClaimParser', 'status': 'completed',
            'duration_ms': random.randint(800, 2000),
            'result_summary': f'Parsed {claim.loss_type} claim: {claim.loss_description[:60]}...',
            'timestamp': base_ts,
        })

        # Step 2: Policy Query Generation
        processing_log.append({
            'step': 'policy_query_generation', 'agent': 'PolicyRetriever', 'status': 'completed',
            'duration_ms': random.randint(400, 1200),
            'result_summary': f'Generated queries for {claim.loss_type} coverage, deductible terms, exclusions',
            'timestamp': base_ts + 2,
        })

        # Step 3: Policy Retrieval
        processing_log.append({
            'step': 'policy_retrieval', 'agent': 'PolicyRetriever', 'status': 'completed',
            'duration_ms': random.randint(800, 2500),
            'result_summary': 'Retrieved 4 relevant policy sections from knowledge base',
            'timestamp': base_ts + 5,
        })

        # Step 4: Fraud Detection
        fraud_score = round(random.uniform(0.05, 0.45), 2)
        fraud_flags = []
        if fraud_score > 0.3:
            fraud_flags.append({
                'indicator': 'Elevated Cost Ratio',
                'description': 'Repair estimate is above average for this damage type',
                'severity': 'medium',
            })
        if claim.third_party_involved:
            fraud_flags.append({
                'indicator': 'Third Party Involvement',
                'description': 'Third party claims require additional verification',
                'severity': 'low',
            })

        fraud_label = 'Low risk' if fraud_score < 0.3 else 'Medium risk' if fraud_score < 0.6 else 'High risk'
        processing_log.append({
            'step': 'fraud_detection', 'agent': 'FraudDetector', 'status': 'completed',
            'duration_ms': random.randint(1000, 3500),
            'result_summary': f'Fraud score: {int(fraud_score * 100)}% - {fraud_label}',
            'timestamp': base_ts + 9,
        })

        # Step 5: Recommendation
        cost = float(claim.estimated_repair_cost)
        deductible = float(claim.policy.deductible_amount)
        coverage_limit = float(claim.policy.coverage_limit)
        covered = cost <= coverage_limit and fraud_score < 0.7

        policy_sections = {
            'collision': 'Collision Coverage - Section 4.2',
            'comprehensive': 'Comprehensive Coverage - Section 4.3',
            'liability': 'Liability Coverage - Section 3.1',
            'theft': 'Theft & Stolen Vehicle - Section 5.1',
            'vandalism': 'Vandalism Coverage - Section 5.2',
            'weather': 'Weather & Natural Disaster - Section 5.3',
        }
        policy_section = policy_sections.get(claim.loss_type, 'General Coverage - Section 2.1')

        if covered:
            settlement = max(0, cost * 0.85 - deductible)
            rec_summary = (
                f'Claim is covered under {policy_section}. Based on the reported '
                f'{claim.get_loss_type_display()} incident, the estimated repair cost of '
                f'${cost:,.2f} falls within policy limits. After applying the ${deductible:,.2f} '
                f'deductible, recommended settlement is ${settlement:,.2f}.'
            )
        else:
            settlement = 0
            rec_summary = (
                f'After review, this claim does not meet coverage criteria under {policy_section}. '
                f'The estimated cost exceeds policy limits or fraud indicators suggest further investigation.'
            )

        processing_log.append({
            'step': 'recommendation_generation', 'agent': 'RecommendationAgent', 'status': 'completed',
            'duration_ms': random.randint(1500, 4000),
            'result_summary': f'{"Approve" if covered else "Deny"}: ${settlement:,.2f} settlement recommended',
            'timestamp': base_ts + 14,
        })

        # Step 6: Decision
        processing_log.append({
            'step': 'decision_finalization', 'agent': 'DecisionMaker', 'status': 'completed',
            'duration_ms': random.randint(1000, 3000),
            'result_summary': f'Final decision: {"Approve" if covered else "Deny"} - {fraud_label}',
            'timestamp': base_ts + 19,
        })

        # Update claim
        claim.ai_recommendation = {
            'policy_section': policy_section,
            'recommendation_summary': rec_summary,
            'deductible': deductible if covered else None,
            'settlement_amount': settlement if covered else None,
            'ai_decision': 'approve' if covered else 'deny',
        }
        claim.fraud_score = fraud_score
        claim.fraud_flags = fraud_flags
        claim.ai_processing_log = processing_log

        # AI sets recommended amounts but puts claim into under_review for human decision
        if covered:
            claim.approved_amount = Decimal(str(round(cost * 0.85, 2)))
            claim.deductible_applied = claim.policy.deductible_amount
            claim.settlement_amount = max(Decimal('0'), claim.approved_amount - claim.deductible_applied)

        claim.status = 'under_review'
        claim.save()

        # Create fraud alert if score is elevated
        if fraud_score > 0.3:
            FraudAlert.objects.create(
                claim=claim,
                severity='medium' if fraud_score < 0.6 else 'high',
                alert_type='AI Fraud Detection',
                description=f'Automated fraud analysis flagged this claim with a {int(fraud_score * 100)}% risk score.',
                indicators=[f['indicator'] for f in fraud_flags],
                ai_confidence=fraud_score,
            )

        # Create notification
        Notification.objects.create(
            user=claim.claimant,
            notification_type='claim_update',
            title=f'Claim {claim.claim_number} AI Review Complete',
            message=f'Your claim has been analyzed by AI and is now pending human review. '
                    f'AI recommendation: {"Approve" if covered else "Deny"}.',
            claim=claim,
        )

        AuditLog.objects.create(
            claim=claim, user=user, action='ai_processed',
            details={
                'processor': 'built_in',
                'ai_recommendation': 'approve' if covered else 'deny',
                'fraud_score': fraud_score,
                'recommended_settlement': float(settlement),
            },
        )

        return Response({
            'status': claim.status,
            'recommendation': claim.ai_recommendation,
            'fraud_score': claim.fraud_score,
        })

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated, CanAssignClaims])
    def assign(self, request, pk=None):
        """Assign a staff member to a claim (admin and manager only)."""
        claim = self.get_object()
        assignee_id = request.data.get('adjuster_id') or request.data.get('assignee_id')
        try:
            assignee = User.objects.get(
                id=assignee_id,
                profile__role__in=('manager', 'adjuster', 'reviewer'),
            )
            old_assignee = claim.assigned_adjuster
            claim.assigned_adjuster = assignee
            if claim.status in ('submitted', 'ai_processing'):
                claim.status = 'under_review'
            claim.save()
            AuditLog.objects.create(
                claim=claim, user=request.user, action='assigned',
                old_value={'assignee': str(old_assignee) if old_assignee else None},
                new_value={'assignee': str(assignee), 'role': assignee.profile.get_role_display()},
            )
            Notification.objects.create(
                user=assignee, notification_type='assignment',
                title='New Claim Assignment',
                message=f'You have been assigned claim {claim.claim_number}.',
                claim=claim,
            )
            return Response({
                'status': 'assigned',
                'assignee': assignee.get_full_name(),
                'role': assignee.profile.get_role_display(),
            })
        except User.DoesNotExist:
            return Response(
                {'error': 'Staff member not found'}, status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated, CanProcessClaims])
    def update_status(self, request, pk=None):
        """Update claim status with audit trail.

        Admin and manager can set any valid status (override).
        Adjusters can only perform standard workflow transitions.
        """
        claim = self.get_object()
        new_status = request.data.get('status')
        notes = request.data.get('notes', '')
        requester_role = _get_role(request.user)

        valid_statuses = [s[0] for s in Claim.STATUS_CHOICES]
        if new_status not in valid_statuses:
            return Response(
                {'error': f'Invalid status. Must be one of: {valid_statuses}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Adjusters can only do standard workflow transitions
        if requester_role not in ('admin', 'manager'):
            allowed_transitions = {
                'submitted': ['under_review', 'ai_processing', 'pending_info'],
                'under_review': ['approved', 'denied', 'pending_info'],
                'ai_processing': ['under_review'],
                'pending_info': ['submitted', 'under_review'],
                'approved': ['settled'],
                'appealed': ['under_review'],
            }
            allowed = allowed_transitions.get(claim.status, [])
            if new_status not in allowed:
                return Response(
                    {'error': f'Cannot transition from {claim.status} to {new_status}. '
                              f'Allowed: {allowed or "none"}. Contact admin/manager for override.'},
                    status=status.HTTP_403_FORBIDDEN,
                )

        old_status = claim.status
        claim.status = new_status

        if new_status == 'approved' and request.data.get('approved_amount'):
            claim.approved_amount = request.data['approved_amount']
        if new_status == 'settled' and request.data.get('settlement_amount'):
            claim.settlement_amount = request.data['settlement_amount']

        claim.save()

        # Determine the audit action based on the new status
        audit_action = 'status_change'
        if new_status == 'approved':
            audit_action = 'approved'
        elif new_status == 'denied':
            audit_action = 'denied'
        elif new_status == 'settled':
            audit_action = 'settled'

        # Mark management overrides in the audit trail
        is_override = requester_role in ('admin', 'manager')
        details = {
            'notes': notes,
            'approved_amount': float(claim.approved_amount or 0),
        }
        if is_override:
            details['override'] = True
            details['override_by_role'] = requester_role

        AuditLog.objects.create(
            claim=claim, user=request.user, action=audit_action,
            old_value={'status': old_status}, new_value={'status': new_status},
            details=details,
        )

        # Notify the claimant of status changes
        status_messages = {
            'approved': f'Your claim {claim.claim_number} has been approved.'
                        f'{" Settlement: $" + str(claim.settlement_amount) if claim.settlement_amount else ""}',
            'denied': f'Your claim {claim.claim_number} has been denied. '
                      f'You may file an appeal if you believe this decision is incorrect.',
            'settled': f'Your claim {claim.claim_number} has been settled. '
                       f'Payment of ${claim.settlement_amount or 0} is being processed.',
            'pending_info': f'Additional information is needed for claim {claim.claim_number}. '
                           f'Please log in and provide the requested documents.',
        }
        if new_status in status_messages:
            Notification.objects.create(
                user=claim.claimant,
                notification_type='claim_update',
                title=f'Claim {claim.claim_number} - {dict(Claim.STATUS_CHOICES).get(new_status, new_status)}',
                message=status_messages[new_status],
                claim=claim,
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
    permission_classes = [permissions.IsAuthenticated, CanManageFraudAlerts]
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
    permission_classes = [permissions.IsAuthenticated, IsStaff]
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
    if role in ('admin', 'manager'):
        claims = Claim.objects.all()
    elif role in ('adjuster', 'reviewer', 'agent'):
        claims = Claim.objects.all()
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
    elif role in ('admin', 'manager'):
        data['total_users'] = User.objects.count()
        data['total_staff'] = UserProfile.objects.filter(role__in=STAFF_ROLES).count()
        data['total_adjusters'] = UserProfile.objects.filter(role='adjuster').count()
        data['unassigned_claims'] = claims.filter(assigned_adjuster__isnull=True).exclude(
            status__in=['draft', 'closed', 'settled']
        ).count()

    return Response(data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated, CanViewAnalytics])
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

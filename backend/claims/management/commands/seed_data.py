"""Seed the database with demo data for development."""
import random
from datetime import date, timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from claims.models import (
    UserProfile, InsurancePolicy, Claim, ClaimNote, Notification,
    FraudAlert, AuditLog,
)


class Command(BaseCommand):
    help = 'Seed the database with demo data'

    def add_arguments(self, parser):
        parser.add_argument('--noinput', action='store_true')

    def handle(self, *args, **options):
        # Check if basic seeding is truly complete (admin + profile + at least one policy)
        basic_seeded = (User.objects.filter(username='admin').exists()
                        and UserProfile.objects.filter(user__username='admin').exists()
                        and InsurancePolicy.objects.exists())

        if basic_seeded:
            self.stdout.write('Basic data already seeded.')
            # Still seed fraud alerts, notifications, audit logs if missing
            admin = User.objects.get(username='admin')
            adjusters = list(User.objects.filter(profile__role='adjuster'))
            if not FraudAlert.objects.exists():
                self._seed_fraud_alerts(admin)
            if not Notification.objects.exists():
                self._seed_notifications(admin, adjusters)
            if not AuditLog.objects.exists():
                self._seed_audit_logs(admin, adjusters)
            self._backfill_processing_logs()
            return

        self.stdout.write('Seeding database...')

        # Create admin user (get_or_create to handle partial previous runs)
        admin, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@insurance.com',
                'first_name': 'System',
                'last_name': 'Admin',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        if created:
            admin.set_password('admin123')
            admin.save()
        UserProfile.objects.get_or_create(user=admin, defaults={'role': 'admin', 'department': 'IT'})

        # Create adjusters
        adjusters = []
        adjuster_names = [
            ('Sarah', 'Mitchell'), ('James', 'Rodriguez'), ('Emily', 'Chen'),
        ]
        for first, last in adjuster_names:
            u, created = User.objects.get_or_create(
                username=f'{first.lower()}.{last.lower()}',
                defaults={
                    'email': f'{first.lower()}.{last.lower()}@insurance.com',
                    'first_name': first, 'last_name': last,
                }
            )
            if created:
                u.set_password('password123')
                u.save()
            UserProfile.objects.get_or_create(user=u, defaults={'role': 'adjuster', 'department': 'Claims'})
            adjusters.append(u)

        # Create customers with policies and claims
        customers_data = [
            ('Ema', 'Johnson'), ('Michael', 'Smith'), ('Lisa', 'Wang'),
            ('Robert', 'Brown'), ('Jennifer', 'Davis'), ('David', 'Wilson'),
            ('Maria', 'Garcia'), ('Thomas', 'Anderson'), ('Susan', 'Taylor'),
            ('Christopher', 'Martin'),
        ]

        vehicles = [
            '2022 Honda City', '2023 Toyota Camry', '2021 Ford F-150',
            '2022 Tesla Model 3', '2020 BMW 3 Series', '2023 Hyundai Sonata',
            '2021 Chevrolet Malibu', '2022 Nissan Altima', '2023 Kia K5',
            '2022 Subaru Outback',
        ]

        loss_descriptions = [
            'Rear-ended by another driver at a red light, resulting in bumper damage and mild whiplash.',
            'Side collision at intersection, significant door damage on passenger side.',
            'Tree branch fell on vehicle during storm, windshield and roof damage.',
            'Hit-and-run in parking lot, scratches and dent on driver side.',
            'Multi-vehicle pileup on highway due to fog, front-end damage.',
            'Backed into a pole in parking garage, rear bumper and taillight damage.',
            'Deer collision on rural road, front bumper and hood damage.',
            'Hail damage during severe thunderstorm, multiple dents on body.',
            'Theft of catalytic converter from parked vehicle.',
            'Vandalism - keyed paint on all four sides of vehicle.',
        ]

        loss_types = ['collision', 'collision', 'comprehensive', 'collision',
                      'collision', 'collision', 'comprehensive', 'weather',
                      'theft', 'vandalism']

        statuses = ['submitted', 'under_review', 'ai_processing', 'approved',
                    'denied', 'settled', 'pending_info', 'approved', 'submitted', 'under_review']

        for i, (first, last) in enumerate(customers_data):
            u, created = User.objects.get_or_create(
                username=f'{first.lower()}.{last.lower()}',
                defaults={
                    'email': f'{first.lower()}@example.com',
                    'first_name': first, 'last_name': last,
                }
            )
            if created:
                u.set_password('password123')
                u.save()
            UserProfile.objects.get_or_create(user=u, defaults={'role': 'customer'})

            policy = InsurancePolicy.objects.create(
                policy_number=f'POL-{100000 + i}',
                holder=u,
                policy_type='auto',
                status='active',
                premium_amount=Decimal(str(random.randint(800, 2500))),
                deductible_amount=Decimal(str(random.choice([250, 500, 750, 1000]))),
                coverage_limit=Decimal(str(random.choice([25000, 50000, 75000, 100000]))),
                effective_date=date.today() - timedelta(days=random.randint(30, 365)),
                expiry_date=date.today() + timedelta(days=random.randint(30, 365)),
                vehicle_details={'make_model': vehicles[i], 'year': vehicles[i][:4]},
            )

            cost = Decimal(str(random.randint(500, 15000)))
            claim = Claim.objects.create(
                policy=policy,
                claimant=u,
                assigned_adjuster=random.choice(adjusters) if statuses[i] != 'submitted' else None,
                status=statuses[i],
                priority=random.choice(['low', 'medium', 'high', 'urgent']),
                loss_type=loss_types[i],
                date_of_loss=date.today() - timedelta(days=random.randint(1, 60)),
                loss_description=loss_descriptions[i],
                estimated_repair_cost=cost,
                vehicle_details={'make_model': vehicles[i]},
                third_party_involved=random.choice([True, False]),
                fraud_score=round(random.uniform(0.01, 0.95), 2) if i % 3 == 0 else None,
            )

            if statuses[i] in ('approved', 'settled'):
                claim.approved_amount = cost * Decimal('0.85')
                claim.deductible_applied = policy.deductible_amount
                claim.settlement_amount = max(
                    Decimal('0'),
                    claim.approved_amount - claim.deductible_applied
                )
                claim.ai_recommendation = {
                    'policy_section': 'Collision Coverage',
                    'recommendation_summary': 'Claim covered under standard collision policy.',
                    'deductible': float(policy.deductible_amount),
                    'settlement_amount': float(claim.settlement_amount),
                }
                claim.ai_processing_log = self._generate_processing_log()
                claim.save()

            ClaimNote.objects.create(
                claim=claim, author=admin,
                content=f'Claim {claim.claim_number} received and logged in system.',
                is_ai_generated=False,
            )

        # Create a demo/test user
        demo, created = User.objects.get_or_create(
            username='demo',
            defaults={
                'email': 'demo@insurance.com',
                'first_name': 'Demo', 'last_name': 'User',
            }
        )
        if created:
            demo.set_password('demo123')
            demo.save()
        UserProfile.objects.get_or_create(user=demo, defaults={'role': 'adjuster', 'department': 'Claims'})

        # Seed fraud alerts if none exist
        if not FraudAlert.objects.exists():
            self._seed_fraud_alerts(admin)

        # Seed notifications if none exist
        if not Notification.objects.exists():
            self._seed_notifications(admin, adjusters)

        # Seed audit logs if none exist
        if not AuditLog.objects.exists():
            self._seed_audit_logs(admin, adjusters)

        # Backfill processing logs for approved/settled claims
        self._backfill_processing_logs()

        self.stdout.write(self.style.SUCCESS(
            f'Seeded: 1 admin, 3 adjusters, {len(customers_data)} customers with policies and claims, '
            f'1 demo user, fraud alerts, notifications, audit logs'
        ))

    def _seed_fraud_alerts(self, admin):
        """Create sample fraud alerts for claims with fraud scores."""
        claims_with_fraud = Claim.objects.filter(fraud_score__isnull=False).order_by('-fraud_score')
        alert_templates = [
            {
                'alert_type': 'Duplicate Claim Pattern',
                'description': 'Multiple claims filed for similar incidents within a short time period. '
                               'Pattern analysis detected overlapping loss descriptions and dates.',
                'severity': 'high',
                'indicators': ['Multiple claims in 30-day window', 'Similar loss descriptions', 'Same vehicle involved'],
            },
            {
                'alert_type': 'Inflated Repair Estimate',
                'description': 'Estimated repair cost significantly exceeds typical costs for the reported damage type. '
                               'Cost is 2.3x the regional average for similar repairs.',
                'severity': 'medium',
                'indicators': ['Cost exceeds regional average by >200%', 'Single repair shop estimate', 'No photos submitted'],
            },
            {
                'alert_type': 'Inconsistent Loss Details',
                'description': 'Discrepancies found between the reported incident details and available evidence. '
                               'Police report timing does not align with claimed sequence of events.',
                'severity': 'critical',
                'indicators': ['Timeline inconsistency', 'Conflicting witness statements', 'Delayed reporting (>72h)'],
            },
            {
                'alert_type': 'Suspicious Claim Timing',
                'description': 'Claim filed shortly after policy activation or coverage increase. '
                               'Policy was upgraded 5 days before the reported incident.',
                'severity': 'high',
                'indicators': ['Claim within 14 days of policy start', 'Recent coverage increase', 'New customer'],
            },
            {
                'alert_type': 'Known Fraud Ring Association',
                'description': 'Claimant address and repair shop match patterns associated with a known fraud ring '
                               'in the metropolitan area. Cross-reference with SIU database flagged this connection.',
                'severity': 'critical',
                'indicators': ['Address matches fraud ring', 'Same repair shop as flagged claims', 'Shared phone number pattern'],
            },
        ]

        statuses = ['open', 'open', 'investigating', 'open', 'resolved']

        for i, claim in enumerate(claims_with_fraud[:5]):
            template = alert_templates[i % len(alert_templates)]
            confidence = max(0.5, min(0.99, (claim.fraud_score or 0.5) + random.uniform(-0.1, 0.1)))
            alert = FraudAlert.objects.create(
                claim=claim,
                severity=template['severity'],
                status=statuses[i],
                alert_type=template['alert_type'],
                description=template['description'],
                indicators=template['indicators'],
                ai_confidence=round(confidence, 2),
                reviewed_by=admin if statuses[i] == 'resolved' else None,
                resolution_notes='Investigated and found legitimate after manual review.' if statuses[i] == 'resolved' else '',
                resolved_at=timezone.now() if statuses[i] == 'resolved' else None,
            )
        self.stdout.write(f'  Created {min(5, claims_with_fraud.count())} fraud alerts')

    def _seed_notifications(self, admin, adjusters):
        """Create sample notifications for users."""
        all_claims = list(Claim.objects.all()[:10])
        notif_data = [
            # Admin notifications
            {'user': admin, 'type': 'fraud_alert', 'title': 'New Critical Fraud Alert',
             'message': 'A critical fraud alert has been generated for a recent claim. Immediate review recommended.'},
            {'user': admin, 'type': 'system', 'title': 'Daily Claims Summary',
             'message': f'Today\'s summary: {Claim.objects.count()} total claims, '
                        f'{Claim.objects.filter(status="submitted").count()} new submissions pending review.'},
            {'user': admin, 'type': 'claim_update', 'title': 'High-Value Claim Submitted',
             'message': 'A new claim exceeding $10,000 has been submitted and requires priority assignment.'},
        ]

        # Adjuster notifications
        for adj in adjusters:
            notif_data.extend([
                {'user': adj, 'type': 'assignment', 'title': 'New Claim Assigned',
                 'message': f'You have been assigned a new claim for review. Please check your queue.'},
                {'user': adj, 'type': 'claim_update', 'title': 'Claim Status Updated',
                 'message': 'A claim in your queue has been updated with new information from the claimant.'},
            ])

        # Customer notifications
        for claim in all_claims[:5]:
            notif_data.append({
                'user': claim.claimant, 'type': 'claim_update',
                'title': f'Update on Claim {claim.claim_number}',
                'message': f'Your claim {claim.claim_number} status has been updated to: {claim.get_status_display()}.',
            })

        for nd in notif_data:
            claim = random.choice(all_claims) if all_claims else None
            Notification.objects.create(
                user=nd['user'],
                notification_type=nd['type'],
                title=nd['title'],
                message=nd['message'],
                claim=claim,
                is_read=random.choice([True, False]),
            )
        self.stdout.write(f'  Created {len(notif_data)} notifications')

    def _seed_audit_logs(self, admin, adjusters):
        """Create sample audit log entries."""
        claims = list(Claim.objects.all()[:10])
        for claim in claims:
            # Created log
            AuditLog.objects.create(
                claim=claim, user=claim.claimant, action='created',
                details={'source': 'web_portal'},
            )
            # Status change logs
            if claim.status != 'submitted':
                adjuster = claim.assigned_adjuster or random.choice(adjusters)
                AuditLog.objects.create(
                    claim=claim, user=adjuster, action='assigned',
                    details={'assigned_to': adjuster.get_full_name()},
                )
                AuditLog.objects.create(
                    claim=claim, user=adjuster, action='status_change',
                    details={'from': 'submitted', 'to': claim.status},
                    old_value={'status': 'submitted'},
                    new_value={'status': claim.status},
                )
            if claim.fraud_score is not None:
                AuditLog.objects.create(
                    claim=claim, user=None, action='fraud_check',
                    details={'fraud_score': float(claim.fraud_score), 'agent': 'FraudDetector'},
                )
            if claim.status in ('approved', 'settled'):
                AuditLog.objects.create(
                    claim=claim, user=claim.assigned_adjuster or admin, action='approved',
                    details={'approved_amount': float(claim.approved_amount or 0)},
                )
        self.stdout.write(f'  Created audit logs for {len(claims)} claims')

    def _generate_processing_log(self):
        """Generate a realistic AI processing pipeline log."""
        import time
        base_ts = time.time() - random.randint(3600, 86400)
        return [
            {
                'step': 'claim_parsing',
                'agent': 'ClaimParser',
                'status': 'completed',
                'duration_ms': random.randint(800, 2500),
                'result_summary': 'Extracted claim details and identified loss type',
                'timestamp': base_ts,
            },
            {
                'step': 'policy_query_generation',
                'agent': 'PolicyRetriever',
                'status': 'completed',
                'duration_ms': random.randint(500, 1500),
                'result_summary': 'Generated 3 policy queries for RAG retrieval',
                'timestamp': base_ts + 3,
            },
            {
                'step': 'policy_retrieval',
                'agent': 'PolicyRetriever',
                'status': 'completed',
                'duration_ms': random.randint(1000, 3000),
                'result_summary': 'Retrieved relevant policy sections from vector store',
                'timestamp': base_ts + 6,
            },
            {
                'step': 'fraud_detection',
                'agent': 'FraudDetector',
                'status': 'completed',
                'duration_ms': random.randint(1200, 4000),
                'result_summary': f'Fraud score: {random.randint(5, 35)}% - Low risk',
                'timestamp': base_ts + 10,
            },
            {
                'step': 'recommendation_generation',
                'agent': 'RecommendationAgent',
                'status': 'completed',
                'duration_ms': random.randint(2000, 5000),
                'result_summary': 'Generated coverage recommendation with settlement calculation',
                'timestamp': base_ts + 15,
            },
            {
                'step': 'decision_finalization',
                'agent': 'DecisionMaker',
                'status': 'completed',
                'duration_ms': random.randint(1500, 3500),
                'result_summary': 'Final decision: Approve with standard deductible applied',
                'timestamp': base_ts + 20,
            },
        ]

    def _backfill_processing_logs(self):
        """Add processing logs to approved/settled claims that are missing them."""
        claims = Claim.objects.filter(
            status__in=['approved', 'settled'],
            ai_recommendation__isnull=False,
        )
        updated = 0
        for claim in claims:
            if not claim.ai_processing_log:
                claim.ai_processing_log = self._generate_processing_log()
                claim.save(update_fields=['ai_processing_log'])
                updated += 1
        if updated:
            self.stdout.write(f'  Backfilled processing logs for {updated} claims')

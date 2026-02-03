"""Seed the database with demo data for development."""
import random
from datetime import date, timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from claims.models import (
    UserProfile, InsurancePolicy, Claim, ClaimNote, Notification,
)


class Command(BaseCommand):
    help = 'Seed the database with demo data'

    def add_arguments(self, parser):
        parser.add_argument('--noinput', action='store_true')

    def handle(self, *args, **options):
        # Check if seeding is truly complete (admin + profile + at least one policy)
        if (User.objects.filter(username='admin').exists()
                and UserProfile.objects.filter(user__username='admin').exists()
                and InsurancePolicy.objects.exists()):
            self.stdout.write('Data already seeded, skipping.')
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

        self.stdout.write(self.style.SUCCESS(
            f'Seeded: 1 admin, 3 adjusters, {len(customers_data)} customers with policies and claims, 1 demo user'
        ))

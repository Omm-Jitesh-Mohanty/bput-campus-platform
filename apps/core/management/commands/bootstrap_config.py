"""
Bootstrap config tables with defaults if empty.
Safe to run on a fresh DB — idempotent.

Usage:
    python manage.py bootstrap_config
    python manage.py bootstrap_config --force   # re-seed even if not empty
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from django.core.management import call_command

from apps.core.models import (
    Department, PriorityLevel, TicketType, SLAPolicy,
    SystemSetting, AIPromptTemplate, NotificationTemplate,
)


class Command(BaseCommand):
    help = 'Seed config tables if they are empty.'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true',
                            help='Reseed even if tables are non-empty')

    def handle(self, *args, **options):
        force = options['force']

        checks = {
            'Departments': Department.objects.count(),
            'Priorities': PriorityLevel.objects.count(),
            'Ticket types': TicketType.objects.count(),
            'SLA policies': SLAPolicy.objects.count(),
            'Settings': SystemSetting.objects.count(),
            'AI prompts': AIPromptTemplate.objects.count(),
            'Notification templates': NotificationTemplate.objects.count(),
        }

        self.stdout.write('Config table counts:')
        for name, count in checks.items():
            self.stdout.write(f'  {name}: {count}')

        all_empty = all(c == 0 for c in checks.values())

        if not all_empty and not force:
            self.stdout.write(self.style.WARNING(
                '\nSome tables have data. Use --force to reseed anyway.'
            ))
            return

        if force:
            with transaction.atomic():
                SLAPolicy.objects.all().delete()
                TicketType.objects.all().delete()
                PriorityLevel.objects.all().delete()
                Department.objects.all().delete()
                SystemSetting.objects.all().delete()
                AIPromptTemplate.objects.all().delete()
                NotificationTemplate.objects.all().delete()

        self.stdout.write('\nRunning data migration...')
        call_command('migrate', 'core', verbosity=1)

        self.stdout.write(self.style.SUCCESS('\n✓ Config bootstrapped.'))
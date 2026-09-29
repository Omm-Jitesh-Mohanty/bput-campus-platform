"""
Verify the system is ready for a demo.

Run 15 minutes before the pitch:
    python manage.py demo_check

Exits with code 0 if all clear, 1 if any check fails.
"""
import os
import socket
import subprocess
import sys

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Verify demo readiness.'

    def handle(self, *args, **options):
        self.stdout.write('\n🎯 Demo Readiness Check\n')
        self.stdout.write('=' * 50 + '\n')

        checks = [
            ('Database connection', self._check_db),
            ('Config tables populated', self._check_config),
            ('Demo users exist', self._check_users),
            ('Tickets for demo', self._check_tickets),
            ('Ollama server reachable', self._check_ollama),
            ('Ollama model loaded', self._check_ollama_model),
            ('Redis reachable', self._check_redis),
            ('LibreOffice available', self._check_libreoffice),
            ('Static files present', self._check_static),
            ('DEBUG mode', self._check_debug),
        ]

        failures = []
        for name, check in checks:
            try:
                ok, msg = check()
                symbol = '✅' if ok else '❌'
                self.stdout.write(f'  {symbol} {name}: {msg}')
                if not ok:
                    failures.append(name)
            except Exception as e:
                self.stdout.write(f'  ❌ {name}: {e}')
                failures.append(name)

        self.stdout.write('\n' + '=' * 50)
        if failures:
            self.stdout.write(self.style.ERROR(
                f'\n❌ {len(failures)} check(s) failed:\n  - ' +
                '\n  - '.join(failures) + '\n'
            ))
            sys.exit(1)
        else:
            self.stdout.write(self.style.SUCCESS(
                '\n✅ All checks passed. Ready to demo.\n'
            ))

    # =================================================================
    def _check_db(self):
        with connection.cursor() as c:
            c.execute('SELECT 1')
        return True, 'connected'

    def _check_config(self):
        from apps.core.models import Department, TicketType, PriorityLevel, SLAPolicy
        depts = Department.objects.count()
        tts = TicketType.objects.count()
        prios = PriorityLevel.objects.count()
        slas = SLAPolicy.objects.count()
        ok = depts > 0 and tts > 0 and prios > 0 and slas > 0
        return ok, f'{depts} depts, {tts} types, {prios} priorities, {slas} SLAs'

    def _check_users(self):
        students = User.objects.filter(role='student').count()
        admins = User.objects.exclude(role='student').count()
        ok = students >= 5 and admins >= 3
        return ok, f'{students} students, {admins} admins'

    def _check_tickets(self):
        from apps.tickets.models import CampusTicket
        pending = CampusTicket.objects.filter(status='pending').count()
        overdue = sum(
            1 for t in CampusTicket.objects.filter(status='pending')
            if t.age_hours > 48
        )
        ok = pending >= 3
        return ok, f'{pending} pending, {overdue} overdue'

    def _check_ollama(self):
        import requests
        url = settings.OLLAMA_URL.replace('/api/generate', '/api/tags')
        try:
            r = requests.get(url, timeout=3)
            ok = r.status_code == 200
            return ok, f'HTTP {r.status_code}'
        except Exception as e:
            return False, f'unreachable: {e}'

    def _check_ollama_model(self):
        import requests
        url = settings.OLLAMA_URL.replace('/api/generate', '/api/tags')
        try:
            r = requests.get(url, timeout=3)
            models = [m['name'] for m in r.json().get('models', [])]
            target = settings.OLLAMA_MODEL
            ok = any(target.split(':')[0] in m for m in models)
            return ok, f'model "{target}" loaded' if ok else f'available: {models}'
        except Exception as e:
            return False, str(e)

    def _check_redis(self):
        try:
            import redis
            r = redis.from_url(settings.REDIS_URL)
            r.ping()
            return True, 'PONG'
        except ImportError:
            return False, 'redis-py not installed (optional)'
        except Exception as e:
            return False, f'unreachable: {e}'

    # def _check_libreoffice(self):
    #     try:
    #         result = subprocess.run(
    #             ['soffice', '--version'],
    #             capture_output=True, timeout=15, check=False,
    #         )
    #         if result.returncode == 0:
    #             version = result.stdout.decode().strip().split('\n')[0]
    #             return True, version
    #         return False, f'exit code {result.returncode}'
    #     except FileNotFoundError:
    #         return False, 'not in PATH (reportlab fallback will be used)'
    #     except Exception as e:
    #         return False, str(e)
    def _check_libreoffice(self):
        import shutil

        try:
            soffice = shutil.which('soffice')

            if not soffice:
                return False, 'not in PATH (reportlab fallback will be used)'

            return True, f'available: {soffice}'

        except Exception as e:
            return False, str(e)

    def _check_static(self):
        from pathlib import Path
        css = Path(settings.BASE_DIR) / 'static' / 'css' / 'design-system.css'
        js = Path(settings.BASE_DIR) / 'static' / 'js' / 'ws_client.js'
        ok = css.exists() and js.exists()
        return ok, 'design-system.css + ws_client.js' if ok else 'missing files'

    def _check_debug(self):
        ok = settings.DEBUG
        return ok, 'DEBUG=True (dev)' if ok else 'DEBUG=False (production!)'
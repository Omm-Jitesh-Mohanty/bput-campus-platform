"""
Benchmark key pages for demo readiness.

Run: python scripts/benchmark_pages.py
"""
# import os
# import time

# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')

# import django
# django.setup()
import os
import sys
import time

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ.setdefault(
    'DJANGO_SETTINGS_MODULE',
    'config.settings.dev',
)

import django
django.setup()

from django.test import Client
from apps.accounts.models import User


PAGES = [
    ('Student dashboard', '/dashboard/'),
    ('Attendance', '/attendance/'),
    ('Timetable', '/attendance/timetable/'),
    ('My requests', '/tickets/'),
    ('Notices', '/notices/'),
    ('Admin dashboard', '/dashboard/admin/'),
    ('Analytics', '/dashboard/analytics/'),
    ('Manage panel', '/manage/'),
    ('Departments', '/manage/departments/'),
    ('SLA matrix', '/manage/slas/'),
]


def main():
    # Login as warden (has access to most pages)
    client = Client()
    user = User.objects.filter(role='warden').first()
    if not user:
        print("No warden user found. Run `python manage.py reset_demo` first.")
        return

    user.set_password('demo1234')
    user.save()
    client.login(username=user.username, password='demo1234')

    print(f"\n⏱  Benchmarking as {user.username}\n")
    print(f"{'Page':<30} {'Time':>10} {'Status':>8}")
    print('-' * 50)

    slow_pages = []

    for name, url in PAGES:
        start = time.time()
        try:
            response = client.get(url)
            elapsed = (time.time() - start) * 1000  # ms
            status = response.status_code
            symbol = '🐢' if elapsed > 1500 else '⚡' if elapsed < 300 else '  '
            print(f"{name:<30} {elapsed:>8.0f} ms {status:>6} {symbol}")
            if elapsed > 1500:
                slow_pages.append((name, elapsed))
        except Exception as e:
            print(f"{name:<30} ERROR: {e}")

    print()
    if slow_pages:
        print("🐢 Slow pages (>1.5s):")
        for name, ms in slow_pages:
            print(f"  - {name}: {ms:.0f}ms")
        print("\nConsider caching or optimizing these.")
    else:
        print("✅ All pages fast enough for demo.")


if __name__ == '__main__':
    main()
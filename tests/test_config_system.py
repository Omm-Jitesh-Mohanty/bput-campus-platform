"""Tests for the config-driven system."""
from django.test import TestCase
from apps.core.models import Department, TicketType, PriorityLevel, SLAPolicy
from apps.core.services import ConfigService


class ConfigSystemTests(TestCase):

    def test_route_to_department(self):
        Department.objects.create(
            code='test_plumbing',
            name='Test Plumbing',
            routing_keywords=['faucet', 'dripping'],
            auto_route_enabled=True,
        )
        d = ConfigService.route_to_department('the faucet is dripping')
        self.assertIsNotNone(d)
        self.assertEqual(d.code, 'test_plumbing')

    def test_sla_lookup(self):
        tt = TicketType.objects.create(code='test_complaint', name='Test',
                                       sla_hours=24)
        prio = PriorityLevel.objects.create(code='test_urgent', name='Test Urgent',
                                            weight=100)
        SLAPolicy.objects.create(
            ticket_type=tt, priority=prio,
            green_hours=4, yellow_hours=8, red_hours=24,
        )

        sla = ConfigService.sla_hours_for('test_complaint', 'test_urgent')
        self.assertEqual(sla['green'], 4)
        self.assertEqual(sla['red'], 24)

    def test_setting_retrieval(self):
        from apps.core.models import SystemSetting
        SystemSetting.objects.update_or_create(
            key='test.key',
            defaults={'value': 42, 'value_type': 'integer'},
        )
        self.assertEqual(ConfigService.get_setting('test.key'), 42)
        self.assertEqual(ConfigService.get_setting('missing.key', 'default'), 'default')
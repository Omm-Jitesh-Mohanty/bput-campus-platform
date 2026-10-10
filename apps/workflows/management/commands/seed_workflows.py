"""
Seed realistic workflows for various ticket types and complaint subtypes.
Run: python manage.py seed_workflows
"""
from django.core.management.base import BaseCommand

from apps.core.models import TicketType, ComplaintSubtype, Department
from apps.workflows.models import Workflow, WorkflowStep


class Command(BaseCommand):
    help = 'Create realistic workflows for campus operations.'

    def handle(self, *args, **options):
        # Clear existing workflows to avoid duplicates
        Workflow.objects.all().delete()

        # Get ticket types
        complaint_tt = TicketType.objects.filter(code='complaint').first()
        leave_tt = TicketType.objects.filter(code='leave').first()
        doc_tt = TicketType.objects.filter(code='document').first()
        gatepass_tt = TicketType.objects.filter(code='gatepass').first()

        # ============================================================
        # 1. MAINTENANCE COMPLAINTS — lightweight
        # ============================================================
        wf_maint, _ = Workflow.objects.get_or_create(
            code='maintenance_chain',
            defaults={
                'name': 'Maintenance Complaint Chain',
                'description': 'For electrical/plumbing/civil repairs. Fast-track.',
                'is_active': True,
            }
        )
        WorkflowStep.objects.get_or_create(workflow=wf_maint, order=1, defaults={
            'name': 'Maintenance Review',
            'role_required': 'lab_asst',
            'action_type': 'review',
            'instructions': 'Verify the issue. Estimate time and parts needed.',
            'can_skip': False,
        })
        WorkflowStep.objects.get_or_create(workflow=wf_maint, order=2, defaults={
            'name': 'HOD Approval',
            'role_required': 'hod',
            'action_type': 'approve',
            'instructions': 'Approve maintenance work.',
        })
        WorkflowStep.objects.get_or_create(workflow=wf_maint, order=3, defaults={
            'name': 'Cost Sanction (if > ₹5,000)',
            'role_required': 'dean',
            'action_type': 'sign',
            'can_skip': True,
            'condition': {
                'field': 'dynamic_data.estimated_cost',
                'operator': '>',
                'value': 5000,
            },
        })

        # ============================================================
        # 2. BEHAVIORAL COMPLAINTS — escalation chain
        # ============================================================
        wf_behav, _ = Workflow.objects.get_or_create(
            code='behavioral_chain',
            defaults={
                'name': 'Behavioral Complaint Chain',
                'description': 'Classroom/discipline issues. Multi-level review.',
                'is_active': True,
            }
        )
        WorkflowStep.objects.get_or_create(workflow=wf_behav, order=1, defaults={
            'name': 'Class Coordinator Review',
            'role_required': 'asst_prof',
            'action_type': 'review',
            'instructions': 'Verify the incident. Collect statements from witnesses.',
        })
        WorkflowStep.objects.get_or_create(workflow=wf_behav, order=2, defaults={
            'name': 'HOD Review',
            'role_required': 'hod',
            'action_type': 'review',
            'instructions': 'Evaluate severity and recommend action.',
        })
        WorkflowStep.objects.get_or_create(workflow=wf_behav, order=3, defaults={
            'name': 'Dean (Student Welfare) Decision',
            'role_required': 'dean',
            'action_type': 'approve',
            'instructions': 'Take final disciplinary action.',
        })
        WorkflowStep.objects.get_or_create(workflow=wf_behav, order=4, defaults={
            'name': 'Principal Notification',
            'role_required': 'principal',
            'action_type': 'notify',
            'instructions': 'Inform Principal of the resolution.',
        })

        # ============================================================
        # 3. FEE / ACCOUNTS COMPLAINTS
        # ============================================================
        wf_fees, _ = Workflow.objects.get_or_create(
            code='fee_chain',
            defaults={
                'name': 'Fee / Accounts Chain',
                'description': 'For fee refunds, corrections, scholarship issues.',
                'is_active': True,
            }
        )
        WorkflowStep.objects.get_or_create(workflow=wf_fees, order=1, defaults={
            'name': 'AO Verification',
            'role_required': 'ao',
            'action_type': 'verify',
            'instructions': 'Verify the account details and history.',
        })
        WorkflowStep.objects.get_or_create(workflow=wf_fees, order=2, defaults={
            'name': 'Dean Approval',
            'role_required': 'dean',
            'action_type': 'approve',
        })
        WorkflowStep.objects.get_or_create(workflow=wf_fees, order=3, defaults={
            'name': 'Principal Sanction',
            'role_required': 'principal',
            'action_type': 'sign',
            'condition': {
                'field': 'dynamic_data.amount',
                'operator': '>',
                'value': 10000,
            },
            'can_skip': True,
        })

        # ============================================================
        # 4. HOSTEL FACILITY COMPLAINTS
        # ============================================================
        wf_hostel, _ = Workflow.objects.get_or_create(
            code='hostel_chain',
            defaults={
                'name': 'Hostel Facility Chain',
                'description': 'Room, water, electricity issues in hostel.',
                'is_active': True,
            }
        )
        WorkflowStep.objects.get_or_create(workflow=wf_hostel, order=1, defaults={
            'name': 'Warden Review',
            'role_required': 'warden',
            'action_type': 'review',
        })
        WorkflowStep.objects.get_or_create(workflow=wf_hostel, order=2, defaults={
            'name': 'Maintenance Team Action',
            'role_required': 'lab_asst',
            'action_type': 'review',
        })
        WorkflowStep.objects.get_or_create(workflow=wf_hostel, order=3, defaults={
            'name': 'Dean (Student Welfare) Sign-off',
            'role_required': 'dean',
            'action_type': 'approve',
            'can_skip': True,
            'condition': {
                'field': 'dynamic_data.escalation_required',
                'operator': '==',
                'value': True,
            },
        })

        # ============================================================
        # 5. LEAVE — short vs long
        # ============================================================
        if leave_tt:
            wf_leave, _ = Workflow.objects.get_or_create(
                code='leave_chain',
                defaults={
                    'name': 'Leave Approval Chain',
                    'description': 'Warden for short leaves, HOD for longer, Dean for extended.',
                    'ticket_type': leave_tt,
                    'is_active': True,
                }
            )
            WorkflowStep.objects.get_or_create(workflow=wf_leave, order=1, defaults={
                'name': 'Warden Approval',
                'role_required': 'warden',
                'action_type': 'approve',
            })
            WorkflowStep.objects.get_or_create(workflow=wf_leave, order=2, defaults={
                'name': 'HOD Approval (if > 3 days)',
                'role_required': 'hod',
                'action_type': 'approve',
                'condition': {
                    'field': 'dynamic_data.duration_days',
                    'operator': '>',
                    'value': 3,
                },
                'can_skip': True,
            })
            WorkflowStep.objects.get_or_create(workflow=wf_leave, order=3, defaults={
                'name': 'Dean Approval (if > 10 days)',
                'role_required': 'dean',
                'action_type': 'approve',
                'condition': {
                    'field': 'dynamic_data.duration_days',
                    'operator': '>',
                    'value': 10,
                },
                'can_skip': True,
            })

        # ============================================================
        # 6. DOCUMENT / CERTIFICATE
        # ============================================================
        if doc_tt:
            wf_doc, _ = Workflow.objects.get_or_create(
                code='document_chain',
                defaults={
                    'name': 'Certificate Issuance Chain',
                    'description': 'Standard official document approval.',
                    'ticket_type': doc_tt,
                    'is_active': True,
                }
            )
            WorkflowStep.objects.get_or_create(workflow=wf_doc, order=1, defaults={
                'name': 'Clerk Verification',
                'role_required': 'clerk',
                'action_type': 'verify',
                'instructions': 'Check eligibility: fee clearance, attendance.',
            })
            WorkflowStep.objects.get_or_create(workflow=wf_doc, order=2, defaults={
                'name': 'HOD Approval',
                'role_required': 'hod',
                'action_type': 'approve',
            })
            WorkflowStep.objects.get_or_create(workflow=wf_doc, order=3, defaults={
                'name': 'Principal Sign-off',
                'role_required': 'principal',
                'action_type': 'sign',
            })

        # ============================================================
        # 7. GATE PASS
        # ============================================================
        if gatepass_tt:
            wf_gate, _ = Workflow.objects.get_or_create(
                code='gatepass_chain',
                defaults={
                    'name': 'Gate Pass Chain',
                    'description': 'Single-step approval by warden.',
                    'ticket_type': gatepass_tt,
                    'is_active': True,
                }
            )
            WorkflowStep.objects.get_or_create(workflow=wf_gate, order=1, defaults={
                'name': 'Warden Approval',
                'role_required': 'warden',
                'action_type': 'approve',
            })

        # ============================================================
        # 8. Wire subtypes to workflows
        # ============================================================
        subtype_mappings = {
            'electrical_repair': ('Electrical Repair', '🔌', 'maintenance_chain',
                                  ['fan', 'light', 'bulb', 'socket', 'spark', 'wire']),
            'plumbing_repair':   ('Plumbing Issue',    '🚰', 'maintenance_chain',
                                  ['tap', 'leak', 'pipe', 'toilet', 'water']),
            'civil_repair':      ('Civil / Furniture', '🪑', 'maintenance_chain',
                                  ['wall', 'door', 'bench', 'ceiling', 'broken']),
            'wifi_issue':        ('WiFi / Network',    '🌐', 'maintenance_chain',
                                  ['wifi', 'internet', 'network', 'slow net']),
            'mess_quality':      ('Mess Food Quality', '🍽', 'hostel_chain',
                                  ['food', 'mess', 'meal', 'stale', 'taste']),
            'hostel_facility':   ('Hostel Facility',   '🏠', 'hostel_chain',
                                  ['room', 'mattress', 'locker', 'wardrobe']),
            'behavioral':        ('Classroom Behavior','⚖️', 'behavioral_chain',
                                  ['fight', 'quarrel', 'misbehave', 'ragging', 'bully']),
            'academic_grievance':('Academic Issue',    '📚', 'behavioral_chain',
                                  ['marks', 'grade', 'exam', 'teacher', 'unfair']),
            'fee_issue':         ('Fee / Accounts',    '💰', 'fee_chain',
                                  ['fee', 'refund', 'scholarship', 'payment']),
        }

        if complaint_tt:
            for code, (name, icon, wf_code, keywords) in subtype_mappings.items():
                wf = Workflow.objects.filter(code=wf_code).first()
                ComplaintSubtype.objects.update_or_create(
                    code=code,
                    defaults={
                        'name': name,
                        'icon': icon,
                        'parent_ticket_type': complaint_tt,
                        'workflow': wf,
                        'routing_keywords': keywords,
                        'is_active': True,
                    }
                )

        self.stdout.write(self.style.SUCCESS(
            f'\n✓ Seeded {Workflow.objects.count()} workflows with '
            f'{WorkflowStep.objects.count()} steps\n'
            f'✓ Seeded {ComplaintSubtype.objects.count()} complaint subtypes'
        ))
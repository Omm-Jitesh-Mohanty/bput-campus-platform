# # from django.contrib import admin

# # Register your models here.
# from django.contrib import admin
# from django.contrib.auth.admin import UserAdmin
# from .models import User


# @admin.register(User)
# class CustomUserAdmin(UserAdmin):
#     list_display = ('username', 'email', 'role', 'department', 'batch_year', 'is_staff')
#     list_filter = ('role', 'department', 'batch_year', 'is_staff')
#     fieldsets = UserAdmin.fieldsets + (
#         ('Campus Info', {'fields': ('role', 'department', 'batch_year',
#                                     'hostel_block', 'room_number', 'phone', 'language_pref')}),
#     )

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, FeeRecord


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'get_full_name', 'role', 'department',
                    'batch_year', 'hostel_block', 'is_staff')
    list_filter = ('role', 'department', 'batch_year', 'hostel_block', 'is_staff')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'phone')

    fieldsets = BaseUserAdmin.fieldsets + (
        ('Campus Info', {
            'fields': ('role', 'department', 'batch_year',
                       'hostel_block', 'room_number', 'phone',
                       'language_pref', 'has_smartphone'),
        }),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Campus Info', {
            'fields': ('role', 'department', 'batch_year', 'hostel_block'),
        }),
    )


@admin.register(FeeRecord)
class FeeRecordAdmin(admin.ModelAdmin):
    list_display = ('student', 'semester', 'total_dues', 'paid_amount',
                    'pending', 'due_date', 'is_cleared')
    list_filter = ('semester', 'is_cleared', 'due_date')
    search_fields = ('student__username', 'student__first_name', 'student__last_name')
    autocomplete_fields = ('student',)
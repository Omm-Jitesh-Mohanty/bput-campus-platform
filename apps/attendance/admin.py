# from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import AttendanceRecord, Timetable, ClassCancellation


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ('student', 'subject_name', 'attended_classes',
                    'total_classes', 'percentage', 'is_below_threshold')
    list_filter = ('subject_name',)
    search_fields = ('student__username', 'subject_name', 'subject_code')
    autocomplete_fields = ('student',)


@admin.register(Timetable)
class TimetableAdmin(admin.ModelAdmin):
    list_display = ('department', 'batch_year', 'day_of_week', 'time_slot',
                    'subject_name', 'faculty_name', 'room', 'is_cancelled')
    list_filter = ('department', 'batch_year', 'day_of_week', 'is_cancelled')
    search_fields = ('subject_name', 'faculty_name')


@admin.register(ClassCancellation)
class ClassCancellationAdmin(admin.ModelAdmin):
    list_display = ('timetable', 'date', 'reason', 'announced_by')
    list_filter = ('date',)
    date_hierarchy = 'date'
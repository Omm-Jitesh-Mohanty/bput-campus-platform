# from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Feedback


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ('id', 'category', 'rating', 'student', 'is_anonymous', 'created_at')
    list_filter = ('category', 'rating', 'is_anonymous')
    search_fields = ('comments', 'student__username')
    autocomplete_fields = ('student',)
    date_hierarchy = 'created_at'
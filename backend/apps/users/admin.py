from django.contrib import admin

from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "driver", "phone", "is_demo")
    list_filter = ("role", "is_demo")
    search_fields = ("user__username", "phone", "role", "driver__full_name")

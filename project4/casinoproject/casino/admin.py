from django.contrib import admin
from .models import BaccaratResult

@admin.register(BaccaratResult)
class BaccaratResultAdmin(admin.ModelAdmin):
    list_display = ('result', 'created_at')
    list_filter = ('result', 'created_at')
    ordering = ('-created_at',)
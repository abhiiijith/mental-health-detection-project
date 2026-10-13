from django.contrib import admin
from .models import Register, ChatHistory, EmotionLog

admin.site.register(Register)

@admin.register(ChatHistory)
class ChatHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'emotion', 'sentiment', 'created_at')
    list_filter = ('role', 'emotion', 'sentiment')
    search_fields = ('user__name', 'message')

@admin.register(EmotionLog)
class EmotionLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'emotion', 'timestamp')
    list_filter = ('emotion',)
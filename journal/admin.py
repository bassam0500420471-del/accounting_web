from django.contrib import admin
from .models import JournalEntry, JournalLine

admin.site.register(JournalEntry)
admin.site.register(JournalLine)

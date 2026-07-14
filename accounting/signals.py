from django.db.models.signals import post_save
from django.dispatch import receiver
from accounts.models import Company
from accounting.utils_chart import ensure_company_root_accounts


@receiver(post_save, sender=Company)
def create_root_accounts_for_new_company(sender, instance, created, **kwargs):
    if created:
        ensure_company_root_accounts(instance)
from django.db.models.signals import post_save
from django.dispatch import receiver

from accounts.models import Company

from .models import Store, StoreTheme, StoreSetting



@receiver(post_save, sender=Company)
def create_company_store(sender, instance, created, **kwargs):

    if created:

        store = Store.objects.create(

            company=instance,

            name=f"متجر {instance.name}",

            slug=f"store-{instance.id}"

        )


        StoreTheme.objects.create(
            store=store
        )


        StoreSetting.objects.create(
            store=store
        )


@receiver(post_save, sender=Store)
def create_store_defaults(sender, instance, created, **kwargs):

    if created:

        StoreTheme.objects.get_or_create(
            store=instance
        )

        StoreSetting.objects.get_or_create(
            store=instance
        )
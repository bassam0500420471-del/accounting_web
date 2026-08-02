from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0002_account_is_payment_method'),
    ]

    operations = [
        migrations.AlterField(
            model_name='journalentry',
            name='entry_no',
            field=models.PositiveIntegerField(
                verbose_name='رقم القيد'
            ),
        ),
        migrations.AddConstraint(
            model_name='journalentry',
            constraint=models.UniqueConstraint(
                fields=('company', 'entry_no'),
                name='unique_company_entry_no'
            ),
        ),
    ]
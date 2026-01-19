from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('hr', '0005_remove_employee_annual_leave_balance_and_more'),
    ]

    operations = [
        # =================== تفاصيل العمل ===================
        migrations.AddField(
            model_name='employee',
            name='department',
            field=models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, to='hr.department'),
        ),
        migrations.AddField(
            model_name='employee',
            name='branch',
            field=models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, to='hr.branch'),
        ),
        migrations.AddField(
            model_name='employee',
            name='job_title',
            field=models.CharField(max_length=100, blank=True),
        ),
        migrations.AddField(
            model_name='employee',
            name='supervisor',
            field=models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, to='hr.employee'),
        ),

        # =================== الإجازات ===================
        migrations.AddField(
            model_name='employee',
            name='annual_leave_entitlement',
            field=models.IntegerField(default=0, verbose_name='الإجازة السنوية المستحقة'),
        ),
        migrations.AddField(
            model_name='employee',
            name='current_annual_leave',
            field=models.IntegerField(default=0, verbose_name='الإجازة السنوية الحالية'),
        ),
        migrations.AddField(
            model_name='employee',
            name='compensatory_leave',
            field=models.IntegerField(default=0, verbose_name='الإجازات التعويضية'),
        ),
    ]

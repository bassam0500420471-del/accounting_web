from django.db import migrations


def create_missing_table(apps, schema_editor):
    Attachment = apps.get_model("hr", "EvaluationScoreAttachment")

    table_name = Attachment._meta.db_table

    existing_tables = schema_editor.connection.introspection.table_names()

    if table_name not in existing_tables:
        schema_editor.create_model(Attachment)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("hr", "0008_employeerequest"),
    ]

    operations = [
        migrations.RunPython(
            create_missing_table,
            noop_reverse,
        ),
    ]
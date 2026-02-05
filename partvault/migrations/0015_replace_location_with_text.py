from django.db import migrations, models


def copy_location_to_text(apps, schema_editor):
    Item = apps.get_model("partvault", "Item")
    for item in Item.objects.all():
        if item.location_id and item.location:
            item.location_text = item.location.name
            item.save(update_fields=["location_text"])


class Migration(migrations.Migration):
    dependencies = [
        ("partvault", "0014_user_owned_taxonomies"),
    ]

    operations = [
        migrations.AddField(
            model_name="item",
            name="location_text",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.RunPython(copy_location_to_text, migrations.RunPython.noop),
        migrations.RemoveField(model_name="item", name="location"),
        migrations.DeleteModel(name="Location"),
        migrations.RenameField(
            model_name="item",
            old_name="location_text",
            new_name="location",
        ),
    ]

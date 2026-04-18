# Generated migration for adding Kirilcha fields and renaming _kr to _kk

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api_v1', '0008_applicationtarget_name'),
    ]

    operations = [
        # FAQCategory: rename _kr to _kk and add _kir
        migrations.RenameField(
            model_name='faqcategory',
            old_name='name_kr',
            new_name='name_kk',
        ),
        migrations.AddField(
            model_name='faqcategory',
            name='name_kir',
            field=models.CharField(max_length=255, verbose_name='Nomi (Kirilcha)', default=''),
        ),
        # ApplicationTarget: rename _kr to _kk
        migrations.RenameField(
            model_name='applicationtarget',
            old_name='position_kr',
            new_name='position_kk',
        ),
        migrations.RenameField(
            model_name='applicationtarget',
            old_name='agency_kr',
            new_name='agency_kk',
        ),
        migrations.RenameField(
            model_name='applicationtarget',
            old_name='desc_kr',
            new_name='desc_kk',
        ),
        migrations.RenameField(
            model_name='applicationtarget',
            old_name='tags_kr',
            new_name='tags_kk',
        ),
        # ApplicationTarget: add _kir fields
        migrations.AddField(
            model_name='applicationtarget',
            name='position_kir',
            field=models.CharField(max_length=255, verbose_name='Lavozim (Kirilcha)', default=''),
        ),
        migrations.AddField(
            model_name='applicationtarget',
            name='agency_kir',
            field=models.CharField(max_length=255, verbose_name='Tashkilot (Kirilcha)', default=''),
        ),
        migrations.AddField(
            model_name='applicationtarget',
            name='desc_kir',
            field=models.TextField(verbose_name='Tavsif (Kirilcha)', default=''),
        ),
        migrations.AddField(
            model_name='applicationtarget',
            name='tags_kir',
            field=models.TextField(verbose_name='Qidiruv teglari (Kirilcha)', blank=True, default=''),
        ),
        # FAQ: rename _kr to _kk
        migrations.RenameField(
            model_name='faq',
            old_name='question_kr',
            new_name='question_kk',
        ),
        migrations.RenameField(
            model_name='faq',
            old_name='answer_kr',
            new_name='answer_kk',
        ),
        # FAQ: add _kir fields
        migrations.AddField(
            model_name='faq',
            name='question_kir',
            field=models.TextField(verbose_name='Savol (Kirilcha)', default=''),
        ),
        migrations.AddField(
            model_name='faq',
            name='answer_kir',
            field=models.TextField(verbose_name='Javob (Kirilcha)', default=''),
        ),
    ]

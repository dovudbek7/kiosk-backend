"""Seed 10 fake employees across 2 districts + sample messages/rings/visits.

Usage:
    python manage.py seed_fake
    python manage.py seed_fake --reset    # delete previous fakes first

The command creates:
    - 2 districts: oltiariq, boz (if missing) + their admin users
    - 10 ApplicationTarget rows (5 per district), each with a Django User
    - 10 messages, 6 rings, 8 visits, 6 service requests — all district-scoped

All fake phone numbers are in the +99890123XXXX range, so --reset only
removes seeded rows and leaves real data alone.
"""

import random
from datetime import time

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.crypto import get_random_string

from api_v1.models import (
    ApplicationTarget,
    District,
    DistrictAdminProfile,
    KioskVisit,
    Message,
    Ring,
    ServiceRequest,
)


FAKE_PHONE_PREFIX = '+99890123'


SEED_TARGETS = [
    # district_slug, name, phone_tail, type, position, agency
    ('oltiariq', 'Azamat Karimov',   '0001', 'HODIM',     'Dasturchi',     "IT bo'limi"),
    ('oltiariq', 'Dilshod Toirov',   '0002', 'HODIM',     'Buxgalter',     "Moliya bo'limi"),
    ('oltiariq', 'Malika Yusupova',  '0003', 'HODIM',     'Kotiba',        'Qabulxona'),
    ('oltiariq', 'Sardor Aliyev',    '0004', 'TASHKILOT', 'Boshliq',       'Hokimlik apparati'),
    ('oltiariq', 'Nargiza Saidova',  '0005', 'HODIM',     'Yurist',        "Yuridik bo'lim"),

    ('boz',      "Jasur G'ulomov",   '0006', 'HODIM',     'Bosh muhandis', "Qurilish bo'limi"),
    ('boz',      'Feruza Rahimova',  '0007', 'TASHKILOT', 'Direktor',      "Ta'lim bo'limi"),
    ('boz',      'Bekzod Ergashev',  '0008', 'HODIM',     'Inspektor',     "Soliq bo'limi"),
    ('boz',      'Gulnora Soliyeva', '0009', 'HODIM',     'Hamshira',      'Markaziy poliklinika'),
    ('boz',      'Otabek Hasanov',   '0010', 'HODIM',     'Politsiya',     'IIB'),
]


SEED_MESSAGES = [
    ('text', 'Salom, murojaatim bor edi. Iltimos qabul qiling.'),
    ('text', "Hujjatlarni qachon olib kelsam bo'ladi?"),
    ('text', 'Ish vaqtingizni bilsam mumkinmi?'),
    ('text', "Faqat o'zingiz bilan gaplashishim kerak."),
    ('text', "Murojaatim ko'rib chiqilganini bilsam bo'ladimi?"),
    ('audio', ''),
    ('text', 'Rahmat, hammasi tushunarli.'),
    ('text', 'Yana bir savolim bor edi.'),
    ('video', ''),
    ('text', 'Yangi murojaat yubordim, tekshirib ko\'rishingizni so\'rayman.'),
]


VISITORS = [
    'Ali Valiyev', 'Sherzod Rashidov', 'Kamola Tursunova', 'Bahodir Saidov',
    'Zilola Musinova', 'Rustam Akhmedov', 'Madina Yuldasheva', 'Doniyor Karimov',
    'Lola Sadirova', 'Sanjar Rakhmatov',
]


class Command(BaseCommand):
    help = 'Seed 10 fake targets across 2 districts + sample messages/rings/visits'

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true',
                            help='Delete previously seeded fake rows first')

    def handle(self, *args, **options):
        if options['reset']:
            self._reset()

        districts = self._seed_districts()
        targets = self._seed_targets(districts)
        self._seed_messages(targets)
        self._seed_rings(targets)
        self._seed_visits(districts)
        self._seed_service_requests(targets)

        self.stdout.write(self.style.SUCCESS(
            f'\n✅ Done. {ApplicationTarget.objects.filter(phone__startswith=FAKE_PHONE_PREFIX).count()} '
            f'fake targets across {len(districts)} districts.'
        ))
        self.stdout.write('Try:')
        self.stdout.write('  curl http://localhost:8000/api/v1/oltiariq/targets/')
        self.stdout.write('  curl http://localhost:8000/api/v1/boz/targets/')

    # ─── reset ────────────────────────────────────────────────────────────

    def _reset(self):
        fakes = ApplicationTarget.objects.filter(phone__startswith=FAKE_PHONE_PREFIX)
        user_ids = list(fakes.values_list('user_id', flat=True))
        n = fakes.count()
        fakes.delete()
        User.objects.filter(id__in=user_ids).delete()
        # Also wipe seed visitor entries
        Message.objects.filter(sender_name__in=VISITORS).delete()
        Ring.objects.filter(caller_name__in=VISITORS).delete()
        self.stdout.write(self.style.WARNING(f'Reset: removed {n} seeded targets + their users'))

    # ─── districts ─────────────────────────────────────────────────────────

    def _seed_districts(self):
        out = {}
        for slug, name in (('oltiariq', 'Oltiariq'), ('boz', "Bo'z")):
            district, created = District.objects.get_or_create(
                slug=slug, defaults={'name': name, 'is_active': True},
            )
            out[slug] = district

            admin_username = f'admin_{slug}'
            user, user_created = User.objects.get_or_create(
                username=admin_username,
                defaults={'is_staff': True, 'first_name': f'{name} admin'},
            )
            if user_created:
                pwd = get_random_string(10)
                user.set_password(pwd)
                user.save()
                self.stdout.write(self.style.SUCCESS(
                    f'  + admin user "{admin_username}" / password: {pwd}'))
            DistrictAdminProfile.objects.get_or_create(user=user, district=district)
            self.stdout.write(f'  district: {slug} ({"new" if created else "exists"})')
        return out

    # ─── targets ───────────────────────────────────────────────────────────

    def _seed_targets(self, districts):
        targets = []
        for slug, name, tail, ttype, position, agency in SEED_TARGETS:
            phone = f'{FAKE_PHONE_PREFIX}{tail}'
            existing = ApplicationTarget.objects.filter(phone=phone).first()
            if existing:
                targets.append(existing)
                continue

            user_pwd = get_random_string(8)
            user = User.objects.create_user(
                username=phone, password=user_pwd, first_name=name,
            )
            target = ApplicationTarget.objects.create(
                district=districts[slug],
                user=user,
                phone=phone,
                target_type=ttype,
                name=name,
                position_uz=position, position_kk=position, position_kir=position,
                position_ru=position, position_en=position,
                agency_uz=agency, agency_kk=agency, agency_kir=agency,
                agency_ru=agency, agency_en=agency,
                desc_uz=f'{position} — {agency}',
                desc_kk=f'{position} — {agency}',
                desc_kir=f'{position} — {agency}',
                desc_ru=f'{position} — {agency}',
                desc_en=f'{position} — {agency}',
                work_days='Dushanba-Juma',
                work_start=time(9, 0),
                work_end=time(18, 0),
                tags_uz=position.lower(),
                tags_kk=position.lower(),
                tags_kir=position.lower(),
                tags_ru=position.lower(),
                tags_en=position.lower(),
            )
            targets.append(target)
            self.stdout.write(f'  + target [{slug}] {name} ({phone})')
        return targets

    # ─── messages ──────────────────────────────────────────────────────────

    def _seed_messages(self, targets):
        for i, (msg_type, content) in enumerate(SEED_MESSAGES):
            target = targets[i % len(targets)]
            Message.objects.create(
                district=target.district,
                target=target.user,
                sender_name=random.choice(VISITORS),
                type=msg_type,
                content=content,
                is_read=random.choice([True, False, False]),
            )
        self.stdout.write(f'  + {len(SEED_MESSAGES)} messages')

    # ─── rings ─────────────────────────────────────────────────────────────

    def _seed_rings(self, targets):
        responses = ['', 'coming', 'busy', 'day_off', 'coming', '']
        for i, response in enumerate(responses):
            target = targets[i % len(targets)]
            Ring.objects.create(
                district=target.district,
                ring_id=get_random_string(32),
                target=target,
                caller_name=random.choice(VISITORS),
                response=response,
                responded_at=timezone.now() if response else None,
            )
        self.stdout.write(f'  + {len(responses)} rings')

    # ─── visits ────────────────────────────────────────────────────────────

    def _seed_visits(self, districts):
        languages = ['uz', 'uz', 'ru', 'en', 'kk', 'uz', 'ru', 'uz']
        for i, lang in enumerate(languages):
            district = list(districts.values())[i % 2]
            KioskVisit.objects.create(
                district=district,
                session_id=get_random_string(32),
                language=lang,
            )
        self.stdout.write(f'  + {len(languages)} visits')

    # ─── service requests ──────────────────────────────────────────────────

    def _seed_service_requests(self, targets):
        actions = ['view', 'view', 'view', 'ring', 'ring', 'message']
        for i, action in enumerate(actions):
            target = targets[i % len(targets)]
            ServiceRequest.objects.create(
                district=target.district,
                target=target,
                action=action,
            )
        self.stdout.write(f'  + {len(actions)} service requests')

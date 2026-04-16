from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from api_v1.models import ApplicationTarget, Message
from django.core.files import File
import os
from datetime import timedelta, time
from django.utils import timezone


class Command(BaseCommand):
    help = 'Populates the database with 10 fake targets and messages'

    def handle(self, *args, **options):
        # First, delete existing fake data (targets with phone starting with +99890)
        deleted_targets = ApplicationTarget.objects.filter(phone__startswith='+99890').delete()
        self.stdout.write(f'Deleted {deleted_targets} existing fake targets')

        # Fake data for 10 targets
        fake_targets_data = [
            {
                'first_name': 'Azamat',
                'last_name': 'Karimov',
                'phone': '998901234567',
                'target_type': ApplicationTarget.Type.HODIM,
                'position_uz': 'Dasturchi',
                'position_kr': 'программист',
                'position_ru': 'Программист',
                'position_en': 'Developer',
                'agency_uz': 'Tech Solutions',
                'agency_kr': 'Tech Solutions',
                'agency_ru': 'Tech Solutions',
                'agency_en': 'Tech Solutions',
                'desc_uz': ' tajribali dasturchi, veb-ilovalar ishlab chiqishda 5 yildan ortiq tajribaga ega',
                'desc_kr': 'tajribali dasturchi, veb-ilovalar ishlab chiqishda 5 yildan ortiq tajribaga ega',
                'desc_ru': 'Опытный программист с более чем 5-летним опытом разработки веб-приложений',
                'desc_en': 'Experienced developer with over 5 years of experience in web application development',
                'work_days': ApplicationTarget.WorkDays.MONDAY_FRIDAY,
                'work_start': '09:00',
                'work_end': '18:00',
                'tags_uz': 'python, django, react, javascript',
                'tags_kr': 'python, django, react, javascript',
                'tags_ru': 'python, django, react, javascript',
                'tags_en': 'python, django, react, javascript',
            },
            {
                'first_name': 'Gulshan',
                'last_name': 'Ahmedova',
                'phone': '998901234568',
                'target_type': ApplicationTarget.Type.HODIM,
                'position_uz': 'Marketing menedjeri',
                'position_kr': 'маркетинг менеджер',
                'position_ru': 'Маркетинг-менеджер',
                'position_en': 'Marketing Manager',
                'agency_uz': 'Business Pro',
                'agency_kr': 'Business Pro',
                'agency_ru': 'Business Pro',
                'agency_en': 'Business Pro',
                'desc_uz': 'Marketing sohasida 7 yillik tajriba, raqamli marketing strategiyasi mutaxassisi',
                'desc_kr': 'Marketing sohasida 7 yillik tajriba, raqamli marketing strategiyasi mutaxassisi',
                'desc_ru': '7 лет опыта в маркетинге, специалист по цифровым маркетинговым стратегиям',
                'desc_en': '7 years of experience in marketing, digital marketing strategy specialist',
                'work_days': ApplicationTarget.WorkDays.MONDAY_FRIDAY,
                'work_start': '08:30',
                'work_end': '17:30',
                'tags_uz': 'marketing, social media, seo, content',
                'tags_kr': 'marketing, social media, seo, content',
                'tags_ru': 'marketing, social media, seo, content',
                'tags_en': 'marketing, social media, seo, content',
            },
            {
                'first_name': 'Samir',
                'last_name': 'Toirov',
                'phone': '998901234569',
                'target_type': ApplicationTarget.Type.TASHKILOT,
                'position_uz': 'Direktor',
                'position_kr': 'директор',
                'position_ru': 'Директор',
                'position_en': 'Director',
                'agency_uz': 'Nurafshon Education Center',
                'agency_kr': 'Nurafshon Education Center',
                'agency_ru': 'Nurafshon Education Center',
                'agency_en': 'Nurafshon Education Center',
                'desc_uz': 'Ta\'lim sohasida 10 yillik tajriba, o\'quv markazini boshqaradi',
                'desc_kr': 'Ta\'lim sohasida 10 yillik tajriba, o\'quv markazini boshqaradi',
                'desc_ru': '10 лет опыта в образовании, руководит учебным центром',
                'desc_en': '10 years of experience in education, manages educational center',
                'work_days': ApplicationTarget.WorkDays.MONDAY_SATURDAY,
                'work_start': '09:00',
                'work_end': '19:00',
                'tags_uz': 'education, management, training',
                'tags_kr': 'education, management, training',
                'tags_ru': 'education, management, training',
                'tags_en': 'education, management, training',
            },
            {
                'first_name': 'Malika',
                'last_name': 'Saidova',
                'phone': '998901234570',
                'target_type': ApplicationTarget.Type.HODIM,
                'position_uz': 'English teacher',
                'position_kr': 'English teacher',
                'position_ru': 'Преподаватель английского',
                'position_en': 'English Teacher',
                'agency_uz': 'British Council Tashkent',
                'agency_kr': 'British Council Tashkent',
                'agency_ru': 'British Council Ташкент',
                'agency_en': 'British Council Tashkent',
                'desc_uz': 'Ingliz tilini o\'qitishda 6 yillik tajriba, Cambridge CELTA sertifikati',
                'desc_kr': 'Ingliz tilini o\'qitishda 6 yillik tajriba, Cambridge CELTA sertifikati',
                'desc_ru': '6 лет опыта преподавания английского языка, сертификат Cambridge CELTA',
                'desc_en': '6 years of teaching English, Cambridge CELTA certified',
                'work_days': ApplicationTarget.WorkDays.MONDAY_FRIDAY,
                'work_start': '10:00',
                'work_end': '18:00',
                'tags_uz': 'english, teaching, cambridge, esl',
                'tags_kr': 'english, teaching, cambridge, esl',
                'tags_ru': 'english, teaching, cambridge, esl',
                'tags_en': 'english, teaching, cambridge, esl',
            },
            {
                'first_name': 'Rustam',
                'last_name': 'Yusupov',
                'phone': '998901234571',
                'target_type': ApplicationTarget.Type.HODIM,
                'position_uz': 'Hisobchi',
                'position_kr': 'бухгалтер',
                'position_ru': 'Бухгалтер',
                'position_en': 'Accountant',
                'agency_uz': 'Zeromax Group',
                'agency_kr': 'Zeromax Group',
                'agency_ru': 'Zeromax Group',
                'agency_en': 'Zeromax Group',
                'desc_uz': 'Buxgalteriya hisobida 8 yillik tajriba, ERP tizimlarida mutaxassis',
                'desc_kr': 'Buxgalteriya hisobida 8 yillik tajriba, ERP tizimlarida mutaxassis',
                'desc_ru': '8 лет опыта в бухгалтерском учете, специалист по ERP системам',
                'desc_en': '8 years of experience in accounting, ERP systems specialist',
                'work_days': ApplicationTarget.WorkDays.MONDAY_FRIDAY,
                'work_start': '09:00',
                'work_end': '18:00',
                'tags_uz': 'accounting, finance, erp, taxes',
                'tags_kr': 'accounting, finance, erp, taxes',
                'tags_ru': 'accounting, finance, erp, taxes',
                'tags_en': 'accounting, finance, erp, taxes',
            },
            {
                'first_name': 'Dilorom',
                'last_name': 'Nigmatova',
                'phone': '998901234572',
                'target_type': ApplicationTarget.Type.HODIM,
                'position_uz': 'Psixolog',
                'position_kr': 'психолог',
                'position_ru': 'Психолог',
                'position_en': 'Psychologist',
                'agency_uz': 'Salomatlik Markazi',
                'agency_kr': 'Salomatlik Markazi',
                'agency_ru': 'Центр Здоровья',
                'agency_en': 'Health Center',
                'desc_uz': 'Klinik psixolog, 5 yillik tajriba, nikoh va oila psixologiyasi mutaxassisi',
                'desc_kr': 'Klinik psixolog, 5 yillik tajriba, nikoh va oila psixologiyasi mutaxassisi',
                'desc_ru': 'Клинический психолог, 5 лет опыта, специалист по семейной психологии',
                'desc_en': 'Clinical psychologist, 5 years experience, family psychology specialist',
                'work_days': ApplicationTarget.WorkDays.MONDAY_SATURDAY,
                'work_start': '14:00',
                'work_end': '20:00',
                'tags_uz': 'psychology, counseling, family, therapy',
                'tags_kr': 'psychology, counseling, family, therapy',
                'tags_ru': 'psychology, counseling, family, therapy',
                'tags_en': 'psychology, counseling, family, therapy',
            },
            {
                'first_name': 'Jahongir',
                'last_name': 'Abdullaev',
                'phone': '998901234573',
                'target_type': ApplicationTarget.Type.HODIM,
                'position_uz': 'Yurist',
                'position_kr': 'юрист',
                'position_ru': 'Юрист',
                'position_en': 'Lawyer',
                'agency_uz': 'Legalconsult LLP',
                'agency_kr': 'Legalconsult LLP',
                'agency_ru': 'Legalconsult LLP',
                'agency_en': 'Legalconsult LLP',
                'desc_uz': 'Huquqshunos, 9 yillik tajriba, tijorat va mulk huquqi mutaxassisi',
                'desc_kr': 'Huquqshunos, 9 yillik tajriba, tijorat va mulk huquqi mutaxassisi',
                'desc_ru': 'Юрист, 9 лет опыта, специалист по коммерческому и имущественному праву',
                'desc_en': 'Lawyer, 9 years experience, commercial and property law specialist',
                'work_days': ApplicationTarget.WorkDays.MONDAY_FRIDAY,
                'work_start': '09:00',
                'work_end': '18:00',
                'tags_uz': 'law, legal, contract, business',
                'tags_kr': 'law, legal, contract, business',
                'tags_ru': 'law, legal, contract, business',
                'tags_en': 'law, legal, contract, business',
            },
            {
                'first_name': 'Zebo',
                'last_name': 'Isoqova',
                'phone': '998901234574',
                'target_type': ApplicationTarget.Type.HODIM,
                'position_uz': 'Dizayner',
                'position_kr': 'дизайнер',
                'position_ru': 'Дизайнер',
                'position_en': 'Designer',
                'agency_uz': 'Creative Studio',
                'agency_kr': 'Creative Studio',
                'agency_ru': 'Creative Studio',
                'agency_en': 'Creative Studio',
                'desc_uz': 'Grafik dizayner, 4 yillik tajriba, brending va web dizayn mutaxassisi',
                'desc_kr': 'Grafik dizayner, 4 yillik tajriba, brending va web dizayn mutaxassisi',
                'desc_ru': 'Графический дизайнер, 4 года опыта, специалист по брендингу и веб-дизайну',
                'desc_en': 'Graphic designer, 4 years experience, branding and web design specialist',
                'work_days': ApplicationTarget.WorkDays.MONDAY_FRIDAY,
                'work_start': '10:00',
                'work_end': '19:00',
                'tags_uz': 'design, branding, illustrator, figma',
                'tags_kr': 'design, branding, illustrator, figma',
                'tags_ru': 'design, branding, illustrator, figma',
                'tags_en': 'design, branding, illustrator, figma',
            },
            {
                'first_name': 'OTajik',
                'last_name': 'Qahorov',
                'phone': '998901234575',
                'target_type': ApplicationTarget.Type.HODIM,
                'position_uz': 'Smm mutaxassisi',
                'position_kr': 'smm мутахассис',
                'position_ru': 'SMM-специалист',
                'position_en': 'SMM Specialist',
                'agency_uz': 'Mediacom Agency',
                'agency_kr': 'Mediacom Agency',
                'agency_ru': 'Mediacom Agency',
                'agency_en': 'Mediacom Agency',
                'desc_uz': 'Ijtimoiy tarmoqlar marketingi mutaxassisi, 3 yillik tajriba',
                'desc_kr': 'Ijtimoiy tarmoqlar marketingi mutaxassisi, 3 yillik tajriba',
                'desc_ru': 'Специалист по маркетингу в социальных сетях, 3 года опыта',
                'desc_en': 'Social media marketing specialist, 3 years experience',
                'work_days': ApplicationTarget.WorkDays.MONDAY_FRIDAY,
                'work_start': '09:00',
                'work_end': '18:00',
                'tags_uz': 'smm, instagram, telegram, content',
                'tags_kr': 'smm, instagram, telegram, content',
                'tags_ru': 'smm, instagram, telegram, content',
                'tags_en': 'smm, instagram, telegram, content',
            },
            {
                'first_name': 'Nodir',
                'last_name': 'Eshqobilov',
                'phone': '998901234576',
                'target_type': ApplicationTarget.Type.HODIM,
                'position_uz': 'Elektr-montachi',
                'position_kr': 'электрик',
                'position_ru': 'Электрик',
                'position_en': 'Electrician',
                'agency_uz': 'Uzelektromontaj',
                'agency_kr': 'Uzelektromontaj',
                'agency_ru': 'Uzelektromontaj',
                'agency_en': 'Uzelektromontaj',
                'desc_uz': 'Elektro-montaj ishlari, 10 yillik tajriba, xavfsizlik sertifikati',
                'desc_kr': 'Elektro-montaj ishlari, 10 yillik tajriba, xavfsizlik sertifikati',
                'desc_ru': 'Электромонтажные работы, 10 лет опыта, сертификат по безопасности',
                'desc_en': 'Electrical installation works, 10 years experience, safety certificate',
                'work_days': ApplicationTarget.WorkDays.MONDAY_SATURDAY,
                'work_start': '08:00',
                'work_end': '17:00',
                'tags_uz': 'electrician, wiring, installation, repair',
                'tags_kr': 'electrician, wiring, installation, repair',
                'tags_ru': 'electrician, wiring, installation, repair',
                'tags_en': 'electrician, wiring, installation, repair',
            },
        ]

        # Create fake targets
        for data in fake_targets_data:
            # Create User
            username = f"{data['first_name'].lower()}_{data['last_name'].lower()}"
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'first_name': data['first_name'],
                    'last_name': data['last_name'],
                    'email': f"{username}@example.com",
                }
            )
            if created:
                # Set password as first_name + 8275 (e.g., alisher8275)
                password = f"{data['first_name'].lower()}8275"
                user.set_password(password)

            # Use existing image or create a simple one
            default_image_path = 'media/profiles/noImage.webp'
            
            target = ApplicationTarget.objects.create(
                user=user,
                phone=data['phone'],
                target_type=data['target_type'],
                image=default_image_path,
                position_uz=data['position_uz'],
                position_kr=data['position_kr'],
                position_ru=data['position_ru'],
                position_en=data['position_en'],
                agency_uz=data['agency_uz'],
                agency_kr=data['agency_kr'],
                agency_ru=data['agency_ru'],
                agency_en=data['agency_en'],
                desc_uz=data['desc_uz'],
                desc_kr=data['desc_kr'],
                desc_ru=data['desc_ru'],
                desc_en=data['desc_en'],
                work_days=data['work_days'],
                work_start=time(int(data['work_start'].split(':')[0]), int(data['work_start'].split(':')[1])),
                work_end=time(int(data['work_end'].split(':')[0]), int(data['work_end'].split(':')[1])),
                tags_uz=data['tags_uz'],
                tags_kr=data['tags_kr'],
                tags_ru=data['tags_ru'],
                tags_en=data['tags_en'],
            )
            self.stdout.write(f'Created target: {target.user.get_full_name()}')

        # Now create messages for each target
        targets = ApplicationTarget.objects.filter(phone__startswith='+99890')
        
        messages_data = [
            # Messages for first target (Azamat Karimov)
            [
                {'sender_name': 'HR Department', 'content': 'Hello Azamat, welcome to Tech Solutions! Your first day is scheduled for next Monday at 09:00.', 'type': Message.MessageType.TEXT},
                {'sender_name': 'System', 'content': 'Your employee ID is TS-2024-001. Please bring your passport and diploma.', 'type': Message.MessageType.TEXT},
            ],
            # Messages for second target (Gulshan Ahmedova)
            [
                {'sender_name': 'CEO', 'content': 'Gulshan, we need to discuss the new marketing campaign. Please come to my office at 14:00.', 'type': Message.MessageType.TEXT},
                {'sender_name': 'Team', 'content': 'Great work on the social media launch! The engagement increased by 40%.', 'type': Message.MessageType.TEXT},
            ],
            # Messages for third target (Samir Toirov)
            [
                {'sender_name': 'Education Ministry', 'content': 'Your center has been approved for the new language program.', 'type': Message.MessageType.TEXT},
                {'sender_name': 'Parent', 'content': 'Assalomu alaykum, Samir bey. Mening bolam uchun ingliz tili kursiga yozilishim mumkinmi?', 'type': Message.MessageType.TEXT},
            ],
            # Messages for fourth target (Malika Saidova)
            [
                {'sender_name': 'Student', 'content': 'Assalomu alaykum, Malika xonim! Ingliz tilini boyitishim uchun dars qachon boshlanadi?', 'type': Message.MessageType.TEXT},
                {'sender_name': 'British Council', 'content': 'Your CELTA renewal has been approved. Congratulations!', 'type': Message.MessageType.TEXT},
            ],
            # Messages for fifth target (Rustam Yusupov)
            [
                {'sender_name': 'Finance', 'content': 'Rustam, the quarterly report is due next Friday. Please submit it before 17:00.', 'type': Message.MessageType.TEXT},
                {'sender_name': 'Tax Authority', 'content': 'Your tax return for Q1 has been processed. No issues found.', 'type': Message.MessageType.TEXT},
            ],
            # Messages for sixth target (Dilorom Nigmatova)
            [
                {'sender_name': 'Patient', 'content': 'Assalomu alaykum, Dilorom xonim. Men oilaviy masalalar bo\'yicha maslahat olishim mumkinmi?', 'type': Message.MessageType.TEXT},
                {'sender_name': 'Clinic', 'content': 'Your consultation schedule for next week has been updated.', 'type': Message.MessageType.TEXT},
            ],
            # Messages for seventh target (Jahongir Abdullaev)
            [
                {'sender_name': 'Client', 'content': 'Jahongir bey, company incorporation hujjatlarini tayyor boldingizmi?', 'type': Message.MessageType.TEXT},
                {'sender_name': 'Court', 'content': 'Your hearing scheduled for April 20th has been moved to April 22nd.', 'type': Message.MessageType.TEXT},
            ],
            # Messages for eighth target (Zebo Isoqova)
            [
                {'sender_name': 'Client', 'content': 'Zebo, logo loyihasi juda yaxshi chiqdi. Rahmat!', 'type': Message.MessageType.TEXT},
                {'sender_name': 'Creative Director', 'content': 'Please submit the final designs for the brand book by Friday.', 'type': Message.MessageType.TEXT},
            ],
            # Messages for ninth target (OTajik Qahorov)
            [
                {'sender_name': 'Client', 'content': 'Telegram kanalimiz uchun postlar tayyor boldimi?', 'type': Message.MessageType.TEXT},
                {'sender_name': 'Analytics', 'content': 'Great news! Our Instagram reach increased by 25% this week.', 'type': Message.MessageType.TEXT},
            ],
            # Messages for tenth target (Nodir Eshqobilov)
            [
                {'sender_name': 'Site Manager', 'content': 'Nodir, bugungi elektr ishlari qachon bajariladi?', 'type': Message.MessageType.TEXT},
                {'sender_name': 'Safety Officer', 'content': 'Please complete the safety training module before starting work.', 'type': Message.MessageType.TEXT},
            ],
        ]

        # Create messages for each target
        for i, target in enumerate(targets):
            if i < len(messages_data):
                for msg_data in messages_data[i]:
                    Message.objects.create(
                        target=target.user,
                        sender_name=msg_data['sender_name'],
                        content=msg_data['content'],
                        type=msg_data['type'],
                        timestamp=timezone.now() - timedelta(days=i),
                    )
                self.stdout.write(f'Created {len(messages_data[i])} messages for {target.user.get_full_name()}')

        self.stdout.write(self.style.SUCCESS(f'Successfully created {len(fake_targets_data)} fake targets with messages'))
"""
Management команда для заполнения БД тестовыми данными (seed для демонстрации).

Что здесь:
- Command.handle(): точка входа, оркестрирует весь seed
- Данные для демонстрации на защите:
  - 20 городов РФ по всем федеральным округам
  - 6 менеджеров (по одному на округ) + super_manager (manager1@sportrent.ru)
  - 20 владельцев инвентаря с паспортными данными и NDA-записями
  - 150 единиц инвентаря (лыжи, велосипеды, байдарки, ролики и т.д.)
  - 55-65 аренд в разных статусах (включая просроченные для демонстрации штрафов)
  - PaymentIntent-записи со статусами succeeded/pending для ЮКассы
- Стратегия: upsert для пользователей (get_or_create), clean-and-seed для остального

Связано с:
- users/models.py: User, Client, Owner, Manager, PassportNDA
- inventory/models.py: Inventory, PickupPoint, City
- rentals/models.py: Rental, Reservation
- payments/models.py: PaymentIntent

Ключевые слова: тестовые данные, seed, demo, populate, демонстрация
"""

import re
import random
import shutil
from datetime import timedelta
from decimal import Decimal
from pathlib import Path


def _norm_phone(phone: str) -> str:
    """Нормализует телефон к виду +7XXXXXXXXXX (E.164, 10 цифр после +7)."""
    digits = re.sub(r'\D', '', phone)
    if len(digits) == 11 and digits[0] in ('7', '8'):
        return '+7' + digits[1:]
    if len(digits) == 10:
        return '+7' + digits
    return phone

from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.db.utils import OperationalError
from django.utils import timezone

from chat.models import ChatMessage
from inventory.models import City, Inventory, PickupPoint, SportCategory
from rentals.models import Contract, DamageReport, Payment, Rental, Reservation
from reviews.models import Review
from users.models import (
    Administrator, BankAccount, Client, Manager, Owner, OwnerAgreement, User,
)

# ─────────────────────────────────────────────────────────────────────────────
# Справочные данные
# ─────────────────────────────────────────────────────────────────────────────

CITY_DATA = [
    # (name, region, lat, lon, district, points_count)
    ('Москва',          'Москва',                   '55.755864', '37.617698', 'ЦФО',  3),
    ('Воронеж',         'Воронежская область',       '51.661535', '39.200287', 'ЦФО',  2),
    ('Ярославль',       'Ярославская область',       '57.626568', '39.893787', 'ЦФО',  2),
    ('Тула',            'Тульская область',          '54.193122', '37.617348', 'ЦФО',  2),
    ('Санкт-Петербург', 'Ленинградская область',     '59.938951', '30.315635', 'СЗФО', 3),
    ('Казань',          'Республика Татарстан',      '55.796127', '49.106414', 'ПФО',  3),
    ('Нижний Новгород', 'Нижегородская область',     '56.326887', '44.005986', 'ПФО',  3),
    ('Самара',          'Самарская область',         '53.195878', '50.100202', 'ПФО',  3),
    ('Уфа',             'Республика Башкортостан',   '54.735152', '55.958736', 'ПФО',  2),
    ('Пермь',           'Пермский край',             '57.990986', '56.229443', 'ПФО',  2),
    ('Саратов',         'Саратовская область',       '51.533562', '46.034266', 'ПФО',  2),
    ('Екатеринбург',    'Свердловская область',      '56.838011', '60.597474', 'УФО',  3),
    ('Челябинск',       'Челябинская область',       '55.154927', '61.401079', 'УФО',  2),
    ('Тюмень',          'Тюменская область',         '57.153033', '65.534328', 'УФО',  2),
    ('Новосибирск',     'Новосибирская область',     '54.989347', '82.904632', 'СФО',  3),
    ('Омск',            'Омская область',            '54.989342', '73.368212', 'СФО',  2),
    ('Красноярск',      'Красноярский край',         '56.010569', '92.852545', 'СФО',  2),
    ('Краснодар',       'Краснодарский край',        '45.035470', '38.975313', 'ЮФО',  3),
    ('Ростов-на-Дону',  'Ростовская область',        '47.222078', '39.720349', 'ЮФО',  2),
    ('Волгоград',       'Волгоградская область',     '48.707103', '44.516939', 'ЮФО',  2),
]

CITY_DISTRICT = {row[0]: row[4] for row in CITY_DATA}

ALL_CATS      = ['Велосипеды', 'Лыжи', 'Сноуборды', 'Ролики', 'Самокаты', 'Туристическое снаряжение', 'Водный спорт']
UFO_SFO_CATS  = ['Велосипеды', 'Лыжи', 'Сноуборды', 'Ролики', 'Самокаты', 'Туристическое снаряжение']
YUFO_CATS     = ['Велосипеды', 'Ролики', 'Самокаты', 'Туристическое снаряжение', 'Водный спорт']

DISTRICT_CATS = {
    'ЦФО': ALL_CATS, 'СЗФО': ALL_CATS, 'ПФО': ALL_CATS,
    'УФО': UFO_SFO_CATS, 'СФО': UFO_SFO_CATS,
    'ЮФО': YUFO_CATS,
}

MANAGER_DATA = [
    # (email, password, full_name, district, phone)
    ('manager1@sportrent.ru',     'manager123', 'Петров Пётр Петрович',        'ЦФО',  '+7(499)100-10-01'),
    ('manager_szfo@sportrent.ru', 'manager123', 'Иванченко Виктор Николаевич', 'СЗФО', '+7(812)200-20-02'),
    ('manager_pfo@sportrent.ru',  'manager123', 'Галимов Ильдар Рифатович',    'ПФО',  '+7(843)300-30-03'),
    ('manager_ufo@sportrent.ru',  'manager123', 'Соколов Дмитрий Андреевич',   'УФО',  '+7(343)400-40-04'),
    ('manager_sfo@sportrent.ru',  'manager123', 'Власов Алексей Геннадьевич',  'СФО',  '+7(383)500-50-05'),
    ('manager_yufo@sportrent.ru', 'manager123', 'Степанова Наталья Олеговна',  'ЮФО',  '+7(861)600-60-06'),
]

OWNER_DATA = [
    # (email, full_name, city, tax_number)
    ('owner1@mail.ru',  'Владимиров Владимир Владимирович', 'Москва',          '770112345601'),
    ('owner2@mail.ru',  'Александрова Мария Сергеевна',    'Воронеж',         '360112345602'),
    ('owner3@mail.ru',  'Николаев Николай Николаевич',     'Ярославль',       '760112345603'),
    ('owner4@mail.ru',  'Беляев Сергей Петрович',          'Тула',            '710112345604'),
    ('owner5@mail.ru',  'Соколова Анна Дмитриевна',        'Санкт-Петербург', '780112345605'),
    ('owner6@mail.ru',  'Миронов Артём Игоревич',          'Казань',          '160112345606'),
    ('owner7@mail.ru',  'Зайцева Екатерина Витальевна',    'Нижний Новгород', '520112345607'),
    ('owner8@mail.ru',  'Борисов Павел Николаевич',        'Самара',          '630112345608'),
    ('owner9@mail.ru',  'Фёдорова Ирина Анатольевна',      'Уфа',             '020112345609'),
    ('owner10@mail.ru', 'Громов Илья Сергеевич',           'Пермь',           '590112345610'),
    ('owner11@mail.ru', 'Тихонова Светлана Романовна',     'Саратов',         '640112345611'),
    ('owner12@mail.ru', 'Сидоров Андрей Вячеславович',     'Екатеринбург',    '660112345612'),
    ('owner13@mail.ru', 'Кузьмина Ольга Игоревна',         'Челябинск',       '740112345613'),
    ('owner14@mail.ru', 'Тарасов Максим Дмитриевич',       'Тюмень',          '720112345614'),
    ('owner15@mail.ru', 'Панова Юлия Алексеевна',          'Новосибирск',     '540112345615'),
    ('owner16@mail.ru', 'Орлов Станислав Викторович',      'Омск',            '550112345616'),
    ('owner17@mail.ru', 'Волков Денис Андреевич',          'Красноярск',      '240112345617'),
    ('owner18@mail.ru', 'Захарова Алина Олеговна',         'Краснодар',       '230112345618'),
    ('owner19@mail.ru', 'Кириллов Роман Евгеньевич',       'Ростов-на-Дону',  '610112345619'),
    ('owner20@mail.ru', 'Лебедева Виктория Павловна',      'Волгоград',       '340112345620'),
]

# Региональные серии паспортов и наименования органов выдачи для владельцев (демо)
CITY_PASSPORT_INFO = {
    'Москва':          ('4501', 'г. Москве'),
    'Воронеж':         ('3601', 'Воронежской области'),
    'Ярославль':       ('7601', 'Ярославской области'),
    'Тула':            ('7101', 'Тульской области'),
    'Санкт-Петербург': ('4001', 'г. Санкт-Петербургу'),
    'Казань':          ('9201', 'Республике Татарстан'),
    'Нижний Новгород': ('5201', 'Нижегородской области'),
    'Самара':          ('6301', 'Самарской области'),
    'Уфа':             ('0201', 'Республике Башкортостан'),
    'Пермь':           ('5901', 'Пермскому краю'),
    'Саратов':         ('6401', 'Саратовской области'),
    'Екатеринбург':    ('6601', 'Свердловской области'),
    'Челябинск':       ('7401', 'Челябинской области'),
    'Тюмень':          ('7201', 'Тюменской области'),
    'Новосибирск':     ('5401', 'Новосибирской области'),
    'Омск':            ('5501', 'Омской области'),
    'Красноярск':      ('2401', 'Красноярскому краю'),
    'Краснодар':       ('2301', 'Краснодарскому краю'),
    'Ростов-на-Дону':  ('6101', 'Ростовской области'),
    'Волгоград':       ('3401', 'Волгоградской области'),
}

CLIENT_DATA = [
    ('client1@mail.ru',  'Иванов Иван Иванович'),
    ('client2@mail.ru',  'Смирнова Елена Александровна'),
    ('client3@mail.ru',  'Кузнецов Дмитрий Павлович'),
    ('client4@mail.ru',  'Морозова Ольга Викторовна'),
    ('client5@mail.ru',  'Федоров Андрей Михайлович'),
    ('client6@mail.ru',  'Лазарева Татьяна Игоревна'),
    ('client7@mail.ru',  'Новиков Сергей Аркадьевич'),
    ('client8@mail.ru',  'Попова Дарья Константиновна'),
    ('client9@mail.ru',  'Щербаков Антон Олегович'),
    ('client10@mail.ru', 'Герасимова Ксения Леонидовна'),
    ('client11@mail.ru', 'Тимофеев Алексей Иванович'),
    ('client12@mail.ru', 'Гусева Наталья Сергеевна'),
    ('client13@mail.ru', 'Ковалёв Михаил Дмитриевич'),
    ('client14@mail.ru', 'Яковлева Анна Петровна'),
    ('client15@mail.ru', 'Семёнов Виктор Борисович'),
]

# (name, address, lat, lon, phone) — индексированы по городу
PICKUP_POINTS_BY_CITY = {
    'Москва': [
        ('СпортРядом Арбат',        'ул. Арбат, 22',               '55.752000', '37.592100', '+7(499)100-10-10'),
        ('СпортРядом Сокольники',   'ул. Сокольнический вал, 1',   '55.789700', '37.677700', '+7(499)100-10-11'),
        ('СпортРядом Коломенская',  'пр-т Андропова, 39',          '55.668000', '37.668600', '+7(499)100-10-12'),
    ],
    'Воронеж': [
        ('СпортРядом Центр',        'пр-т Революции, 30',          '51.661500', '39.200300', '+7(473)200-20-20'),
        ('СпортРядом Советский',    'Московский пр-т, 88',         '51.674400', '39.171200', '+7(473)200-20-21'),
    ],
    'Ярославль': [
        ('СпортРядом Центр',        'ул. Советская, 5',            '57.626100', '39.884500', '+7(485)300-30-30'),
        ('СпортРядом Заволжский',   'Тутаевское шоссе, 14',        '57.665100', '39.839800', '+7(485)300-30-31'),
    ],
    'Тула': [
        ('СпортРядом Центр',        'пр-т Ленина, 14',             '54.193100', '37.617300', '+7(487)400-40-40'),
        ('СпортРядом Пролетарский', 'ул. Мосина, 14',              '54.169300', '37.635500', '+7(487)400-40-41'),
    ],
    'Санкт-Петербург': [
        ('СпортРядом Невский',      'Невский проспект, 50',        '59.930900', '30.346100', '+7(812)500-50-50'),
        ('СпортРядом Петроградская','ул. Б. Пушкарская, 10',       '59.961700', '30.301400', '+7(812)500-50-51'),
        ('СпортРядом Московский',   'Московский пр-т, 100',        '59.889500', '30.321800', '+7(812)500-50-52'),
    ],
    'Казань': [
        ('СпортРядом Баумана',      'ул. Баумана, 44',             '55.794900', '49.113000', '+7(843)600-60-60'),
        ('СпортРядом Кремль',       'ул. Кремлёвская, 18',         '55.799400', '49.106500', '+7(843)600-60-61'),
        ('СпортРядом Дербышки',     'ул. Мира, 12',                '55.854100', '49.216800', '+7(843)600-60-62'),
    ],
    'Нижний Новгород': [
        ('СпортРядом Покровка',     'ул. Б. Покровская, 25',       '56.328600', '44.003500', '+7(831)700-70-70'),
        ('СпортРядом Сормово',      'ул. Коминтерна, 104',         '56.366100', '43.864700', '+7(831)700-70-71'),
        ('СпортРядом Кузнечиха',    'ул. Родионова, 165',          '56.281300', '43.991200', '+7(831)700-70-72'),
    ],
    'Самара': [
        ('СпортРядом Центр',        'ул. Куйбышева, 74',           '53.194600', '50.156400', '+7(846)800-80-80'),
        ('СпортРядом Металлург',    'пр-т Металлургов, 49',        '53.209700', '50.237400', '+7(846)800-80-81'),
        ('СпортРядом Советский',    'ул. Советской Армии, 101',    '53.225200', '50.198800', '+7(846)800-80-82'),
    ],
    'Уфа': [
        ('СпортРядом Центр',        'пр-т Октября, 3',             '54.729800', '55.960000', '+7(347)900-90-90'),
        ('СпортРядом Черниковка',   'ул. Первомайская, 47',        '54.805700', '55.943200', '+7(347)900-90-91'),
    ],
    'Пермь': [
        ('СпортРядом Центр',        'ул. Ленина, 38',              '57.990400', '56.230100', '+7(342)910-10-10'),
        ('СпортРядом Кировский',    'шоссе Космонавтов, 111',      '58.011800', '56.187700', '+7(342)910-10-11'),
    ],
    'Саратов': [
        ('СпортРядом Центр',        'пр-т Кирова, 14',             '51.533500', '46.034200', '+7(845)920-20-20'),
        ('СпортРядом Заводской',    'ул. Жуковского, 27',          '51.498000', '45.999300', '+7(845)920-20-21'),
    ],
    'Екатеринбург': [
        ('СпортРядом Центр',        'ул. Ленина, 24/8',            '56.838900', '60.605700', '+7(343)930-30-30'),
        ('СпортРядом Пионерский',   'ул. Первомайская, 77',        '56.846800', '60.661300', '+7(343)930-30-31'),
        ('СпортРядом Уралмаш',      'пр-т Космонавтов, 18',        '56.903100', '60.610200', '+7(343)930-30-32'),
    ],
    'Челябинск': [
        ('СпортРядом Центр',        'ул. Кирова, 100',             '55.154900', '61.401000', '+7(351)940-40-40'),
        ('СпортРядом Северо-Запад', 'ул. Труда, 203',              '55.178100', '61.369000', '+7(351)940-40-41'),
    ],
    'Тюмень': [
        ('СпортРядом Центр',        'ул. Республики, 52',          '57.153000', '65.534300', '+7(345)950-50-50'),
        ('СпортРядом Восточный',    'ул. Мельникайте, 106',        '57.159700', '65.588000', '+7(345)950-50-51'),
    ],
    'Новосибирск': [
        ('СпортРядом Красный пр-т', 'Красный проспект, 82',        '54.990600', '82.901700', '+7(383)960-60-60'),
        ('СпортРядом Академгородок','пр-т Ак. Лаврентьева, 6',    '54.844000', '83.106900', '+7(383)960-60-61'),
        ('СпортРядом Заельцовский', 'ул. Дуси Ковальчук, 179',    '55.028300', '82.928600', '+7(383)960-60-62'),
    ],
    'Омск': [
        ('СпортРядом Центр',        'ул. Ленина, 8',               '54.989300', '73.368200', '+7(381)970-70-70'),
        ('СпортРядом Кировский',    'пр-т Карла Маркса, 26',       '54.968500', '73.394000', '+7(381)970-70-71'),
    ],
    'Красноярск': [
        ('СпортРядом Центр',        'пр-т Мира, 38',               '56.010600', '92.852600', '+7(391)980-80-80'),
        ('СпортРядом Советский',    'ул. Маерчака, 10',            '56.028100', '92.881400', '+7(391)980-80-81'),
    ],
    'Краснодар': [
        ('СпортРядом Красная',      'ул. Красная, 55',             '45.039600', '38.976900', '+7(861)990-90-90'),
        ('СпортРядом Гидрострой',   'ул. Дзержинского, 100',       '45.058100', '38.964900', '+7(861)990-90-91'),
        ('СпортРядом Прикубанский', 'ул. им. Тюляева, 13',         '45.019600', '39.031100', '+7(861)990-90-92'),
    ],
    'Ростов-на-Дону': [
        ('СпортРядом Центр',        'ул. Большая Садовая, 54',     '47.222000', '39.720300', '+7(863)010-10-10'),
        ('СпортРядом Ленинский',    'пр-т Кировский, 66',          '47.206400', '39.742600', '+7(863)010-10-11'),
    ],
    'Волгоград': [
        ('СпортРядом Центр',        'пр-т Ленина, 32',             '48.707100', '44.516900', '+7(844)020-20-20'),
        ('СпортРядом Красноармейский','пр-т Героев Сталинграда, 47','48.568000', '44.526800', '+7(844)020-20-21'),
    ],
}

ITEMS_BY_CAT = {
    'Велосипеды': [
        ('Горный велосипед Trek Marlin 7',         'Хардтейл 29" для трейлов и кросс-кантри',         'Trek',        'Marlin 7',          Decimal('800'),  'excellent'),
        ('Шоссейный велосипед Giant TCR Advanced', 'Лёгкий карбоновый шоссейник',                     'Giant',       'TCR Advanced',      Decimal('1200'), 'excellent'),
        ('Городской велосипед Stels Navigator 350','Комфортный городской велосипед',                   'Stels',       'Navigator 350',     Decimal('500'),  'good'),
        ('Горный велосипед Specialized Rockhopper','Надёжный хардтейл 27.5"',                          'Specialized', 'Rockhopper',        Decimal('750'),  'good'),
        ('Гибридный велосипед Trek FX 2',          'Для города и парка',                              'Trek',        'FX 2',              Decimal('520'),  'good'),
        ('Горный велосипед Merida Big.Nine 300',   'Найнер для быстрых трасс',                        'Merida',      'Big.Nine 300',      Decimal('900'),  'excellent'),
        ('BMX Haro Downtown 20',                   'Трюковый велосипед для стрита',                   'Haro',        'Downtown 20',       Decimal('400'),  'good'),
        ('Электровелосипед Cube Reaction Hybrid',  'Горный e-bike с мотором Bosch 625 Вт',            'Cube',        'Reaction Hybrid',   Decimal('1500'), 'excellent'),
        ('Фэтбайк Stels Fat 26"',                  'Велосипед на широких шинах для бездорожья',       'Stels',       'Fat 26"',           Decimal('650'),  'good'),
        ('Складной велосипед Dahon Qix D8',        'Компактный складник для города',                  'Dahon',       'Qix D8',            Decimal('480'),  'good'),
    ],
    'Лыжи': [
        ('Горные лыжи Atomic Redster G9',          'Профессиональный GS-карвинг',                     'Atomic',      'Redster G9',        Decimal('1500'), 'excellent'),
        ('Беговые лыжи Fischer Speedmax Classic',  'Коньковые лыжи для гонки',                       'Fischer',     'Speedmax Classic',  Decimal('900'),  'good'),
        ('Горные лыжи Rossignol Hero Elite LT',    'Карвинг для опытных лыжников',                   'Rossignol',   'Hero Elite LT',     Decimal('1300'), 'excellent'),
        ('Беговые лыжи Madshus Redline SC',        'Гоночные лыжи для конькового хода',               'Madshus',     'Redline SC',        Decimal('1100'), 'excellent'),
        ('Горные лыжи Head Supershape E-Speed',    'Универсальный карвинг для склона',                'Head',        'Supershape E-Speed',Decimal('1200'), 'good'),
        ('Горные лыжи Salomon QST 92',             'All-mountain для глубокого снега',                'Salomon',     'QST 92',            Decimal('1000'), 'good'),
        ('Беговые лыжи Salomon RS8 Skate',         'Конёк среднего уровня',                           'Salomon',     'RS8 Skate',         Decimal('700'),  'good'),
        ('Горные лыжи Elan Wingman 86 CTI',        'Универсал для новичков и среднего уровня',        'Elan',        'Wingman 86 CTI',    Decimal('1100'), 'excellent'),
    ],
    'Сноуборды': [
        ('Сноуборд Burton Custom X',               'Жёсткий для парка и пайпа',                       'Burton',      'Custom X',          Decimal('1100'), 'excellent'),
        ('Сноуборд Ride Agenda',                   'Всегорный для начинающих',                        'Ride',        'Agenda',            Decimal('700'),  'good'),
        ('Сноуборд Salomon Assassin',              'Парковый трюковый борд',                           'Salomon',     'Assassin',          Decimal('1000'), 'excellent'),
        ('Сноуборд K2 Raygun',                     'Универсал для склона и парка',                    'K2',          'Raygun',            Decimal('850'),  'good'),
        ('Сноуборд Nidecker Megatron',             'Жёсткий для карвинга',                            'Nidecker',    'Megatron',          Decimal('950'),  'excellent'),
        ('Сноуборд Lib Tech Travis Rice Orca',     'Борд для глубокого паудера',                      'Lib Tech',    'Travis Rice Orca',  Decimal('1300'), 'excellent'),
    ],
    'Ролики': [
        ('Ролики Rollerblade Zetrablade',          'Фитнес-ролики для взрослых',                      'Rollerblade', 'Zetrablade',        Decimal('400'),  'good'),
        ('Ролики K2 F.I.T. 84',                    'Мягкие фитнес-ролики',                            'K2',          'F.I.T. 84',         Decimal('450'),  'good'),
        ('Ролики Powerslide Next Core',            'Скоростные для марафона',                         'Powerslide',  'Next Core',         Decimal('600'),  'excellent'),
        ('Ролики Seba FR1 80',                     'Для агрессивного катания',                        'Seba',        'FR1 80',            Decimal('500'),  'good'),
        ('Ролики Rollerblade Twister Edge',        'Городские urban-ролики',                          'Rollerblade', 'Twister Edge',      Decimal('550'),  'excellent'),
        ('Детские ролики Micro Trixx',             'Регулируемые ролики для детей',                   'Micro',       'Trixx',             Decimal('300'),  'good'),
    ],
    'Самокаты': [
        ('Электросамокат Xiaomi Mi Pro 2',         'Мощный до 25 км/ч, запас хода 45 км',            'Xiaomi',      'Mi Pro 2',          Decimal('600'),  'excellent'),
        ('Самокат Razor A5 Lux',                   'Складной самокат для взрослых',                   'Razor',       'A5 Lux',            Decimal('300'),  'good'),
        ('Электросамокат Ninebot Max G30',         'Максимальный запас хода 65 км',                   'Ninebot',     'Max G30',           Decimal('750'),  'excellent'),
        ('Электросамокат Kugoo S3 Pro',            'Мощный внедорожный электросамокат',               'Kugoo',       'S3 Pro',            Decimal('650'),  'good'),
        ('Трюковый самокат Tao Tao Zodiac',        'Для парковых трюков',                             'Tao Tao',     'Zodiac',            Decimal('250'),  'good'),
        ('Электросамокат Dualtron Mini',           'Компактный городской двухмоторный',               'Minimotors',  'Dualtron Mini',     Decimal('800'),  'excellent'),
    ],
    'Туристическое снаряжение': [
        ('Палатка Quechua Arpenaz 3',              'Трёхместная летняя лёгкая палатка',               'Quechua',     'Arpenaz 3',         Decimal('450'),  'good'),
        ('Рюкзак Osprey Atmos AG 65',              'Туристический 65 л с вентиляцией спины',          'Osprey',      'Atmos AG 65',       Decimal('350'),  'excellent'),
        ('Палатка Nordway Sphinx 2',               'Двухместная трёхсезонная палатка',                'Nordway',     'Sphinx 2',          Decimal('380'),  'good'),
        ('Рюкзак Deuter Aircontact 55+10',         'С системой вентиляции спины',                     'Deuter',      'Aircontact 55+10',  Decimal('480'),  'excellent'),
        ('Палатка MSR Hubba Hubba NX',             'Ультралёгкая двухместная палатка',                'MSR',         'Hubba Hubba NX',    Decimal('600'),  'excellent'),
        ('Рюкзак Gregory Baltoro 75',              'Экспедиционный рюкзак 75 л',                      'Gregory',     'Baltoro 75',        Decimal('520'),  'excellent'),
        ('Спальник Marmot Trestles 30',            'Синтетик, комфорт до -1°C',                       'Marmot',      'Trestles 30',       Decimal('280'),  'good'),
        ('Треккинговые палки Black Diamond Distance','Карбоновые складные палки',                     'Black Diamond','Distance Z',        Decimal('200'),  'excellent'),
        ('Коврик Therm-a-Rest NeoAir XLite',       'Надувной самонадувающийся',                       'Therm-a-Rest', 'NeoAir XLite',     Decimal('250'),  'excellent'),
        ('Гермомешок Sea to Summit Dry Sack 20L',  'Водонепроницаемый мешок 20 л',                    'Sea to Summit','Dry Sack 20L',      Decimal('150'),  'good'),
    ],
    'Водный спорт': [
        ('SUP-борд Starboard iGO Zen 10.8',        'Надувной SUP для прогулок',                       'Starboard',   'iGO Zen SC 10.8',   Decimal('800'),  'excellent'),
        ('Каяк Intex Explorer K2',                 'Надувной двухместный каяк',                       'Intex',       'Explorer K2',       Decimal('500'),  'good'),
        ('SUP-борд Red Paddle Co Ride 10.6',       'Жёсткий универсальный SUP',                       'Red Paddle Co','Ride 10.6',         Decimal('950'),  'excellent'),
        ('Каяк Sevylor Colorado',                  'Двухместный надувной каяк',                       'Sevylor',     'Colorado',          Decimal('450'),  'good'),
        ('SUP-борд F-One Sk8 Air',                 'Для волн и ветра',                                'F-One',       'Sk8 Air',           Decimal('1100'), 'excellent'),
        ('Байдарка Tahe Marine Yakkair HP2',       'Двухместная надувная байдарка',                   'Tahe Marine', 'Yakkair HP2',       Decimal('600'),  'good'),
        ('Виндсёрф JP Australia YoungBlood',       'Для обучения виндсёрфингу',                       'JP Australia','YoungBlood',        Decimal('900'),  'good'),
    ],
}

# Количество единиц инвентаря на каждого владельца (по индексу в OWNER_DATA)
# indices 0-10 (ЦФО+СЗФО+ПФО, 11 owners): 8 items = 88
# indices 11-16 (УФО+СФО, 6 owners): 7 items = 42
# indices 17-19 (ЮФО, 3 owners): 8+8+7 = 23
# Итого: 153
OWNER_ITEM_COUNTS = [8, 8, 8, 8, 8,  8, 8, 8, 8, 8, 8,  7, 7, 7, 7, 7, 7,  8, 8, 7]

REVIEW_COMMENTS = [
    'Отличное состояние, всё понравилось! Буду брать снова.',
    'Хороший инвентарь, рекомендую. Работает как надо.',
    'Всё прошло гладко, спасибо менеджеру за оперативность.',
    'Качественное оборудование, сдали вовремя и без проблем.',
    'Приятное обслуживание, инвентарь в хорошем состоянии.',
    'Брал лыжи на выходные — отличный выбор, всё соответствует описанию.',
    'SUP-борд в идеальном состоянии, буду рекомендовать друзьям.',
    'Велосипед чистый, хорошо настроен. Очень доволен.',
    'Ролики немного поношенные, но катаются хорошо. На 4.',
    'Самокат заряжен, всё работает. Удобно для прогулок.',
    'Палатка не пропускает воду, собирается легко. Отлично!',
    'Менеджер быстро ответил на вопросы, инвентарь в хорошем состоянии.',
    'Рюкзак немного потрёпан, но функционален. В целом нормально.',
    'Сноуборд в отличном состоянии, давно так хорошо не катался!',
    'Каяк надувался долго, но в целом всё хорошо.',
    'Рекомендую! Всё как на фото, менеджер пошёл навстречу.',
    'Электросамокат мощный, но немного шумит. На 4.',
    'Горные лыжи — топ! Карвинг просто отличный.',
    'Туристическое снаряжение в хорошем состоянии. Поход прошёл отлично.',
    'Хорошо, но хотелось бы более новое оборудование.',
    'Всё отлично, спасибо! Точно вернусь.',
    'Инвентарь соответствует описанию. Аренда прошла без нареканий.',
    'Прекрасный сервис и качественный инвентарь. Рекомендую!',
]


class Command(BaseCommand):
    help = 'Заполняет БД тестовыми данными (clean-and-seed, кроме пользователей — те upsert)'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('Начинаем заполнение БД...'))
        try:
            connection.ensure_connection()
        except OperationalError as exc:
            raise CommandError(
                'Не удалось подключиться к PostgreSQL. Проверьте sportrent/.env.\n'
                f'Детали: {exc}'
            ) from exc

        self._clear_data()
        self.create_users()
        self.create_categories()
        self.create_cities()
        self.create_pickup_points()
        self.create_inventory()
        self.create_rentals()
        self.create_reviews()
        self.create_chats()
        self.create_payment_intents()

        self.stdout.write(self.style.SUCCESS('\nБаза данных успешно заполнена!'))
        self.stdout.write('Открыть сайт: http://localhost/')
        self.stdout.write('')
        self.stdout.write('Тестовые аккаунты:')
        self.stdout.write('  admin@sportrent.ru        / admin123')
        self.stdout.write('  manager1@sportrent.ru     / manager123  (ЦФО: Москва, Воронеж, Ярославль, Тула)')
        self.stdout.write('  manager_szfo@sportrent.ru / manager123  (СЗФО: Санкт-Петербург)')
        self.stdout.write('  manager_pfo@sportrent.ru  / manager123  (ПФО: Казань, НН, Самара, Уфа, Пермь, Саратов)')
        self.stdout.write('  manager_ufo@sportrent.ru  / manager123  (УФО: Екатеринбург, Челябинск, Тюмень)')
        self.stdout.write('  manager_sfo@sportrent.ru  / manager123  (СФО: Новосибирск, Омск, Красноярск)')
        self.stdout.write('  manager_yufo@sportrent.ru / manager123  (ЮФО: Краснодар, Ростов-на-Дону, Волгоград)')
        self.stdout.write('  owner1@mail.ru .. owner20@mail.ru  / owner123')
        self.stdout.write('  client1@mail.ru .. client15@mail.ru / client123')

    # ─── Очистка ────────────────────────────────────────────────────────────

    def _clear_data(self):
        """Удаляет все данные кроме пользователей и их профилей."""
        self.stdout.write('Очищаем данные...')
        # Строгий порядок по PROTECT-связям
        from payments.models import PaymentIntent
        PaymentIntent.objects.all().delete()
        ChatMessage.objects.all().delete()
        Review.objects.all().delete()
        Payment.objects.all().delete()
        DamageReport.objects.all().delete()
        Reservation.objects.all().delete()
        Contract.objects.all().delete()
        Rental.objects.all().delete()
        Inventory.objects.all().delete()
        PickupPoint.objects.all().delete()
        City.objects.all().delete()
        SportCategory.objects.all().delete()
        self.stdout.write(self.style.WARNING('  Данные очищены.'))

    # ─── Пользователи ───────────────────────────────────────────────────────

    def create_users(self):
        self.stdout.write('Создаём пользователей...')

        # Администратор
        admin_user, created = User.objects.get_or_create(
            email='admin@sportrent.ru',
            defaults={'role': 'administrator', 'is_staff': True, 'is_superuser': True}
        )
        if created:
            admin_user.set_password('admin123')
            admin_user.save()
        Administrator.objects.get_or_create(
            user=admin_user,
            defaults={'full_name': 'Администратор Системы', 'email_work': 'admin@sportrent.ru'}
        )

        # Менеджеры — district → Manager
        self.managers = {}
        for email, password, full_name, district, phone in MANAGER_DATA:
            phone = _norm_phone(phone)
            user, created = User.objects.get_or_create(
                email=email, defaults={'role': 'manager', 'is_staff': True}
            )
            if created:
                user.set_password(password)
                user.save()
            if not user.phone:
                user.phone = phone
                user.save(update_fields=['phone'])
            manager, _ = Manager.objects.get_or_create(
                user=user,
                defaults={'full_name': full_name, 'phone_work': phone, 'email_work': email}
            )
            # manager1 видит все заявки и аренды
            if email == 'manager1@sportrent.ru' and not manager.is_super_manager:
                manager.is_super_manager = True
                manager.save(update_fields=['is_super_manager'])
            self.managers[district] = manager

        # Владельцы
        for idx, (email, full_name, city_name, tax_number) in enumerate(OWNER_DATA, start=1):
            user, created = User.objects.get_or_create(
                email=email, defaults={'role': 'owner'}
            )
            if created:
                user.set_password('owner123')
                user.save()
            if not user.phone:
                user.phone = f'+79{200000000 + idx:09d}'
                user.save(update_fields=['phone'])
            owner, _ = Owner.objects.get_or_create(
                user=user,
                defaults={'full_name': full_name, 'tax_number': tax_number, 'verified': True}
            )
            if not owner.tax_number:
                try:
                    owner.tax_number = tax_number
                    owner.save(update_fields=['tax_number'])
                except Exception:
                    pass
            if not OwnerAgreement.objects.filter(owner=owner, is_accepted=True).exists():
                OwnerAgreement.objects.create(
                    owner=owner,
                    owner_percentage=70,
                    store_percentage=30,
                    agreement_text='Соглашение о выплатах: 70% владельцу, 30% платформе.',
                    is_accepted=True,
                    accepted_date=timezone.now() - timedelta(days=random.randint(30, 365)),
                )
            if not BankAccount.objects.filter(owner=owner).exists():
                BankAccount.objects.create(
                    owner=owner,
                    bank_name='Сбербанк',
                    account_number=f'4081-7810-{idx:04d}-{idx * 7:04d}',
                    recipient_name=full_name,
                    is_default=True,
                )

            # Паспортные данные (демо) — заполняем если ещё нет
            if not owner.passport_series:
                p_series, p_region = CITY_PASSPORT_INFO.get(city_name, (f'{5000 + idx:04d}', city_name))
                p_number = f'{100000 + idx:06d}'
                p_issue_date = (timezone.now() - timedelta(days=365 * random.randint(3, 15))).date()
                p_dept_code = f'{100 + idx:03d}-{200 + idx:03d}'
                p_issued_by = f'ОУФМС по {p_region} (ДЕМО)'
                owner.passport_series = p_series
                owner.passport_number = p_number
                owner.passport_issue_date = p_issue_date
                owner.passport_department_code = p_dept_code
                owner.passport_issued_by = p_issued_by
                owner.passport_nda_accepted_at = (
                    timezone.now() - timedelta(days=random.randint(30, 365))
                )
                owner.passport_nda_version = '1.0'
                owner.save(update_fields=[
                    'passport_series', 'passport_number', 'passport_issue_date',
                    'passport_department_code', 'passport_issued_by',
                    'passport_nda_accepted_at', 'passport_nda_version',
                ])

        # Клиенты
        for idx, (email, full_name) in enumerate(CLIENT_DATA, start=1):
            user, created = User.objects.get_or_create(
                email=email, defaults={'role': 'client'}
            )
            if created:
                user.set_password('client123')
                user.save()
            if not user.phone:
                user.phone = f'+79{100000000 + idx:09d}'
                user.save(update_fields=['phone'])
            passport_series = f'{4500 + idx:04d}'
            passport_number = f'{120000 + idx:06d}'
            passport_issue_date = (timezone.now() - timedelta(days=365 * random.randint(3, 15))).date()
            passport_dept = f'{random.randint(100, 899):03d}-{random.randint(100, 899):03d}'
            client, created_c = Client.objects.get_or_create(
                user=user,
                defaults={
                    'full_name': full_name,
                    'verified': idx <= 10,
                    'preferred_payment': random.choice(['card', 'cash', 'online']),
                    'passport_series': passport_series,
                    'passport_number': passport_number,
                    'passport_issue_date': passport_issue_date,
                    'passport_department_code': passport_dept,
                }
            )
            if not created_c and not client.passport_series:
                client.passport_series = passport_series
                client.passport_number = passport_number
                client.passport_issue_date = passport_issue_date
                client.passport_department_code = passport_dept
                client.save()

        self.stdout.write(self.style.SUCCESS(f'  Пользователей: {User.objects.count()}'))

    # ─── Категории ──────────────────────────────────────────────────────────

    def create_categories(self):
        self.stdout.write('Создаём категории...')
        cats = [
            {'name': 'Велосипеды',               'description': 'Горные, шоссейные, городские велосипеды',  'icon': 'bi-bicycle'},
            {'name': 'Лыжи',                     'description': 'Горные и беговые лыжи',                    'icon': 'bi-snow'},
            {'name': 'Сноуборды',                'description': 'Сноуборды для разных стилей катания',      'icon': 'bi-snow2'},
            {'name': 'Ролики',                   'description': 'Роликовые коньки для фитнеса и агро',      'icon': 'bi-badge-vo'},
            {'name': 'Самокаты',                 'description': 'Электросамокаты и обычные самокаты',       'icon': 'bi-scooter'},
            {'name': 'Туристическое снаряжение', 'description': 'Палатки, рюкзаки, спальники',             'icon': 'bi-backpack'},
            {'name': 'Водный спорт',             'description': 'SUP-борды, каяки, байдарки',              'icon': 'bi-water'},
        ]
        for c in cats:
            SportCategory.objects.get_or_create(name=c['name'], defaults=c)
        self.stdout.write(self.style.SUCCESS(f'  Категорий: {SportCategory.objects.count()}'))

    # ─── Города ─────────────────────────────────────────────────────────────

    def create_cities(self):
        self.stdout.write('Создаём города...')
        self.cities = {}
        for name, region, lat, lon, district, _ in CITY_DATA:
            city = City.objects.create(
                name=name, region=region,
                lat=Decimal(lat), lon=Decimal(lon),
            )
            self.cities[name] = city

        for email, _, city_name, _ in OWNER_DATA:
            city = self.cities.get(city_name)
            if city:
                Owner.objects.filter(user__email=email).update(home_city=city)

        self.stdout.write(self.style.SUCCESS(f'  Городов: {City.objects.count()}'))

    # ─── Точки выдачи ───────────────────────────────────────────────────────

    def create_pickup_points(self):
        self.stdout.write('Создаём точки выдачи...')
        self.pickup_points_by_city = {}
        for city_name, points in PICKUP_POINTS_BY_CITY.items():
            city = self.cities[city_name]
            manager = self.managers[CITY_DISTRICT[city_name]]
            self.pickup_points_by_city[city_name] = []
            for name, address, lat, lon, phone in points:
                pp = PickupPoint.objects.create(
                    city=city, manager=manager,
                    name=name, address=address,
                    lat=Decimal(lat), lon=Decimal(lon),
                    phone=_norm_phone(phone), is_active=True,
                )
                self.pickup_points_by_city[city_name].append(pp)
        self.stdout.write(self.style.SUCCESS(f'  Точек выдачи: {PickupPoint.objects.count()}'))

    # ─── Инвентарь ──────────────────────────────────────────────────────────

    def create_inventory(self):
        self.stdout.write('Создаём инвентарь...')
        from django.conf import settings

        default_img_src = Path(settings.BASE_DIR) / 'static' / 'img' / 'inventory_default.jpg'
        media_inv_dir = Path(settings.MEDIA_ROOT) / 'inventory'
        media_inv_dir.mkdir(parents=True, exist_ok=True)
        use_default_img = default_img_src.exists()
        if not use_default_img:
            self.stdout.write(self.style.WARNING(
                f'  Картинка-заглушка не найдена: {default_img_src} — image будет пустым.'
            ))

        categories = {cat.name: cat for cat in SportCategory.objects.all()}

        for owner_idx, (email, _, city_name, _) in enumerate(OWNER_DATA):
            owner = Owner.objects.get(user__email=email)
            district = CITY_DISTRICT[city_name]
            manager = self.managers[district]
            bank_account = BankAccount.objects.filter(owner=owner, is_default=True).first()
            points = self.pickup_points_by_city.get(city_name, [])
            item_count = OWNER_ITEM_COUNTS[owner_idx]
            allowed_cats = DISTRICT_CATS[district]
            rng = random.Random(42 + owner_idx * 100 + 7)

            for cat_name, (name, desc, brand, model, price, condition) in self._select_items(owner_idx, allowed_cats, item_count):
                status = rng.choices(['available', 'pending'], weights=[85, 15])[0]
                pp = rng.choice(points) if points else None
                item = Inventory.objects.create(
                    owner=owner,
                    manager=manager if status == 'available' else None,
                    category=categories[cat_name],
                    name=name, description=desc,
                    brand=brand, model=model,
                    price_per_day=price,
                    condition=condition, status=status,
                    pickup_point=pp,
                    bank_account=bank_account,
                    min_rental_days=rng.randint(1, 3),
                    max_rental_days=rng.randint(7, 30),
                    deposit_amount=(price * Decimal('0.3')).quantize(Decimal('0.01')),
                )
                if use_default_img:
                    dst = media_inv_dir / f'default_{item.pk}.jpg'
                    if not dst.exists():
                        shutil.copy(str(default_img_src), str(dst))
                    item.image = f'inventory/default_{item.pk}.jpg'
                    item.save(update_fields=['image'])

        total = Inventory.objects.count()
        avail = Inventory.objects.filter(status='available').count()
        pend  = Inventory.objects.filter(status='pending').count()
        self.stdout.write(self.style.SUCCESS(
            f'  Инвентаря: {total} (доступно: {avail}, ожидает: {pend})'
        ))

    def _select_items(self, owner_idx, allowed_cats, count):
        """Детерминированный round-robin выбор предметов для владельца."""
        rng = random.Random(42 + owner_idx * 100)
        cats = list(allowed_cats)
        rng.shuffle(cats)
        pools = {}
        for cat in cats:
            pool = list(ITEMS_BY_CAT[cat])
            rng.shuffle(pool)
            pools[cat] = pool

        selected = []
        used_names = set()
        repeats = (count // len(cats)) + 2
        for _ in range(repeats):
            if len(selected) >= count:
                break
            for cat in cats:
                if len(selected) >= count:
                    break
                for i, item in enumerate(pools[cat]):
                    if item[0] not in used_names:
                        selected.append((cat, item))
                        used_names.add(item[0])
                        pools[cat].pop(i)
                        break
        return selected[:count]

    # ─── Аренды ─────────────────────────────────────────────────────────────

    def create_rentals(self):
        self.stdout.write('Создаём аренды...')
        rng = random.Random(99)
        now = timezone.now()

        clients = list(Client.objects.all())
        all_managers = list(Manager.objects.all())
        available_items = list(
            Inventory.objects.filter(status='available')
            .select_related('owner', 'pickup_point__city', 'owner__home_city')
        )

        if not clients or not available_items:
            self.stdout.write(self.style.WARNING('  Нет клиентов или инвентаря — пропуск.'))
            self._completed_rentals = []
            self._active_rentals = []
            return

        def get_manager(item):
            city_obj = None
            if item.pickup_point_id:
                city_obj = item.pickup_point.city
            elif item.owner.home_city_id:
                city_obj = item.owner.home_city
            if city_obj:
                d = CITY_DISTRICT.get(city_obj.name)
                if d and d in self.managers:
                    return self.managers[d]
            return all_managers[0]

        # ── 35 завершённых
        completed_rentals = []
        for _ in range(35):
            client = rng.choice(clients)
            item = rng.choice(available_items)
            days_ago = rng.randint(10, 90)
            rent_days = rng.randint(2, 14)
            start = now - timedelta(days=days_ago)
            end = start + timedelta(days=rent_days)
            total = item.price_per_day * rent_days
            bank_acc = BankAccount.objects.filter(owner=item.owner, is_default=True).first()
            rental = Rental.objects.create(
                inventory=item, client=client,
                manager=get_manager(item),
                start_date=start, end_date=end,
                actual_return_date=end,
                total_price=total,
                deposit_paid=item.deposit_amount,
                status='completed', payment_status='paid',
                bank_account=bank_acc,
            )
            Payment.objects.create(
                rental=rental, amount=total,
                payment_method=rng.choice(['card', 'online', 'transfer']),
                status='completed', payment_date=start,
                transaction_id=f'TXN-{rental.rental_id.hex[:12].upper()}',
            )
            agreement = OwnerAgreement.objects.filter(owner=item.owner, is_accepted=True).first()
            pct = Decimal(str((agreement.owner_percentage if agreement else 70) / 100))
            item.owner.total_earnings += (total * pct).quantize(Decimal('0.01'))
            item.owner.save(update_fields=['total_earnings'])
            completed_rentals.append(rental)

        # ── 12 активных (меняем статус инвентаря на 'rented')
        rng.shuffle(available_items)
        active_pool = available_items[:12]
        active_rentals = []
        for item in active_pool:
            client = rng.choice(clients)
            days_ago = rng.randint(1, 5)
            rent_days = rng.randint(5, 12)
            start = now - timedelta(days=days_ago)
            end = now + timedelta(days=rent_days - days_ago)
            total = item.price_per_day * rent_days
            bank_acc = BankAccount.objects.filter(owner=item.owner, is_default=True).first()
            rental = Rental.objects.create(
                inventory=item, client=client,
                manager=get_manager(item),
                start_date=start, end_date=end,
                total_price=total,
                deposit_paid=item.deposit_amount,
                status='active', payment_status='paid',
                bank_account=bank_acc,
            )
            Payment.objects.create(
                rental=rental, amount=total,
                payment_method=rng.choice(['card', 'online']),
                status='completed', payment_date=start,
                transaction_id=f'TXN-{rental.rental_id.hex[:12].upper()}',
            )
            item.status = 'rented'
            item.save(update_fields=['status'])
            active_rentals.append(rental)

        # ── 8 подтверждённых (будущие)
        confirmed_pool = available_items[12:20]
        for item in confirmed_pool:
            client = rng.choice(clients)
            days_ahead = rng.randint(3, 15)
            rent_days = rng.randint(3, 10)
            start = now + timedelta(days=days_ahead)
            end = start + timedelta(days=rent_days)
            total = item.price_per_day * rent_days
            bank_acc = BankAccount.objects.filter(owner=item.owner, is_default=True).first()
            rental = Rental.objects.create(
                inventory=item, client=client,
                manager=get_manager(item),
                start_date=start, end_date=end,
                total_price=total,
                deposit_paid=item.deposit_amount,
                status='confirmed', payment_status='paid',
                bank_account=bank_acc,
            )
            Payment.objects.create(
                rental=rental, amount=item.deposit_amount,
                payment_method=rng.choice(['card', 'online']),
                status='completed', payment_date=now,
                transaction_id=f'TXN-{rental.rental_id.hex[:12].upper()}',
            )

        # ── Демо-аренды для проверки штрафов за просрочку ──────────────────
        overdue_pool = available_items[20:24]
        if len(overdue_pool) >= 4:
            # 1. Просроченная аренда без оплаты штрафа (3 дня назад должны были вернуть)
            item1 = overdue_pool[0]
            c1 = rng.choice(clients)
            overdue_rental_1 = Rental.objects.create(
                inventory=item1, client=c1,
                manager=get_manager(item1),
                start_date=now - timedelta(days=8),
                end_date=now - timedelta(days=3),
                total_price=item1.price_per_day * 5,
                deposit_paid=item1.deposit_amount,
                status='active', payment_status='paid',
                bank_account=BankAccount.objects.filter(owner=item1.owner, is_default=True).first(),
            )
            Payment.objects.create(
                rental=overdue_rental_1, amount=overdue_rental_1.total_price,
                payment_method='online', status='completed', payment_date=now - timedelta(days=8),
                transaction_id=f'TXN-OVD1-{overdue_rental_1.rental_id.hex[:8].upper()}',
            )
            item1.status = 'rented'
            item1.save(update_fields=['status'])

            # 2. Просроченная аренда с частично оплаченным штрафом (оплатили 5 дней назад, ещё 2 дня накапало)
            item2 = overdue_pool[1]
            c2 = rng.choice(clients)
            paid_at = now - timedelta(days=2)
            overdue_rental_2 = Rental.objects.create(
                inventory=item2, client=c2,
                manager=get_manager(item2),
                start_date=now - timedelta(days=12),
                end_date=now - timedelta(days=7),
                total_price=item2.price_per_day * 5,
                deposit_paid=item2.deposit_amount,
                status='active', payment_status='paid',
                overdue_fee_paid_at=paid_at,
                overdue_fee_snapshot=item2.price_per_day * 5,
                bank_account=BankAccount.objects.filter(owner=item2.owner, is_default=True).first(),
            )
            Payment.objects.create(
                rental=overdue_rental_2, amount=overdue_rental_2.total_price,
                payment_method='online', status='completed', payment_date=now - timedelta(days=12),
                transaction_id=f'TXN-OVD2-{overdue_rental_2.rental_id.hex[:8].upper()}',
            )
            item2.status = 'rented'
            item2.save(update_fields=['status'])

            # 3. Аренда с неоплаченной доплатой за продление
            item3 = overdue_pool[2]
            c3 = rng.choice(clients)
            overdue_rental_3 = Rental.objects.create(
                inventory=item3, client=c3,
                manager=get_manager(item3),
                start_date=now - timedelta(days=6),
                end_date=now + timedelta(days=4),
                total_price=item3.price_per_day * 6,
                deposit_paid=item3.deposit_amount,
                status='active', payment_status='delayed',
                additional_payment=item3.price_per_day * 4,
                additional_payment_paid=False,
                bank_account=BankAccount.objects.filter(owner=item3.owner, is_default=True).first(),
            )
            Payment.objects.create(
                rental=overdue_rental_3, amount=overdue_rental_3.total_price,
                payment_method='card', status='completed', payment_date=now - timedelta(days=6),
                transaction_id=f'TXN-EXT3-{overdue_rental_3.rental_id.hex[:8].upper()}',
            )
            item3.status = 'rented'
            item3.save(update_fields=['status'])

            # 4. Аренда, где менеджер простил штраф через продление (end_date перенесли вперёд)
            item4 = overdue_pool[3]
            c4 = rng.choice(clients)
            overdue_rental_4 = Rental.objects.create(
                inventory=item4, client=c4,
                manager=get_manager(item4),
                start_date=now - timedelta(days=10),
                end_date=now + timedelta(days=3),  # продлено — просрочки больше нет
                total_price=item4.price_per_day * 10,
                deposit_paid=item4.deposit_amount,
                status='active', payment_status='paid',
                additional_payment=item4.price_per_day * 3,
                additional_payment_paid=True,
                bank_account=BankAccount.objects.filter(owner=item4.owner, is_default=True).first(),
            )
            Payment.objects.create(
                rental=overdue_rental_4, amount=overdue_rental_4.total_price,
                payment_method='card', status='completed', payment_date=now - timedelta(days=10),
                transaction_id=f'TXN-FRG4-{overdue_rental_4.rental_id.hex[:8].upper()}',
            )
            item4.status = 'rented'
            item4.save(update_fields=['status'])
            active_rentals += [overdue_rental_1, overdue_rental_2, overdue_rental_3, overdue_rental_4]

        self._completed_rentals = completed_rentals
        self._active_rentals = active_rentals
        self.stdout.write(self.style.SUCCESS(
            f'  Аренд: {Rental.objects.count()} '
            f'(завершено: 35, активно: {len(active_rentals)}, подтверждено: {len(confirmed_pool)}, '
            f'из них демо-просрочок: {min(4, len(overdue_pool))})'
        ))

    # ─── Отзывы ─────────────────────────────────────────────────────────────

    def create_reviews(self):
        self.stdout.write('Создаём отзывы...')
        from reviews.utils import update_inventory_rating
        rng = random.Random(77)

        completed = list(getattr(self, '_completed_rentals', []))
        rng.shuffle(completed)

        for rental in completed[:23]:
            rating = rng.choices([3, 4, 5], weights=[25, 40, 35])[0]
            Review.objects.create(
                rental=rental,
                reviewer=rental.client.user,
                target_type='inventory',
                reviewed_id=rental.inventory.inventory_id,
                rating=rating,
                comment=rng.choice(REVIEW_COMMENTS),
                status='published',
                punctuality_rating=min(5, max(1, rating + rng.randint(-1, 1))),
                condition_rating=min(5, max(1, rating + rng.randint(-1, 1))),
                communication_rating=min(5, max(1, rating + rng.randint(-1, 1))),
            )

        for inventory in Inventory.objects.all():
            update_inventory_rating(inventory)

        self.stdout.write(self.style.SUCCESS(f'  Отзывов: {Review.objects.count()}'))

    # ─── Чаты ───────────────────────────────────────────────────────────────

    def create_chats(self):
        self.stdout.write('Создаём чаты...')
        active = getattr(self, '_active_rentals', [])
        if len(active) < 2:
            self.stdout.write(self.style.WARNING('  Недостаточно активных аренд — пропуск.'))
            return

        dialogs = [
            (active[0], [
                (True,  'Добрый день! По какому адресу забрать инвентарь?'),
                (False, 'Здравствуйте! Адрес точки: {address}. Режим работы 10:00–20:00.'),
                (True,  'Спасибо! Нужен ли какой-то документ?'),
                (False, 'Достаточно паспорта. Менеджер встретит вас.'),
                (True,  'Отлично, буду в 15:00!'),
            ]),
            (active[1], [
                (True,  'Здравствуйте, можно продлить аренду на 2 дня?'),
                (False, 'Добрый день! Да, продление возможно. Стоимость — {price} ₽/день.'),
                (True,  'Хорошо, давайте продлим.'),
                (False, 'Продление оформлено. Спасибо, что предупредили заранее!'),
            ]),
        ]

        for rental, messages in dialogs:
            if not rental.manager:
                continue
            client_user = rental.client.user
            manager_user = rental.manager.user
            address = rental.inventory.pickup_point.address if rental.inventory.pickup_point else 'уточняется'
            price = rental.inventory.price_per_day

            for i, (from_client, text) in enumerate(messages):
                sender = client_user if from_client else manager_user
                receiver = manager_user if from_client else client_user
                sent = rental.start_date - timedelta(hours=len(messages) - i)
                ChatMessage.objects.create(
                    rental=rental, sender=sender, receiver=receiver,
                    message_text=text.format(address=address, price=price),
                    sent_date=sent,
                    is_read=True,
                    read_date=sent + timedelta(minutes=5),
                )

        self.stdout.write(self.style.SUCCESS(f'  Сообщений в чате: {ChatMessage.objects.count()}'))

    # ─── Платежи ЮКасса (тестовые) ──────────────────────────────────────────

    def create_payment_intents(self):
        self.stdout.write('Создаём тестовые PaymentIntent...')
        from payments.models import PaymentIntent
        from rentals.models import PaymentHistory

        rng = random.Random(99)

        paid_rentals = list(Rental.objects.filter(payment_status='paid').select_related('client__user')[:5])
        if not paid_rentals:
            self.stdout.write(self.style.WARNING('  Нет оплаченных аренд — пропуск.'))
            return

        now = timezone.now()

        # 3 успешно оплаченные аренды — основная оплата
        for rental in paid_rentals[:3]:
            fake_yookassa_id = f'2a{str(rng.randint(10**17, 10**18-1))[:9]}-000f-5000-8000-{str(rng.randint(10**11, 10**12-1))}'
            PaymentIntent.objects.create(
                rental=rental,
                user=rental.client.user,
                amount=rental.total_price,
                purpose='rental_main',
                yookassa_payment_id=fake_yookassa_id,
                status='succeeded',
                raw_webhook_data={'event': 'payment.succeeded', 'demo': True},
                created_at=rental.created_date,
            )

        # 1 аренда с оплаченной доплатой за продление
        ext_rental = Rental.objects.filter(additional_payment__gt=0).first()
        if ext_rental:
            fake_id = f'2a{str(rng.randint(10**17, 10**18-1))[:9]}-000f-5000-8001-{str(rng.randint(10**11, 10**12-1))}'
            PaymentIntent.objects.create(
                rental=ext_rental,
                user=ext_rental.client.user,
                amount=ext_rental.additional_payment,
                purpose='extension',
                yookassa_payment_id=fake_id,
                status='succeeded',
                raw_webhook_data={'event': 'payment.succeeded', 'demo': True},
            )
            if not PaymentHistory.objects.filter(rental=ext_rental, payment_type='extension_card').exists():
                PaymentHistory.objects.create(
                    rental=ext_rental,
                    amount=ext_rental.additional_payment,
                    payment_type='extension_card',
                    paid_at=now,
                )

        # 1 аренда с оплаченным штрафом
        ov_rental = Rental.objects.filter(overdue_fee_paid_at__isnull=False).first()
        if ov_rental:
            fake_id = f'2a{str(rng.randint(10**17, 10**18-1))[:9]}-000f-5000-8002-{str(rng.randint(10**11, 10**12-1))}'
            PaymentIntent.objects.create(
                rental=ov_rental,
                user=ov_rental.client.user,
                amount=ov_rental.overdue_fee_snapshot or Decimal('0'),
                purpose='overdue',
                yookassa_payment_id=fake_id,
                status='succeeded',
                raw_webhook_data={'event': 'payment.succeeded', 'demo': True},
            )

        # 1 отменённый платёж
        any_rental = paid_rentals[-1]
        fake_id_c = f'2a{str(rng.randint(10**17, 10**18-1))[:9]}-000f-5000-8003-{str(rng.randint(10**11, 10**12-1))}'
        PaymentIntent.objects.create(
            rental=any_rental,
            user=any_rental.client.user,
            amount=any_rental.total_price,
            purpose='rental_main',
            yookassa_payment_id=fake_id_c,
            status='canceled',
            raw_webhook_data={'event': 'payment.canceled', 'demo': True},
        )

        self.stdout.write(self.style.SUCCESS(f'  PaymentIntent: {PaymentIntent.objects.count()}'))

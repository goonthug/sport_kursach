"""
Утилиты для экспорта данных в XLSX и PDF.
"""

from io import BytesIO
from django.http import HttpResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill
from datetime import datetime


def export_inventory_to_xlsx(inventory_qs):
    """
    Экспорт списка инвентаря в XLSX.
    """
    # Создаем workbook и активный лист
    wb = Workbook()
    ws = wb.active
    ws.title = "Инвентарь"

    # Заголовки
    headers = ['Название', 'Категория', 'Бренд', 'Модель', 'Состояние', 'Цена/день', 'Статус', 'Рейтинг', 'Аренд']
    ws.append(headers)

    # Стили заголовка
    header_fill = PatternFill(start_color='2C5F7C', end_color='2C5F7C', fill_type='solid')
    header_font = Font(bold=True, color='FFFFFF')

    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal='center', vertical='center')

    # Данные
    for item in inventory_qs:
        ws.append([
            item.name,
            item.category.name,
            item.brand or '-',
            item.model or '-',
            item.get_condition_display(),
            float(item.price_per_day),
            item.get_status_display(),
            float(item.avg_rating) if item.avg_rating else '-',
            item.total_rentals,
        ])

    # Автоширина колонок
    for column in ws.columns:
        max_length = 0
        column_letter = column[0].column_letter
        for cell in column:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = min(max_length + 2, 50)
        ws.column_dimensions[column_letter].width = adjusted_width

    # Сохраняем в BytesIO
    output = BytesIO()
    wb.save(output)
    output.seek(0)

    # Создаем HTTP response
    response = HttpResponse(
        output.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="inventory_{datetime.now().strftime("%Y%m%d")}.xlsx"'

    return response


def export_rentals_to_xlsx(rentals_qs):
    """
    Экспорт списка аренд в XLSX.
    """
    wb = Workbook()
    ws = wb.active
    ws.title = "Аренды"

    # Заголовки
    headers = ['ID', 'Инвентарь', 'Клиент', 'Дата начала', 'Дата окончания', 'Дней', 'Стоимость', 'Статус']
    ws.append(headers)

    # Стили
    header_fill = PatternFill(start_color='3A7CA5', end_color='3A7CA5', fill_type='solid')
    header_font = Font(bold=True, color='FFFFFF')

    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal='center', vertical='center')

    # Данные
    for rental in rentals_qs:
        ws.append([
            str(rental.rental_id)[:8],
            rental.inventory.name,
            rental.client.full_name,
            rental.start_date.strftime('%d.%m.%Y'),
            rental.end_date.strftime('%d.%m.%Y'),
            rental.rental_days,
            float(rental.total_price),
            rental.get_status_display(),
        ])

    # Автоширина
    for column in ws.columns:
        max_length = 0
        column_letter = column[0].column_letter
        for cell in column:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = min(max_length + 2, 50)
        ws.column_dimensions[column_letter].width = adjusted_width

    output = BytesIO()
    wb.save(output)
    output.seek(0)

    response = HttpResponse(
        output.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="rentals_{datetime.now().strftime("%Y%m%d")}.xlsx"'

    return response


def export_inventory_to_pdf(inventory_qs):
    """
    Экспорт списка инвентаря в PDF.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []

    # Стили
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#2C5F7C'),
        spaceAfter=30,
        alignment=1  # CENTER
    )

    # Заголовок
    title = Paragraph("Каталог инвентаря SportRent", title_style)
    elements.append(title)
    elements.append(Spacer(1, 0.2 * inch))

    # Дата генерации
    date_text = f"Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
    date_para = Paragraph(date_text, styles['Normal'])
    elements.append(date_para)
    elements.append(Spacer(1, 0.3 * inch))

    # Таблица данных
    data = [['Название', 'Категория', 'Цена/день', 'Статус', 'Рейтинг']]

    for item in inventory_qs[:50]:  # Ограничение для PDF
        data.append([
            item.name[:30],
            item.category.name,
            f"{item.price_per_day} руб.",
            item.get_status_display(),
            f"{item.avg_rating:.1f}" if item.avg_rating else '-'
        ])

    table = Table(data, colWidths=[2.5 * inch, 1.5 * inch, 1 * inch, 1 * inch, 0.8 * inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2C5F7C')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F4F7F9')]),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 0.3 * inch))

    # Итого
    total_text = f"Всего предметов: {inventory_qs.count()}"
    total_para = Paragraph(total_text, styles['Normal'])
    elements.append(total_para)

    # Генерация PDF
    doc.build(elements)

    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="inventory_{datetime.now().strftime("%Y%m%d")}.pdf"'

    return response


def export_stats_to_pdf(stats_data):
    """
    Экспорт статистики в PDF (для админки).
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#2C5F7C'),
        spaceAfter=30,
        alignment=1
    )

    # Заголовок
    title = Paragraph("Отчет SportRent", title_style)
    elements.append(title)
    elements.append(Spacer(1, 0.3 * inch))

    # Период
    period_text = f"Период: {datetime.now().strftime('%d.%m.%Y')}"
    elements.append(Paragraph(period_text, styles['Normal']))
    elements.append(Spacer(1, 0.3 * inch))

    # Статистика
    stats_table_data = [
        ['Показатель', 'Значение'],
        ['Всего пользователей', str(stats_data.get('total_users', 0))],
        ['Клиентов', str(stats_data.get('total_clients', 0))],
        ['Владельцев', str(stats_data.get('total_owners', 0))],
        ['Инвентаря', str(stats_data.get('total_inventory', 0))],
        ['Доступно', str(stats_data.get('available_inventory', 0))],
        ['Всего аренд', str(stats_data.get('total_rentals', 0))],
        ['Активных', str(stats_data.get('active_rentals', 0))],
        ['Завершенных', str(stats_data.get('completed_rentals', 0))],
        ['Общий доход', f"{stats_data.get('total_revenue', 0)} руб."],
    ]

    stats_table = Table(stats_table_data, colWidths=[3 * inch, 2 * inch])
    stats_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2C5F7C')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F4F7F9')]),
    ]))

    elements.append(stats_table)

    doc.build(elements)
    buffer.seek(0)

    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="stats_{datetime.now().strftime("%Y%m%d")}.pdf"'

    return response
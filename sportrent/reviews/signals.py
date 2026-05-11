"""
Сигналы для автоматического пересчёта рейтингов после изменения отзыва.
Паттерн «Наблюдатель»: Review (издатель) → пересчёт рейтинга (подписчик).
"""

import logging
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Review
from .utils import update_inventory_rating

logger = logging.getLogger('reviews')


@receiver(post_save, sender=Review)
def recalculate_rating_on_review_save(sender, instance, **kwargs):
    """
    Пересчитывает рейтинг инвентаря при сохранении отзыва.
    Срабатывает только для опубликованных отзывов на инвентарь.
    """
    if instance.target_type != 'inventory' or instance.status != 'published':
        return

    try:
        from inventory.models import Inventory
        inventory = Inventory.objects.get(inventory_id=instance.reviewed_id)
        update_inventory_rating(inventory)
        logger.debug('Рейтинг инвентаря %s пересчитан по сигналу', inventory.inventory_id)
    except Exception as e:
        logger.error('Ошибка при пересчёте рейтинга через сигнал: %s', e)

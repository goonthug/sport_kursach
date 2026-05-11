"""
MongoDB logging handler — пишет WARNING+ логи в коллекцию application_logs.
Если MongoDB недоступна, молча пропускает запись и не роняет приложение.
"""

import logging
from datetime import datetime, timezone

# Ленивый синглтон: подключаемся к Mongo только при первом логе
_collection = None


def _get_collection():
    global _collection
    if _collection is not None:
        return _collection

    from django.conf import settings
    import pymongo

    client = pymongo.MongoClient(settings.MONGO_URL, serverSelectionTimeoutMS=2000)
    _collection = client[settings.MONGO_DB]['application_logs']
    return _collection


class MongoDBHandler(logging.Handler):
    """Отправляет лог-записи в MongoDB коллекцию application_logs."""

    def emit(self, record):
        try:
            col = _get_collection()
            col.insert_one({
                'timestamp': datetime.fromtimestamp(record.created, tz=timezone.utc),
                'level': record.levelname,
                'logger': record.name,
                'module': record.module,
                'message': self.format(record),
            })
        except Exception:
            # handleError пишет в stderr — не прерываем приложение
            self.handleError(record)

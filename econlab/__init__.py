"""Пакет для работы со стендом «Экономика страны».

    from econlab import City, MockCity, EconError

City — ваш город на стенде, MockCity — офлайн-город с честными правилами для отладки,
EconError — ошибка стенда. Подробности: help(City), help(MockCity).
"""
from .client import City, EconError
from .mock import MockCity

__all__ = ["City", "MockCity", "EconError"]

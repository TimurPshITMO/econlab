"""Пакет для ЛР 3 «Экономика страны»: подключение к стенду, офлайн-режим, статистика, графики."""
from . import plots, stats
from .client import City, EconError
from .mock import MockCity
from .shuffle import simulate_neighbors

__all__ = ["City", "MockCity", "EconError", "stats", "plots", "simulate_neighbors"]

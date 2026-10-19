"""Модель тасовки врезкой — её пишете вы (этап 2).

Модель Гилберта–Шеннона–Ридса:
  1. Колоду из n карт разрезают: число карт в верхней части ~ Bin(n, 1/2).
  2. Части сводят: пока в обеих частях есть карты, следующая карта падает из части,
     где осталось a карт, с вероятностью a / (a + b) (b — сколько осталось в другой).
     Порядок карт внутри каждой части сохраняется.
"""
import random

from .stats import neighbors_kept


def riffle(deck: list, rng: random.Random) -> list:
    """Одна тасовка врезкой. Верните НОВЫЙ список — перетасованную колоду."""
    # TODO (этап 2): реализуйте модель Гилберта–Шеннона–Ридса.
    raise NotImplementedError("Реализуйте riffle(deck, rng) в econlab/shuffle.py или переопределите её в ноутбуке.")


def simulate_neighbors(riffle_fn, k: int, n_cards: int = 36, trials: int = 2000, seed: int = 0) -> list:
    """Сохранённые соседства после k тасовок функцией riffle_fn, для trials повторов.
    Колода начинается упорядоченной: 0, 1, …, n_cards − 1."""
    rng = random.Random(seed)
    out = []
    for _ in range(trials):
        start = list(range(n_cards))
        deck = start
        for _ in range(k):
            deck = riffle_fn(deck, rng)
            if not isinstance(deck, list) or sorted(deck) != start:
                raise ValueError("Функция тасовки должна вернуть список — ту же колоду в новом порядке. "
                                 "Похоже, она ещё не дописана или теряет карты.")
        out.append(neighbors_kept(start, deck))
    return out

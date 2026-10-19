"""Небольшие статистические помощники. Формулы — из курса, ничего сверх него."""
import math

import numpy as np
import pandas as pd

Z90, Z95 = 1.645, 1.96


def mean_range(x, level: float = 0.95) -> tuple:
    """Выборочное среднее и диапазон x̄ ± z·s/√n, в который истинное ожидание попадает
    с вероятностью ≈ level (нормальное приближение, как в теореме Муавра–Лапласа)."""
    x = np.asarray(x, dtype=float)
    n = len(x)
    m = x.mean()
    if n < 2:
        return m, (math.nan, math.nan)
    z = {0.9: Z90, 0.95: Z95}.get(level, 1.96)
    se = x.std(ddof=1) / math.sqrt(n)
    return m, (m - z * se, m + z * se)


def freq_range(k: int, n: int, level: float = 0.95) -> tuple:
    """Частота k/n и диапазон p̂ ± z·√(p̂(1−p̂)/n) для вероятности (теорема Муавра–Лапласа)."""
    p = k / n
    z = {0.9: Z90, 0.95: Z95}.get(level, 1.96)
    se = math.sqrt(p * (1 - p) / n)
    return p, (p - z * se, p + z * se)


# старые имена
mean_ci, prop_ci = mean_range, freq_range


def z_score(p_hat: float, p0: float, n: int) -> float:
    """На сколько стандартных отклонений частота p̂ отличается от p0 при n наблюдениях."""
    return (p_hat - p0) / math.sqrt(p0 * (1 - p0) / n)


def pairs(xs) -> pd.DataFrame:
    """Пары соседних наблюдений (X, Y): X — значение в попытке n, Y — в попытке n+1."""
    xs = list(xs)
    return pd.DataFrame({"X": xs[:-1], "Y": xs[1:]})


def transition_table(xs, size: int = 37, normalize: bool = False) -> pd.DataFrame:
    """Таблица переходов: сколько раз за значением x следовало значение y.
    normalize=True — условные частоты P(Y = y | X = x) по строкам."""
    t = pd.crosstab(pairs(xs)["X"], pairs(xs)["Y"]).reindex(index=range(size), columns=range(size), fill_value=0)
    if normalize:
        t = t.div(t.sum(axis=1).replace(0, np.nan), axis=0)
    return t


def cumulative_mean(x) -> np.ndarray:
    """Накопленное среднее: (x1 + … + xn) / n для n = 1, 2, …"""
    x = np.asarray(x, dtype=float)
    return np.cumsum(x) / np.arange(1, len(x) + 1)


def neighbors_kept(before, after) -> int:
    """Сколько соседств «a, затем b» из порядка before сохранилось в порядке after."""
    nxt = {before[i]: before[i + 1] for i in range(len(before) - 1)}
    return sum(1 for i in range(len(after) - 1) if nxt.get(after[i]) == after[i + 1])


def normal_interval(mean: float, var: float, level: float = 0.9) -> tuple:
    """Диапазон mean ± z·√var — например, для суммы многих независимых вкладов (нормальное приближение)."""
    z = {0.9: Z90, 0.95: Z95}.get(level, 1.645)
    s = math.sqrt(var)
    return mean - z * s, mean + z * s

"""Готовые графики для отчёта."""
import matplotlib.pyplot as plt
import numpy as np

from .stats import cumulative_mean, pairs, transition_table


def _ax(ax, figsize=(7, 4)):
    if ax is None:
        _, ax = plt.subplots(figsize=figsize)
    return ax


def quarter_frequencies(quarters, ax=None):
    """Частоты кварталов фестиваля и уровень 1/37."""
    ax = _ax(ax)
    counts = np.bincount(np.asarray(quarters, dtype=int), minlength=37) / len(quarters)
    ax.bar(range(37), counts, color="#5a0a5a")
    ax.axhline(1 / 37, color="k", ls="--", lw=1, label="1/37")
    ax.set_xlabel("квартал")
    ax.set_ylabel("частота")
    ax.set_title(f"Кварталы фестиваля, n = {len(quarters)}")
    ax.legend()
    return ax


def neighbor_scatter(xs, ax=None, title="Соседние смены: (X, Y)"):
    """Диаграмма рассеяния соседних наблюдений с небольшим дрожанием точек."""
    ax = _ax(ax, (5, 5))
    p = pairs(xs)
    rng = np.random.default_rng(0)
    ax.scatter(p["X"] + rng.uniform(-.3, .3, len(p)), p["Y"] + rng.uniform(-.3, .3, len(p)),
               s=8, alpha=.5, color="#5a0a5a")
    ax.set_xlabel("X (смена n)")
    ax.set_ylabel("Y (смена n+1)")
    ax.set_title(title)
    ax.set_aspect("equal")
    return ax


def transition_heatmap(xs, size=37, ax=None):
    """Тепловая карта таблицы переходов X → Y."""
    ax = _ax(ax, (6, 5))
    t = transition_table(xs, size)
    im = ax.imshow(t.values, origin="lower", cmap="magma_r")
    ax.set_xlabel("Y (следующее значение)")
    ax.set_ylabel("X (текущее значение)")
    ax.set_title("Сколько раз за X следовало Y")
    plt.colorbar(im, ax=ax, fraction=.046)
    return ax


def cumulative_return(returns_by_label: dict, ax=None, reference=1.0):
    """Накопленная средняя выручка на 1 вложенный ящик по числу попыток для нескольких стратегий.
    returns_by_label = {"честный режим": [...], "моя стратегия": [...]}; рынок даёт ровно 1."""
    ax = _ax(ax)
    for label, r in returns_by_label.items():
        ax.plot(np.arange(1, len(r) + 1), cumulative_mean(r), label=label)
    ax.axhline(reference, color="k", ls="--", lw=1, label="рынок (1 монета за ящик)")
    ax.set_xlabel("число попыток")
    ax.set_ylabel("средняя выручка на ящик")
    ax.set_title("Накопленная средняя выручка на ящик")
    ax.legend()
    return ax


def shuffle_comparison(ks, hands_mean, hands_err, model_mean, ideal, ax=None):
    """Сохранённые соседства после k тасовок: руки (с погрешностью), модель, идеал."""
    ax = _ax(ax)
    ax.errorbar(ks[:len(hands_mean)], hands_mean, yerr=hands_err, fmt="o-", capsize=4, label="руки")
    ax.plot(ks, model_mean, "s--", label="модель")
    ax.axhline(ideal, color="k", ls=":", label="идеальное перемешивание")
    ax.set_xlabel("число тасовок k")
    ax.set_ylabel("сохранённые соседства, среднее")
    ax.set_title("Насколько перемешана колода")
    ax.legend()
    return ax

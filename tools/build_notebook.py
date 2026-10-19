"""Сборка ноутбука notebooks/lab3.ipynb из ячеек ниже.

    python tools/build_notebook.py

Разделы и номера пунктов совпадают с текстом задания (Задание/lab3.tex).
Перед выдачей студентам впишите REPO_URL в ячейку подключения.
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "notebooks" / "lab3.ipynb"
cells = []


def md(text):
    cells.append({"cell_type": "markdown", "metadata": {}, "source": text.strip("\n")})


def code(text):
    cells.append({"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [],
                  "source": text.strip("\n")})


# =====================================================================
md("""
# Лабораторная работа №3 — рабочий ноутбук

Перед началом сохраните копию: **Файл → Сохранить копию на Диске** — и работайте в ней.

Разделы ноутбука совпадают с разделами задания, номера пунктов — тоже. Код подключения к стенду,
загрузки данных и графиков уже написан; ячейки с пометкой `# TODO` заполняете вы.

Напоминание. В каждой попытке вы вкладываете от 1 до 5 ящиков товара; на рынке ящик стоит ровно
1 монету. **Результат** города — вся выручка минус всё вложенное. Запас: 600 попыток ярмарки,
600 попыток фестиваля и 60 эфиров радио; всё доступно сразу, до срока сдачи.
""")

# =====================================================================
md("""
## 0. Подключение

Ячейка ниже скачивает пакет `econlab` из репозитория курса и подключает его.
Запускайте её в начале каждой сессии Colab.
""")

code("""
REPO_URL = "https://github.com/TimurPshITMO/econlab.git"   # репозиторий курса
SERVER_URL = "https://lab-economy-im.ru"                      # стенд

import os, sys
if not os.path.exists("econlab-repo"):
    !git clone -q $REPO_URL econlab-repo
else:
    !git -C econlab-repo pull -q
sys.path.insert(0, "econlab-repo")

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from econlab import City, MockCity, EconError, stats, plots, simulate_neighbors
""")

md("""
**Токен команды** выдаёт преподаватель. Не вставляйте его прямо в код: ноутбук могут увидеть другие.
Сохраните токен в секретах Colab (значок ключа слева) под именем `ECON_TOKEN`
и разрешите ноутбуку доступ к нему.
""")

code("""
try:
    from google.colab import userdata
    TOKEN = userdata.get("ECON_TOKEN")
except Exception:
    TOKEN = input("Токен команды: ")

city = City(TOKEN, url=SERVER_URL)
city.status()
""")

md("""
Отлаживать код удобно в **офлайн-режиме**: `MockCity` повторяет правила стенда, но все активности в нём
честные, а попытки не тратятся. Эксплойт в офлайн-режиме не найти.
""")

code("""
offline = MockCity(K=city.K, seed=1)
offline.fair(kind=0, lot=1)
""")

# =====================================================================
md("""
## 1. Экономический расчёт

Пункты 1.1–1.6 решаются на бумаге. Ячейки ниже помогают проверить ответы численно.
Число $K$ вашего города — `city.K`.
""")

code("""
K = city.K
K
""")

code("""
# 1.2: распределение выручки R на 1 вложенный ящик, E R и D R как функции K
def fair_ER(K):
    ...  # TODO

def fair_DR(K):
    ...  # TODO

fair_ER(K), fair_DR(K)
""")

md("Проверка формул симуляцией: миллион попыток «на бумаге», без стенда.")

code("""
rng = np.random.default_rng(0)
matches = (rng.integers(0, 6, size=(1_000_000, 3)) == 0).sum(axis=1)
R = np.choose(matches, [0, 2, 3, K + 1])
print("E R ≈", R.mean(), "  D R ≈", R.var())
""")

code("""
# 1.3: число попыток n, при котором суммарный результат на ярмарке положителен с вероятностью ≥ 0.95,
#      по неравенству Чебышёва и по теореме Муавра–Лапласа;
#      вероятность отрицательного результата, если потратить все 600 попыток.
# TODO
""")

code("""
# 1.4: число «трёх совпадений» за 600 попыток — биномиальное распределение и приближение Пуассона;
#      вероятность ни разу не увидеть «три совпадения».
# TODO
""")

# =====================================================================
md("""
## 2. Как перемешивает радио: эксперимент с колодой

**2.2.** Для каждой серии упорядочьте колоду, сделайте $k = 1, 2, 3, 4$ тасовки врезкой и после каждой
посчитайте число **сохранённых соседств** $S_k$. Впишите результаты: один список на каждое $k$,
одно число на серию.
""")

code("""
S_hands = {   # TODO: ваши данные, не меньше 10 серий
    1: [],
    2: [],
    3: [],
    4: [],
}
pd.DataFrame({k: pd.Series(v) for k, v in S_hands.items()}).describe()
""")

md("""
**2.4.** Модель тасовки врезкой (модель Гилберта–Шеннона–Ридса):
1. число карт в верхней части разреза ~ Bin(n, 1/2);
2. пока в обеих частях есть карты, следующая карта падает из части, где осталось $a$ карт,
   с вероятностью $a/(a+b)$; порядок карт внутри частей сохраняется.
""")

code("""
import random

def riffle(deck, rng):
    # TODO (2.4): одна тасовка врезкой; верните новый список
    ...

model = {k: simulate_neighbors(riffle, k, trials=3000) for k in range(1, 8)}
pd.DataFrame({k: [np.mean(v), np.var(v, ddof=1)] for k, v in model.items()},
             index=["E S_k", "D S_k"]).round(2)
""")

code("""
# 2.5: руки / модель / идеально перемешанная колода (идеал — ответ п. 2.3)
ks = list(range(1, 8))
hands_k = [k for k in S_hands if len(S_hands[k]) > 1]
hands_mean = [np.mean(S_hands[k]) for k in hands_k]
hands_err = [1.96 * np.std(S_hands[k], ddof=1) / np.sqrt(len(S_hands[k])) for k in hands_k]
ideal = 35 / 36
plots.shuffle_comparison(ks, hands_mean, hands_err, [np.mean(model[k]) for k in ks], ideal)
plt.show()
""")

# =====================================================================
md("""
## 3. Исследование на стенде

### Фестиваль

**3.1.** Соберите не меньше 300 наблюдений. Дешевле всего ставить фургон на половину улицы с вложением 1.
""")

code("""
N = 300
for i in range(N):
    try:
        city.festival("west", 1)
    except EconError as e:
        print("Остановились:", e)
        break
fest = city.history("festival")
xs = fest["quarter"].tolist()
len(xs)
""")

code("""
# 3.2: кварталы выпадают равновероятно?
plots.quarter_frequencies(xs)
plt.show()
""")

code("""
# 3.3: корреляция номеров кварталов в соседних попытках
p = stats.pairs(xs)
print("corr(X, Y) =", round(np.corrcoef(p.X, p.Y)[0, 1], 4))
plots.neighbor_scatter(xs)
plt.show()
""")

code("""
# 3.4: проверка независимости своим способом (п. 1.6) и оценка по Муавру–Лапласу.
# Пригодятся: stats.transition_table(xs, normalize=True), plots.transition_heatmap(xs),
#             stats.freq_range(k, n), stats.z_score(p_hat, p0, n)
# TODO
""")

code("""
# 3.5: стратегия и оценка математического ожидания выручки на ящик при ней
# TODO
""")

md("""
### Радио

Каталог песен: `level` — аудитория песни (популярность от 1 до 9).
""")

code("""
catalog = city.catalog()
catalog.head()
""")

code("""
# Несколько эфиров просто слушаем, ничего не покупая
def never(played, previous, catalog, m):
    return False

for _ in range(3):
    try:
        city.play_broadcast(never)
    except EconError as e:
        print("Остановились:", e)
        break
logs = city.radio_logs()          # {номер эфира: порядок песен}
sorted(logs)
""")

code("""
# 3.6–3.7: сколько соседств предыдущего эфира сохраняется в следующем; сравните с этапом 2
kept = [stats.neighbors_kept(logs[b - 1], logs[b]) for b in sorted(logs) if b >= 1]
kept, np.mean(kept)
""")

code("""
# 3.8–3.9: правило покупки паузы. Вернуть True — купить паузу после СЛЕДУЮЩЕЙ песни.
#   played   — песни, уже прозвучавшие в этом эфире;   previous — предыдущий эфир;
#   catalog  — таблица песен (catalog.loc[id, "level"]); m — средняя аудитория ещё не прозвучавших песен.
def decide(played, previous, catalog, m):
    # TODO
    return False

b = city.play_broadcast(decide, lot=5)
b[b.buy]
""")

code("""
# Средняя выручка на ящик по купленным паузам и её разброс по Муавру–Лапласу
radio = city.history("radio")
bought = radio[radio.buy == 1]
r = bought.revenue / bought.lot
stats.mean_range(r) if len(r) > 1 else "пока нет покупок"
""")

md("""
### Заявки в Экономическую палату

По каждой активности подайте заявку: вердикт (`"exploit"` — эксплойт есть, `"fair"` — активность честная)
и текст — что вы нашли, как собирали данные, какие числа получили и почему уверены.
Заявку можно подать и на сайте стенда, в разделе «Палата».
""")

code("""
# city.claim("fair", verdict="...", text="...")
# city.claim("festival", verdict="...", text="...")
# city.claim("radio", verdict="...", text="...")
city.claims()
""")

# =====================================================================
md("""
## 4. Бюджетный план

**4.2.** Ожидаемый итоговый результат и диапазон, в который он попадёт с вероятностью 0,9
(по нормальному приближению, как в теореме Муавра–Лапласа). Если вклады попыток независимы,
их ожидания и дисперсии складываются: `stats.normal_interval(mean, var, 0.9)`.
Отправьте прогноз **до** того, как тратить оставшиеся попытки.
""")

code("""
# TODO (4.2)
# mean, var = ..., ...
# low, high = stats.normal_interval(mean, var, 0.9)
# city.forecast(mean, low, high)
city.status()
""")

md("""
**4.3.** Заготовка бота: тратит оставшиеся попытки фестиваля и радио по вашим правилам.
""")

code("""
def festival_target(history):
    # TODO: куда ставить фургон, исходя из истории попыток (таблица city.history("festival"))
    return "west"

def spend_the_rest(fest_lot=1, radio_lot=5):
    while True:
        try:
            city.festival(festival_target(city.history("festival")), fest_lot)
        except EconError:
            break
    while city.radio_state()["can_play"]:
        city.play_broadcast(decide, lot=radio_lot)
    return city.status()

# spend_the_rest(fest_lot=..., radio_lot=...)
""")

code("""
# 4.4: средняя выручка на ящик по числу попыток — честный способ игры против вашей стратегии
fest = city.history("festival")
ret = fest.revenue / fest.lot
honest = ret[fest.target.isin(["west", "east"])]
strategy = ret[~fest.target.isin(["west", "east"])]
plots.cumulative_return({"половина улицы": honest.tolist(), "моя стратегия": strategy.tolist()})
plt.show()
""")

# =====================================================================
md("""
## 5. Отчёт

Сохраните нужные графики, например `plt.savefig("figure.png", dpi=150)`, и вставьте их в отчёт.
""")

nb = {"cells": cells, "metadata": {"colab": {"provenance": []},
                                   "kernelspec": {"display_name": "Python 3", "name": "python3"},
                                   "language_info": {"name": "python"}},
      "nbformat": 4, "nbformat_minor": 0}
for c in nb["cells"]:
    lines = c["source"].split("\n")
    c["source"] = [ln + "\n" for ln in lines[:-1]] + [lines[-1]]
OUT.parent.mkdir(exist_ok=True)
OUT.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"Ноутбук: {OUT} ({len(cells)} ячеек)")

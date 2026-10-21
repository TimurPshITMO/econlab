"""Сборка ноутбука notebooks/lab2.ipynb из ячеек ниже.

    python tools/build_notebook.py

Разделы и номера пунктов совпадают с текстом задания.
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "notebooks" / "lab2.ipynb"
README = "https://github.com/TimurPshITMO/econlab#readme"
cells = []


def md(text):
    cells.append({"cell_type": "markdown", "metadata": {}, "source": text.strip("\n")})


def code(text):
    cells.append({"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [],
                  "source": text.strip("\n")})


# =====================================================================
md("""
# Лабораторная работа №2 — рабочий ноутбук

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
SERVER_URL = "https://lab-economy-im.ru"                    # стенд

import os, sys
if not os.path.exists("econlab-repo"):
    !git clone -q $REPO_URL econlab-repo
else:
    !git -C econlab-repo pull -q
sys.path.insert(0, "econlab-repo")

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats as st          # распределения: st.binom, st.poisson, st.norm
from econlab import City, MockCity, EconError
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

md(f"""
### Шпаргалка по `econlab`

| Вызов | Что делает | Что возвращает |
| --- | --- | --- |
| `city.status()` | коротко о городе | срок сдачи, результат, ступень, сколько попыток использовано, K |
| `city.K` | число K ярмарки вашего города | целое число |
| `city.fair(kind, lot)` | попытка на ярмарке: вид товара 0–5, вложение 1–5 | словарь; `["outcome"]["matches"]` — число совпадений, `["revenue"]` — выручка |
| `city.festival(target, lot)` | попытка на фестивале: квартал 0–36, `"west"` (1–18) или `"east"` (19–36) | словарь; `["outcome"]["quarter"]` — квартал сцены, `["revenue"]` — выручка |
| `city.catalog()` | каталог песен радио | таблица: индекс `id`, столбцы `title`, `artist`, `genre`, `level` (аудитория) |
| `city.play_broadcast(decide, lot)` | эфир радио целиком по вашему правилу `decide` | таблица из 36 строк: `song`, `level`, `m`, `buy`, `lot`, `revenue`, … |
| `city.radio_logs()` | порядок песен во всех прошедших эфирах | словарь `{{номер эфира: [id песен]}}`, эфир 0 — исходный порядок |
| `city.radio_state()` | состояние радио | словарь: номер эфира, `next_m`, `previous` (предыдущий эфир), … |
| `city.history(activity)` | все ваши попытки: `"fair"`, `"festival"` или `"radio"` | таблица pandas, столбцы ниже |
| `city.claim(activity, verdict, text)` | заявка в Палату | заявка со статусом |
| `city.claims()` | ваши заявки | таблица |
| `city.forecast(mean, low, high, text)` | бюджетный план (п. 4.2) — заявка в Палату с обоснованием | заявка со статусом |

Столбцы `city.history(...)`:
- `"fair"`: `idx`, `kind`, `lot`, `want1`, `want2`, `want3` (желания покупателей), `matches`, `revenue`;
- `"festival"`: `idx`, `target`, `lot`, `quarter` (квартал сцены), `revenue`;
- `"radio"`: `idx`, `broadcast`, `pos` (номер песни в эфире), `buy` (1 — пауза куплена), `lot`, `song`, `level`, `m`, `revenue`.

Ошибки стенда (закончился запас, неверное вложение, стенд закрыт) приходят как исключение `EconError`
с понятным текстом. Подробное описание любого метода: `help(city.fair)`, `help(City.play_broadcast)`.
Полный справочник — в [README репозитория]({README}).
""")

md("""
Отлаживать код удобно в **офлайн-режиме**: `MockCity` повторяет правила и ответы стенда, но все активности
в нём честные, а попытки стенда не тратятся. Эксплойт в офлайн-режиме не найти.
""")

code("""
offline = MockCity(K=city.K, seed=1)
offline.fair(kind=0, lot=1)
""")

# =====================================================================
md("""
## 1. Экономический расчёт

Пункты 1.1–1.6 решаются на бумаге. Ячейки ниже помогают проверить ответы численно.
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

md("Проверка формул моделированием: миллион попыток «на бумаге», без стенда.")

code("""
rng = np.random.default_rng(0)
matches = (rng.integers(0, 6, size=(1_000_000, 3)) == 0).sum(axis=1)   # совпадения с видом товара 0
R = np.choose(matches, [0, 2, 3, K + 1])                                # выручка на 1 ящик
print("E R ≈", R.mean(), "  D R ≈", R.var())
""")

code("""
# 1.3: число попыток n по неравенству Чебышёва
# TODO

# 1.3: моделированием оцените вероятность закончить с отрицательным результатом,
#      если потратить на ярмарку все 600 попыток с вложением 1 (например, 10 000 прогонов)
# TODO
""")

code("""
# 1.4: число «трёх совпадений» за 600 попыток: биномиальное распределение и приближение Пуассона
# Пригодятся st.binom.pmf(k, n, p) и st.poisson.pmf(k, lam)
# TODO
""")

# =====================================================================
md("""
## 2. Как перемешивает радио: эксперимент с колодой

**2.2.** Впишите результаты эксперимента: для каждого $k$ — список значений $S_k$, по одному на серию.
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
Готовые функции: подсчёт сохранённых соседств и прогон модели тасовки.
""")

code("""
import random


def neighbors_kept(before, after):
    \"\"\"Сколько соседств «a, сразу за ней b» из порядка before сохранилось в порядке after.\"\"\"
    nxt = {before[i]: before[i + 1] for i in range(len(before) - 1)}
    return sum(1 for i in range(len(after) - 1) if nxt.get(after[i]) == after[i + 1])


def simulate_neighbors(riffle, k, n_cards=36, trials=2000, seed=0):
    \"\"\"S_k в trials повторах: упорядоченная колода, k тасовок функцией riffle(deck, rng).\"\"\"
    rng = random.Random(seed)
    out = []
    for _ in range(trials):
        start = list(range(n_cards))
        deck = start
        for _ in range(k):
            deck = riffle(deck, rng)
            if not isinstance(deck, list) or sorted(deck) != start:
                raise ValueError("riffle должна вернуть список — ту же колоду в новом порядке.")
        out.append(neighbors_kept(start, deck))
    return out
""")

md("""
**2.4.** Модель тасовки врезкой (модель Гилберта–Шеннона–Ридса):
1. число карт в верхней части разреза ~ Bin(n, 1/2);
2. пока в обеих частях есть карты, следующая карта падает из части, где осталось $a$ карт,
   с вероятностью $a/(a+b)$ ($b$ — сколько осталось в другой части); порядок карт внутри частей сохраняется.

Функция `riffle(deck, rng)` получает колоду (список) и генератор `random.Random`;
случайные числа берите из него: `rng.random()`, `rng.randint(a, b)`.
""")

code("""
def riffle(deck, rng):
    # TODO (2.4): одна тасовка врезкой; верните новый список
    ...

model = {k: simulate_neighbors(riffle, k, trials=3000) for k in range(1, 8)}
pd.DataFrame({k: [np.mean(v), np.var(v, ddof=1)] for k, v in model.items()},
             index=["E S_k", "D S_k"]).round(2)
""")

code("""
# 2.5: руки, модель и идеально перемешанная колода (идеал — ответ п. 2.3)
ks = list(range(1, 8))
hands_k = [k for k in S_hands if S_hands[k]]
plt.plot(ks, [np.mean(model[k]) for k in ks], "s--", label="модель")
plt.plot(hands_k, [np.mean(S_hands[k]) for k in hands_k], "o", label="руки")
plt.axhline(35 / 36, color="k", ls=":", label="идеальное перемешивание")
plt.xlabel("число тасовок k"); plt.ylabel("сохранённые соседства, среднее"); plt.legend()
plt.show()

# TODO (2.5): с помощью модели оцените, насколько может отличаться от E S_k среднее
#             по стольким сериям, сколько провели вы
""")

# =====================================================================
md("""
## 3. Исследование на стенде

### Фестиваль

**3.1.** Соберите не меньше 300 наблюдений.
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
# 3.2: частоты кварталов
freq = pd.Series(xs).value_counts().reindex(range(37), fill_value=0) / len(xs)
plt.bar(freq.index, freq.values)
plt.axhline(1 / 37, color="k", ls="--", label="1/37")
plt.xlabel("квартал"); plt.ylabel("частота"); plt.legend()
plt.show()

# TODO (3.2)
""")

code("""
# 3.3: пары соседних попыток (X, Y) и их корреляция
pairs = pd.DataFrame({"X": xs[:-1], "Y": xs[1:]})
print("corr(X, Y) =", round(np.corrcoef(pairs.X, pairs.Y)[0, 1], 4))
plt.scatter(pairs.X, pairs.Y, s=8, alpha=.5)
plt.xlabel("X (попытка i)"); plt.ylabel("Y (попытка i + 1)"); plt.gca().set_aspect("equal")
plt.show()
""")

code("""
# 3.4: таблица переходов — сколько раз за кварталом x шёл квартал y
transitions = pd.crosstab(pairs.X, pairs.Y).reindex(index=range(37), columns=range(37), fill_value=0)

# TODO (3.4)
""")

code("""
# 3.5
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
# 3.6: сколько соседств предыдущего эфира сохраняется в следующем
kept = [neighbors_kept(logs[b - 1], logs[b]) for b in sorted(logs) if b >= 1]
kept, np.mean(kept)

# TODO (3.7)
""")

code("""
# 3.8
# TODO
""")

code("""
# 3.9: правило покупки паузы. Вернуть True — купить паузу после СЛЕДУЮЩЕЙ песни.
#   played   — песни, уже прозвучавшие в этом эфире;   previous — предыдущий эфир;
#   catalog  — таблица песен (catalog.loc[id, "level"]); m — средняя аудитория ещё не прозвучавших песен.
def decide(played, previous, catalog, m):
    # TODO
    return False

b = city.play_broadcast(decide, lot=5)
b[b.buy]
""")

code("""
# 3.9: выручка на ящик по купленным паузам
radio = city.history("radio")
bought = radio[radio.buy == 1]
r = bought.revenue / bought.lot
print("покупок:", len(r), "  средняя выручка на ящик:", r.mean() if len(r) else "—")

# TODO (3.9)
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

**4.2.** Бюджетный план — заявка в Палату: прогноз итогового результата, диапазон и обоснование.
Подайте его **до** того, как тратить оставшиеся попытки. Можно и на сайте стенда, в разделе «Палата».
""")

code("""
# TODO (4.2)
# mean, low, high = ...
# city.forecast(mean, low, high, text="...")
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
# 4.4: средняя выручка на ящик по первым n попыткам — честный способ игры и ваша стратегия
fest = city.history("festival")
ret = fest.revenue / fest.lot
honest = ret[fest.target.isin(["west", "east"])].to_numpy()
strategy = ret[~fest.target.isin(["west", "east"])].to_numpy()
for label, r in [("половина улицы", honest), ("моя стратегия", strategy)]:
    plt.plot(np.arange(1, len(r) + 1), np.cumsum(r) / np.arange(1, len(r) + 1), label=label)
plt.axhline(1, color="k", ls="--", lw=1, label="рынок (1 монета за ящик)")
plt.xlabel("число попыток n"); plt.ylabel("средняя выручка на ящик"); plt.legend()
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

"""Подключение к стенду: класс City — ваш город."""
import time

import pandas as pd
import requests

DEFAULT_URL = "https://lab-economy-im.ru"


class EconError(Exception):
    """Ошибка, которую вернул стенд или пакет. Текст ошибки объясняет, что не так.

    Атрибуты:
        message — текст ошибки;
        code    — короткий код или None:
                  "limit"       — запас попыток этой активности закончился;
                  "not_started" — стенд для вашей страны ещё не открыт;
                  "closed"      — срок сдачи прошёл, попытки закрыты;
                  "bad_lot"     — вложение не целое число от 1 до 5;
                  "bad_kind"    — вид товара ярмарки не от 0 до 5;
                  "bad_target"  — неверная цель фестиваля;
                  "in_progress" — эфир радио уже начат (доиграйте его через radio_step);
        status  — HTTP-код ответа стенда (400 — неверный ввод или правила игры, 401 — токен не найден)
                  или None, если до стенда не удалось достучаться.

        try:
            city.festival("west", 1)
        except EconError as e:
            print(e.code, e.message)
    """

    def __init__(self, message, code=None, status=None):
        super().__init__(message)
        self.message, self.code, self.status = message, code, status


class City:
    """Ваш город на стенде.

        city = City(TOKEN)                       # стенд https://lab-economy-im.ru
        city.status()                            # срок, результат, сколько попыток использовано
        city.fair(kind=3, lot=1)                 # попытка на ярмарке
        city.festival(target="west", lot=1)      # попытка на фестивале
        city.play_broadcast(decide, lot=5)       # эфир радио по вашему правилу
        city.history("festival")                 # история попыток таблицей pandas

    Аргументы:
        token       — токен команды (выдаёт преподаватель);
        url         — адрес стенда, по умолчанию https://lab-economy-im.ru;
        max_per_sec — не больше стольких запросов в секунду. Если стенд всё же ответит
                      «слишком много запросов», пакет сам подождёт и повторит запрос;
        verbose     — True: печатать ответ стенда на каждую попытку.

    Подробности о любом методе: help(city.fair), help(City.play_broadcast) и т. д.
    """

    def __init__(self, token: str, url: str = DEFAULT_URL, session=None, max_per_sec: float = 20.0,
                 verbose: bool = False):
        self.url = url.rstrip("/")
        self.token = token.strip()
        self._s = session or requests.Session()
        self._headers = {"Authorization": f"Bearer {self.token}"}
        self._min_gap = 1.0 / max_per_sec if max_per_sec else 0.0
        self._last = 0.0
        self.verbose = verbose

    # ---------------- низкий уровень ----------------
    def request(self, method: str, path: str, json=None, params=None):
        """Запрос к API стенда (служебный метод, обычно не нужен). Возвращает разобранный JSON."""
        for attempt in range(30):
            gap = self._min_gap - (time.monotonic() - self._last)
            if gap > 0:
                time.sleep(gap)
            self._last = time.monotonic()
            try:
                r = self._s.request(method, self.url + path, json=json, params=params,
                                    headers=self._headers, timeout=30)
            except requests.RequestException as e:
                if attempt < 3:
                    time.sleep(1 + attempt)
                    continue
                raise EconError(f"Не удалось связаться со стендом: {e}") from None
            if r.status_code == 429:
                time.sleep(0.5)
                continue
            break
        if r.status_code >= 400:
            try:
                body = r.json()
                msg, code = body.get("detail", r.text), body.get("code")
            except ValueError:
                msg, code = r.text, None
            if isinstance(msg, list):  # ошибка формата запроса
                msg = "; ".join(f"{'.'.join(map(str, e.get('loc', [])))}: {e.get('msg')}" for e in msg)
            raise EconError(msg, code, r.status_code)
        if "text/csv" in r.headers.get("content-type", ""):
            return r.text
        return r.json()

    # ---------------- город ----------------
    def me(self) -> dict:
        """Полная карточка города (словарь).

        Ключи:
            "city"    — название, команда, герб;
            "country" — страна: "name", "status" ("not_started" / "open" / "closed"),
                        "start_at", "deadline_at" (время московское);
            "rules"   — "fair_K", "lot_min", "lot_max", "fair_total", "festival_total",
                        "radio_broadcasts", "radio_songs";
            "stats"   — "overprofit" (результат города), "invested", "revenue",
                        "by_activity" (то же по каждой активности), "usage" (сколько попыток
                        использовано), "limits" (сколько осталось), "tier" (ступень города);
            "rewards" — достопримечательности города.
        """
        return self.request("GET", "/api/me")

    def status(self) -> dict:
        """Коротко о городе: срок сдачи, результат, ступень, сколько попыток использовано, K ярмарки.

        Результат — вся выручка минус всё вложенное (0 — то же, что продать весь товар на рынке).
        """
        m = self.me()
        st, u = m["stats"], m["stats"]["usage"]
        out = {
            "город": m["city"]["label"], "страна": m["country"]["name"],
            "срок сдачи": m["country"]["deadline_at"],
            "результат": st["overprofit"], "ступень": st["tier"]["name"],
            "ярмарка": f'{u["fair"]["used"]} из {u["fair"]["total"]} попыток',
            "фестиваль": f'{u["festival"]["used"]} из {u["festival"]["total"]} попыток',
            "радио": f'{u["radio"]["broadcasts_used"]} из {u["radio"]["broadcasts_total"]} эфиров',
            "K ярмарки": m["rules"]["fair_K"],
        }
        if m["country"]["status"] == "not_started":
            out["стенд"] = "ещё не открыт"
        elif m["country"]["status"] == "closed":
            out["стенд"] = "срок сдачи прошёл"
        return out

    @property
    def K(self) -> int:
        """Число K ярмарки вашего города: при трёх совпадениях выручка (K + 1)·s."""
        return self.me()["rules"]["fair_K"]

    def rename(self, name: str = None, coat: dict = None) -> dict:
        """Название и герб города (то же можно сделать на сайте стенда).

        name — от 2 до 40 символов;
        coat — {"shape": форма щита, "figure": фигура, "color": "#RRGGBB", "motto": девиз до 60 символов}.
               Формы: "heater", "round", "french", "banner".
               Фигуры: "tower", "wave", "star", "key", "sun", "tree", "anchor", "bird", "bell", "dice".
        Возвращает карточку города, как me().
        """
        return self.request("PATCH", "/api/city", json={"name": name, "coat": coat})

    # ---------------- активности ----------------
    def fair(self, kind: int, lot: int = 1) -> dict:
        """Попытка на ярмарке.

        kind — вид товара, целое от 0 до 5;
        lot  — вложение s, целое от 1 до 5 ящиков.

        Возвращает словарь:
            "idx"      — номер попытки ярмарки (с 0);
            "choice"   — {"kind", "lot"};
            "outcome"  — {"wants": [вид товара каждого из трёх покупателей], "matches": число совпадений};
            "invested" — вложено ящиков; "revenue" — выручка; "profit" — revenue − invested.

            r = city.fair(kind=0, lot=1)
            r["outcome"]["matches"], r["revenue"]
        """
        return self._log(self.request("POST", "/api/fair", json={"kind": kind, "lot": lot}))

    def festival(self, target, lot: int = 1) -> dict:
        """Попытка на фестивале.

        target — куда поставить фургон: номер квартала 0–36 (выручка 36·s, если сцена там),
                 "west" — кварталы 1–18 или "east" — кварталы 19–36 (выручка 2·s, если сцена в этой половине);
        lot    — вложение s, целое от 1 до 5 ящиков.

        Возвращает словарь:
            "idx"      — номер попытки фестиваля (с 0);
            "choice"   — {"target", "lot"};
            "outcome"  — {"quarter": квартал, где была сцена, "mult": выручка на ящик};
            "invested", "revenue", "profit" — как у fair().

            r = city.festival("west", 1)
            r["outcome"]["quarter"]
        """
        return self._log(self.request("POST", "/api/festival", json={"target": target, "lot": lot}))

    # ---------------- радио ----------------
    def radio_state(self) -> dict:
        """Состояние радио перед следующим решением.

        Ключи:
            "broadcast"   — номер текущего эфира (с 1); "broadcasts_total" — сколько эфиров всего;
            "position"    — номер следующей песни в эфире (с 0); 0 — эфир ещё не начат;
            "can_play"    — можно ли сейчас слушать (эфиры не кончились и стенд открыт);
            "finished"    — все эфиры использованы;
            "next_m"      — m перед следующим решением: средняя аудитория ещё не прозвучавших песен;
            "played"      — id песен, уже прозвучавших в текущем эфире, по порядку;
            "previous"    — порядок песен (id) в предыдущем эфире;
            "catalog"     — каталог песен (список словарей, удобнее — catalog()).
        """
        return self.request("GET", "/api/radio/state")

    def radio_step(self, buy: bool, lot: int = 1) -> dict:
        """Одно решение на радио: покупать ли рекламную паузу после СЛЕДУЮЩЕЙ песни.

        Какая песня будет следующей, заранее не видно. Обычно удобнее play_broadcast().

        buy — True: купить паузу; False: не покупать (ничего не вкладывается, выручка 0);
        lot — вложение s при покупке, целое от 1 до 5.

        Возвращает словарь:
            "choice"  — {"buy", "lot"} (при buy=False lot = 0);
            "outcome" — {"broadcast", "pos": номер песни в эфире, "song": id прозвучавшей песни,
                         "level": её аудитория v, "m": m в момент решения};
            "invested", "revenue" (= 0,95·s·v/m при покупке), "profit".
        """
        return self._log(self.request("POST", "/api/radio/step", json={"buy": bool(buy), "lot": lot}))

    def radio_log(self, broadcast: int) -> list:
        """Эфирная справка: порядок песен (список id) в эфире с номером broadcast.

        Эфир 0 — исходный порядок до первого эфира. Для текущего эфира — только уже прозвучавшие песни.
        """
        return self.request("GET", "/api/radio/log", params={"broadcast": broadcast})["playlist"]

    def radio_logs(self) -> dict:
        """Все полностью прозвучавшие эфиры (и эфир 0): словарь {номер эфира: [id песен по порядку]}.

            logs = city.radio_logs()
            logs[3]          # порядок песен в эфире 3
        """
        st = self.radio_state()
        last = st["broadcast"] if st["finished"] else st["broadcast"] - 1
        return {b: self.radio_log(b) for b in range(last + 1)}

    def catalog(self) -> pd.DataFrame:
        """Каталог песен — таблица с индексом id и столбцами
        "title" (название), "artist" (исполнитель), "genre" (жанр), "level" (аудитория v, от 1 до 9).

            cat = city.catalog()
            cat.loc[5, "level"]      # аудитория песни с id 5
        """
        return pd.DataFrame(self.radio_state()["catalog"]).set_index("id")

    def play_broadcast(self, decide, lot: int = 5) -> pd.DataFrame:
        """Проиграть один эфир целиком: 36 решений подряд по вашему правилу decide.

        decide(played, previous, catalog, m) -> bool вызывается перед каждой песней и решает,
        покупать ли паузу после СЛЕДУЮЩЕЙ песни:
            played   — список id песен, уже прозвучавших в этом эфире, по порядку (в начале эфира пустой);
            previous — порядок песен (id) в предыдущем эфире;
            catalog  — каталог песен, как catalog();
            m        — средняя аудитория ещё не прозвучавших в этом эфире песен.
        lot — вложение при каждой покупке, от 1 до 5.

        Эфир должен быть не начат: если его уже начали через radio_step, доиграйте его там же.

        Возвращает таблицу из 36 строк со столбцами
            "broadcast", "pos", "song", "level", "m", "buy", "lot", "revenue".

            def never(played, previous, catalog, m):
                return False
            b = city.play_broadcast(never)
        """
        st = self.radio_state()
        if not st["can_play"]:
            raise EconError("Радио недоступно: все эфиры использованы или стенд закрыт.", "limit")
        if st["position"] != 0:
            raise EconError("Текущий эфир уже начат. Доиграйте его функцией radio_step.", "in_progress")
        cat = pd.DataFrame(st["catalog"]).set_index("id")
        levels = cat["level"].to_dict()
        played, rows = [], []
        for _ in range(len(levels)):
            rest = [s for s in levels if s not in played]
            m = sum(levels[s] for s in rest) / len(rest)
            buy = bool(decide(list(played), st["previous"], cat, m))
            r = self.radio_step(buy, lot if buy else 1)
            played.append(r["outcome"]["song"])
            rows.append({"broadcast": r["outcome"]["broadcast"], "pos": r["outcome"]["pos"],
                         "song": r["outcome"]["song"], "level": r["outcome"]["level"], "m": r["outcome"]["m"],
                         "buy": buy, "lot": r["choice"]["lot"], "revenue": r["revenue"]})
        return pd.DataFrame(rows)

    # ---------------- история ----------------
    def history(self, activity: str) -> pd.DataFrame:
        """Все ваши попытки одной активности — таблица pandas, по строке на попытку, по порядку.

        activity — "fair", "festival" или "radio". Столбцы:
            fair:     idx, kind (вид товара), lot, want1, want2, want3 (желания покупателей),
                      matches (число совпадений), revenue;
            festival: idx, target (квартал, "west" или "east"), lot, quarter (квартал сцены), revenue;
            radio:    idx, broadcast, pos (номер песни в эфире), buy (1 — пауза куплена), lot,
                      song (id песни), level (её аудитория), m, revenue.

            fest = city.history("festival")
            xs = fest["quarter"].tolist()
        """
        data = self.request("GET", f"/api/history/{activity}")
        return pd.DataFrame(data)

    # ---------------- Палата и прогноз ----------------
    def claim(self, activity: str, verdict: str, text: str) -> dict:
        """Заявка в Экономическую палату (то же можно сделать на сайте стенда).

        activity — "fair", "festival" или "radio";
        verdict  — "exploit" (эксплойт есть) или "fair" (активность честная);
        text     — что вы нашли: как собирали данные, какие числа получили, почему уверены
                   (не короче 20 символов).

        По одной активности может быть только одна заявка на проверке. Отклонённую заявку
        можно исправить и подать снова. Возвращает заявку: "id", "status" ("pending" — на проверке,
        "approved", "rejected"), "teacher_comment" и др.
        """
        return self.request("POST", "/api/claims", json={"activity": activity, "verdict": verdict, "text": text})

    def claims(self) -> pd.DataFrame:
        """Ваши заявки таблицей: activity ("fair", "festival", "radio" или "budget"), verdict, text,
        status, teacher_comment, created_at, decided_at; у бюджетного плана ещё forecast (прогноз)."""
        return pd.DataFrame(self.request("GET", "/api/claims"))

    def forecast(self, mean: float, low: float, high: float, text: str) -> dict:
        """Бюджетный план (п. 4.2) — заявка в Палату (то же можно сделать на сайте стенда).

        mean — ожидаемый итоговый результат, когда все попытки будут использованы;
        low, high — диапазон, в который итог попадёт с вероятностью не меньше 0,9; нужно low ≤ mean ≤ high;
        text — обоснование (не короче 20 символов): какие активности и вложения вы используете дальше,
               как посчитали ожидание и дисперсию, какие допущения сделали, как получили диапазон.

        Стенд запоминает, сколько попыток было использовано в момент подачи. Заявку проверяет
        преподаватель; за подтверждённый план город получает знак «Надёжный бюджет».
        После срока сдачи план не принимается.
        """
        return self.request("POST", "/api/claims", json={"activity": "budget", "text": text,
                                                         "mean": mean, "low": low, "high": high})

    # ---------------- страна ----------------
    def country(self) -> dict:
        """Карта страны: "cities" — города с их ступенями и достопримечательностями, столица и др."""
        return self.request("GET", "/api/country")

    def news(self, limit: int = 20) -> list:
        """Последние limit новостей страны: список словарей с ключами "text", "created_at" и др."""
        return self.request("GET", "/api/news", params={"limit": limit})

    # ---------------- служебное ----------------
    def _log(self, r: dict) -> dict:
        if self.verbose:
            print(r)
        return r

    def __repr__(self):
        return f"City(url={self.url!r})"

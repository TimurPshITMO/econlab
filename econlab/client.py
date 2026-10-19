"""Подключение к стенду: класс City — ваш город."""
import time

import pandas as pd
import requests

DEFAULT_URL = "https://lab-economy-im.ru"


class EconError(Exception):
    """Ошибка стенда: текст понятен без расшифровки (лимит, неверный ввод и т. п.)."""

    def __init__(self, message, code=None, status=None):
        super().__init__(message)
        self.message, self.code, self.status = message, code, status


class City:
    """Ваш город на стенде.

        city = City(token="...")   # по умолчанию стенд https://lab-economy-im.ru
        city.status()                       # день, склад, сверхприбыль, остаток лимитов
        city.fair(kind=3, lot=1)            # ярмарка
        city.festival(target="west", lot=1) # фестиваль: квартал 0–36, "west" или "east"
        city.radio_step(buy=False)          # радио: решение по следующей песне
        city.history("festival")            # история в виде таблицы pandas
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
        """Полная карточка города (словарь)."""
        return self.request("GET", "/api/me")

    def status(self) -> dict:
        """Коротко: срок, результат, сколько попыток использовано."""
        m = self.me()
        st, u = m["stats"], m["stats"]["usage"]
        out = {
            "город": m["city"]["label"], "страна": m["country"]["name"],
            "срок сдачи": m["country"]["deadline_at"],
            "результат (сверхприбыль)": st["overprofit"], "ступень": st["tier"]["name"],
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
        """Бонус ярмарки за три совпадения в вашем городе."""
        return self.me()["rules"]["fair_K"]

    def rename(self, name: str = None, coat: dict = None) -> dict:
        """Название и герб: coat = {"shape": "heater", "figure": "tower", "color": "#7a1f5c", "motto": "..."}"""
        return self.request("PATCH", "/api/city", json={"name": name, "coat": coat})

    # ---------------- активности ----------------
    def fair(self, kind: int, lot: int = 1) -> dict:
        """Ярмарка: вид товара 0–5, вложение 1–5 ящиков.
        Возвращает желания покупателей, число совпадений и выручку."""
        return self._log(self.request("POST", "/api/fair", json={"kind": kind, "lot": lot}))

    def festival(self, target, lot: int = 1) -> dict:
        """Фестиваль: target — квартал 0–36, "west" (1–18) или "east" (19–36)."""
        return self._log(self.request("POST", "/api/festival", json={"target": target, "lot": lot}))

    # ---------------- радио ----------------
    def radio_state(self) -> dict:
        """Номер эфира и позиция следующей песни, m, предыдущий эфир, каталог песен."""
        return self.request("GET", "/api/radio/state")

    def radio_step(self, buy: bool, lot: int = 1) -> dict:
        """Решение по следующей песне: купить паузу после неё (buy=True) или нет."""
        return self._log(self.request("POST", "/api/radio/step", json={"buy": bool(buy), "lot": lot}))

    def radio_log(self, broadcast: int) -> list:
        """Эфирная справка: порядок песен (их id) в эфире broadcast. Эфир 0 — исходный порядок до начала."""
        return self.request("GET", "/api/radio/log", params={"broadcast": broadcast})["playlist"]

    def radio_logs(self) -> dict:
        """Все прошедшие эфиры: {номер эфира: [id песен]}."""
        st = self.radio_state()
        last = st["broadcast"] if st["finished"] else st["broadcast"] - 1
        return {b: self.radio_log(b) for b in range(last + 1)}

    def catalog(self) -> pd.DataFrame:
        """Каталог песен: id, название, исполнитель, жанр, уровень популярности (аудитория)."""
        return pd.DataFrame(self.radio_state()["catalog"]).set_index("id")

    def play_broadcast(self, decide, lot: int = 5) -> pd.DataFrame:
        """Проиграть один эфир целиком (36 песен).

        decide(played, previous, catalog, m) -> bool  — покупать ли паузу после СЛЕДУЮЩЕЙ песни.
          played   — id песен, уже прозвучавших в этом эфире (по порядку);
          previous — предыдущий эфир (список id);
          catalog  — таблица песен (см. catalog());
          m        — средняя аудитория ещё не прозвучавших в этом эфире песен.
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
        """Ваша история попыток: activity = "fair", "festival" или "radio"."""
        data = self.request("GET", f"/api/history/{activity}")
        return pd.DataFrame(data)

    # ---------------- Палата и прогноз ----------------
    def claim(self, activity: str, verdict: str, text: str) -> dict:
        """Заявка в Экономическую палату.

        activity — "fair", "festival" или "radio";
        verdict  — "exploit" (эксплойт есть) или "fair" (активность честная);
        text     — что вы нашли: как собирали данные, какие числа получили, почему уверены.
        """
        return self.request("POST", "/api/claims", json={"activity": activity, "verdict": verdict, "text": text})

    def claims(self) -> pd.DataFrame:
        """Ваши заявки и их статусы."""
        return pd.DataFrame(self.request("GET", "/api/claims"))

    def forecast(self, mean: float, low: float, high: float) -> dict:
        """Прогноз итогового результата и диапазон [low, high], в который он попадёт с вероятностью 0,9
        (по нормальному приближению, как в теореме Муавра–Лапласа)."""
        return self.request("POST", "/api/forecast", json={"mean": mean, "low": low, "high": high})

    # ---------------- страна ----------------
    def country(self) -> dict:
        """Карта страны: города, их ступени, столица, достопримечательности."""
        return self.request("GET", "/api/country")

    def news(self, limit: int = 20) -> list:
        """Лента новостей страны."""
        return self.request("GET", "/api/news", params={"limit": limit})

    # ---------------- служебное ----------------
    def _log(self, r: dict) -> dict:
        if self.verbose:
            print(r)
        return r

    def __repr__(self):
        return f"City(url={self.url!r})"

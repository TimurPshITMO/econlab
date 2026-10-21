"""Офлайн-режим: тот же интерфейс, что у City, но город живёт у вас в ноутбуке."""
import random

from .client import City, EconError

FAIR_TOTAL = FEST_TOTAL = 600
BROADCASTS = 60
N_SONGS = 36
LEVELS = [lvl for lvl in range(1, 10) for _ in range(4)]
GENRES = ["поп", "рок", "джаз", "электроника"]


class MockCity(City):
    """Офлайн-город для отладки кода: те же методы, что у City, но без стенда и токена.

    Правила и формат ответов те же, что на стенде, но все активности здесь ЧЕСТНЫЕ: желания
    покупателей, кварталы фестиваля и порядок песен в каждом эфире выбираются независимо
    и равновероятно. Поэтому эксплойт здесь не найти. Попытки стенда не тратятся.

    K    — число K ярмарки (возьмите K своего города: MockCity(K=city.K));
    seed — зерно генератора: с одинаковым seed получаются одинаковые исходы.

    Заявки и прогнозы офлайн никуда не отправляются, только печатаются.

        offline = MockCity(K=city.K, seed=1)
        offline.festival("west", 1)
    """

    def __init__(self, K: int = 25, seed: int | None = None):
        super().__init__(token="offline", url="offline", max_per_sec=0)
        self.rng = random.Random(seed)
        self._K = K
        self.attempts = {"fair": [], "festival": [], "radio": []}
        levels = LEVELS[:]
        self.rng.shuffle(levels)
        self.songs = [{"id": i, "title": f"Песня {i + 1}", "artist": "Офлайн-исполнитель",
                       "genre": GENRES[i % 4], "level": levels[i]} for i in range(N_SONGS)]
        self.playlists = []
        for _ in range(BROADCASTS + 1):
            p = list(range(N_SONGS))
            self.rng.shuffle(p)
            self.playlists.append(p)

    def __repr__(self):
        return f"MockCity(K={self._K}) — офлайн, честные правила"

    # эмуляция API стенда
    def request(self, method, path, json=None, params=None):
        json = json or {}
        h = getattr(self, "_" + method.lower() + path.replace("/api/", "_").replace("/", "_"), None)
        if h is None:
            raise EconError(f"Офлайн-режим не поддерживает {method} {path}.")
        return h(json if method != "GET" else (params or {}))

    def _check_lot(self, lot):
        if not isinstance(lot, int) or not 1 <= lot <= 5:
            raise EconError("Вложение должно быть целым числом от 1 до 5 ящиков.", "bad_lot")

    def _stats(self):
        inv = sum(a["invested"] for v in self.attempts.values() for a in v)
        rev = sum(a["revenue"] for v in self.attempts.values() for a in v)
        by = {k: {"attempts": len(v), "invested": sum(a["invested"] for a in v),
                  "revenue": sum(a["revenue"] for a in v)} for k, v in self.attempts.items()}
        for b in by.values():
            b["overprofit"] = b["revenue"] - b["invested"]
        r = len(self.attempts["radio"])
        usage = {"fair": {"used": len(self.attempts["fair"]), "total": FAIR_TOTAL},
                 "festival": {"used": len(self.attempts["festival"]), "total": FEST_TOTAL},
                 "radio": {"used": r, "total": BROADCASTS * N_SONGS,
                           "broadcasts_used": r // N_SONGS, "broadcasts_total": BROADCASTS}}
        return {"overprofit": round(rev - inv, 2), "invested": inv, "revenue": round(rev, 2),
                "by_activity": by, "usage": usage,
                "limits": {"fair": FAIR_TOTAL - usage["fair"]["used"],
                           "festival": FEST_TOTAL - usage["festival"]["used"],
                           "radio_songs": BROADCASTS * N_SONGS - r},
                "tier": {"level": 0, "name": "офлайн", "next_at": None}}

    def _get_me(self, _):
        return {"city": {"label": "Офлайн-город", "name": None, "team_name": "офлайн", "coat": None},
                "country": {"name": "Офлайн", "status": "open", "deadline_at": None},
                "rules": {"fair_K": self._K}, "stats": self._stats(), "rewards": {}}

    def _post_fair(self, body):
        kind, lot = body.get("kind"), body.get("lot")
        self._check_lot(lot)
        if not isinstance(kind, int) or not 0 <= kind <= 5:
            raise EconError("Вид товара — целое число от 0 до 5.", "bad_kind")
        if len(self.attempts["fair"]) >= FAIR_TOTAL:
            raise EconError(f"Все {FAIR_TOTAL} попыток ярмарки использованы.", "limit")
        wants = [self.rng.randrange(6) for _ in range(3)]
        m = wants.count(kind)
        rev = float(lot * {0: 0, 1: 2, 2: 3, 3: self._K + 1}[m])
        a = {"idx": len(self.attempts["fair"]), "choice": {"kind": kind, "lot": lot},
             "outcome": {"wants": wants, "matches": m}, "invested": lot, "revenue": rev}
        self.attempts["fair"].append(a)
        return {**a, "activity": "fair", "profit": rev - lot}

    def _post_festival(self, body):
        target, lot = body.get("target"), body.get("lot")
        self._check_lot(lot)
        if isinstance(target, str):
            t = target.strip().lower()
            target = {"запад": "west", "восток": "east"}.get(t, t)
            if target.isdigit():
                target = int(target)
        if target not in ("west", "east") and not (isinstance(target, int) and not isinstance(target, bool)
                                                   and 0 <= target <= 36):
            raise EconError("Цель фестиваля: номер квартала 0–36, 'west' или 'east'.", "bad_target")
        if len(self.attempts["festival"]) >= FEST_TOTAL:
            raise EconError(f"Все {FEST_TOTAL} попыток фестиваля использованы.", "limit")
        q = self.rng.randrange(37)
        if target == "west":
            mult = 2 if 1 <= q <= 18 else 0
        elif target == "east":
            mult = 2 if q >= 19 else 0
        else:
            mult = 36 if q == target else 0
        a = {"idx": len(self.attempts["festival"]), "choice": {"target": target, "lot": lot},
             "outcome": {"quarter": q, "mult": mult}, "invested": lot, "revenue": float(lot * mult)}
        self.attempts["festival"].append(a)
        return {**a, "activity": "festival", "profit": a["revenue"] - lot}

    def _pos(self):
        n = len(self.attempts["radio"])
        return n // N_SONGS + 1, n % N_SONGS

    def _m(self, b, pos):
        rest = self.playlists[b][pos:]
        return sum(self.songs[s]["level"] for s in rest) / len(rest)

    def _get_radio_state(self, _):
        b, pos = self._pos()
        fin = b > BROADCASTS
        return {"broadcast": min(b, BROADCASTS), "broadcasts_total": BROADCASTS, "position": 0 if fin else pos,
                "can_play": not fin, "finished": fin,
                "next_m": None if fin else round(self._m(b, pos), 4),
                "played": [] if fin else self.playlists[b][:pos],
                "previous": self.playlists[b - 1] if not fin else self.playlists[-1], "catalog": self.songs}

    def _post_radio_step(self, body):
        b, pos = self._pos()
        if b > BROADCASTS:
            raise EconError(f"Все {BROADCASTS} эфиров радио использованы.", "limit")
        buy, lot = bool(body.get("buy")), body.get("lot", 1)
        if buy:
            self._check_lot(lot)
        else:
            lot = 0
        song = self.playlists[b][pos]
        level = self.songs[song]["level"]
        m = self._m(b, pos)
        rev = round(0.95 * lot * level / m, 4) if buy else 0.0
        a = {"idx": len(self.attempts["radio"]), "choice": {"buy": buy, "lot": lot},
             "outcome": {"broadcast": b, "pos": pos, "song": song, "level": level, "m": round(m, 4)},
             "invested": lot, "revenue": rev}
        self.attempts["radio"].append(a)
        return {**a, "activity": "radio", "profit": rev - lot}

    def _get_radio_log(self, params):
        d = int(params["broadcast"])
        cur, pos = self._pos()
        if d < cur:
            return {"broadcast": d, "complete": True, "playlist": self.playlists[d]}
        if d == cur:
            return {"broadcast": d, "complete": False, "playlist": self.playlists[d][:pos]}
        raise EconError("Этот эфир ещё не звучал.")

    def _flat(self, act, a):
        o, c = a["outcome"], a["choice"]
        if act == "fair":
            return {"idx": a["idx"], "kind": c["kind"], "lot": c["lot"], "want1": o["wants"][0],
                    "want2": o["wants"][1], "want3": o["wants"][2], "matches": o["matches"], "revenue": a["revenue"]}
        if act == "festival":
            return {"idx": a["idx"], "target": c["target"], "lot": c["lot"], "quarter": o["quarter"],
                    "revenue": a["revenue"]}
        return {"idx": a["idx"], "broadcast": o["broadcast"], "pos": o["pos"], "buy": int(c["buy"]), "lot": c["lot"],
                "song": o["song"], "level": o["level"], "m": o["m"], "revenue": a["revenue"]}

    def _get_history_fair(self, _):
        return [self._flat("fair", a) for a in self.attempts["fair"]]

    def _get_history_festival(self, _):
        return [self._flat("festival", a) for a in self.attempts["festival"]]

    def _get_history_radio(self, _):
        return [self._flat("radio", a) for a in self.attempts["radio"]]

    def _post_claims(self, body):
        if body.get("activity") == "budget" and not (body["low"] <= body["mean"] <= body["high"]):
            raise EconError("Нужно low ≤ mean ≤ high.", status=400)
        print("Офлайн-режим: заявка не отправлена.", body)
        return body

    def _get_claims(self, _):
        return []

    def _get_news(self, _):
        return []

    def _get_country(self, _):
        return {"name": "Офлайн", "status": "open", "cities": []}

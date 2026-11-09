"""Validated, append-only fundamental observations; independent of holdings."""
from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import urlsplit

from src.config import METRIC_FIELDS
from src.currencies import SUPPORTED_CURRENCIES

if TYPE_CHECKING:
    import sqlite3
    from src.database import Database
    from src.models import Review

UNITS = {name: ("percent" if name in {
    "dividend_yield", "roe", "payout_ratio", "revenue_growth_3y"
} else "ratio") for name in METRIC_FIELDS}
UNITS["revenue"] = "currency"
MARKET_METRICS = {"pe_ratio", "dividend_yield"}


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False,
                      separators=(",", ":"))


def _hash(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def _keys(obj: Any, required: set[str], optional: set[str] = frozenset()) -> dict:
    if not isinstance(obj, dict):
        raise ValueError("Oczekiwano obiektu JSON.")
    if required - obj.keys():
        raise ValueError("Brak pól: " + ", ".join(sorted(required - obj.keys())))
    if obj.keys() - required - optional:
        raise ValueError("Nieznane pola: " + ", ".join(sorted(obj.keys() - required - optional)))
    return obj


def _text(value: Any, label: str, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str) or not value.strip() or len(value) > 20000:
        raise ValueError(f"{label}: wymagany niepusty tekst (maks. 20000 znaków).")
    return value.strip()


def iso_date(value: Any, label: str = "Data", nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError(f"{label}: wymagany format RRRR-MM-DD.")
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError as exc:
        raise ValueError(f"{label}: niepoprawna data.") from exc


def valid_isin(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError("ISIN musi być tekstem.")
    value = value.strip().upper()
    if not re.fullmatch(r"[A-Z]{2}[A-Z0-9]{9}\d", value):
        raise ValueError(f"Niepoprawny format ISIN: {value}")
    digits = "".join(str(int(c, 36)) if c.isalpha() else c for c in value)
    total = 0
    for index, char in enumerate(reversed(digits)):
        n = int(char) * (2 if index % 2 else 1)
        total += n // 10 + n % 10
    if total % 10:
        raise ValueError(f"Niepoprawna cyfra kontrolna ISIN: {value}")
    return value


def _currency(value: Any, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str) or value not in SUPPORTED_CURRENCIES:
        raise ValueError("Waluta wymaga trzyliterowego kodu, np. EUR, albo null.")
    return value


def _unique_object(pairs: list) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Powtórzony klucz JSON: {key}")
        result[key] = value
    return result


def read_package(path: str | Path) -> dict:
    path = Path(path)
    if path.stat().st_size > 5_000_000:
        raise ValueError("Pakiet przekracza limit 5 MB.")
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"),
                         object_pairs_hook=_unique_object,
                         parse_constant=lambda x: (_ for _ in ()).throw(ValueError(f"Niedozwolona liczba: {x}")))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Niepoprawny JSON: {exc}") from exc
    except RecursionError as exc:
        raise ValueError("Zbyt głęboko zagnieżdżony JSON.") from exc
    return validate_package(raw)


def validate_package(raw: Any) -> dict:
    """Strict v1 schema, normalized at both preview and commit boundaries."""
    p = _keys(raw, {"schema_version", "issuer", "instruments", "observations"})
    if type(p["schema_version"]) is not int or p["schema_version"] != 1:
        raise ValueError("Obsługiwana jest wyłącznie schema_version: 1.")
    issuer = _keys(p["issuer"], {"id", "name"})
    issuer_id = _text(issuer["id"], "Identyfikator emitenta")
    if issuer_id.startswith("isin:"):
        issuer_id = "isin:" + valid_isin(issuer_id[5:])
    elif not re.fullmatch(r"lei:[A-Z0-9]{20}", issuer_id):
        raise ValueError("Emitent wymaga id lei:<LEI> albo isin:<główny ISIN>.")
    issuer = {"id": issuer_id, "name": _text(issuer["name"], "Nazwa emitenta")}
    if not isinstance(p["instruments"], list) or not p["instruments"]:
        raise ValueError("Wymagana jest niepusta lista instruments.")
    instruments = {}
    for item in p["instruments"]:
        item = _keys(item, {"isin", "share_class", "currency"}, {"ticker"})
        isin = valid_isin(item["isin"])
        if isin in instruments:
            raise ValueError(f"Powtórzony instrument: {isin}")
        instruments[isin] = {"isin": isin, "share_class": _text(item["share_class"], "Klasa akcji"),
                             "currency": _currency(item["currency"]),
                             "ticker": _text(item.get("ticker"), "Ticker", True)}
    if not isinstance(p["observations"], list) or not 1 <= len(p["observations"]) <= 10000:
        raise ValueError("Lista observations musi zawierać 1–10000 pozycji.")
    observations = []
    seen = {}
    for index, raw_observation in enumerate(p["observations"], 1):
        try:
            o = _validate_observation(raw_observation, instruments)
            key = logical_key(issuer_id, o)
            fingerprint = observation_fingerprint(issuer_id, o)
            if key in seen and seen[key] != fingerprint:
                raise ValueError("Dwie sprzeczne wersje tej samej obserwacji w jednym pakiecie.")
            seen[key] = fingerprint
            observations.append(o)
        except ValueError as exc:
            raise ValueError(f"Obserwacja {index}: {exc}") from exc
    return {"schema_version": 1, "issuer": issuer,
            "instruments": list(instruments.values()), "observations": observations}


def _validate_observation(raw: Any, instruments: dict) -> dict:
    o = dict(_keys(raw, {"metric", "scope", "isin", "period", "valuation_date", "published_on",
                         "value", "unit", "currency", "definition", "source", "calculation",
                         "missing_reason", "uncertainty"}))
    if not isinstance(o["metric"], str) or o["metric"] not in UNITS:
        raise ValueError(f"Nieobsługiwana metryka: {o['metric']}")
    if o["unit"] != UNITS[o["metric"]]:
        raise ValueError(f"Jednostka {o['metric']} musi być {UNITS[o['metric']]}.")
    if not isinstance(o["scope"], str) or o["scope"] not in {"company", "instrument"}:
        raise ValueError("scope wymaga company albo instrument.")
    if o["scope"] == "company":
        if o["isin"] is not None or o["metric"] in MARKET_METRICS:
            raise ValueError("Dane spółki wymagają isin: null; P/E i yield wymagają instrumentu.")
    else:
        o["isin"] = valid_isin(o["isin"])
        if o["isin"] not in instruments:
            raise ValueError("ISIN obserwacji nie występuje w instruments.")
    if o["metric"] == "revenue" and o["scope"] != "company":
        raise ValueError("Przychody dotyczą spółki.")
    period = dict(_keys(o["period"], {"start", "end", "basis"}))
    period["start"] = iso_date(period["start"], "Początek okresu")
    period["end"] = iso_date(period["end"], "Koniec okresu")
    if not isinstance(period["basis"], str) or period["basis"] not in {"annual", "quarter", "ttm", "instant"} or period["start"] > period["end"]:
        raise ValueError("Niepoprawny okres lub basis.")
    if period["basis"] == "instant" and period["start"] != period["end"]:
        raise ValueError("Okres instant wymaga jednakowych dat start i end.")
    o["period"] = period
    o["published_on"] = iso_date(o["published_on"], "Data udostępnienia", True)
    o["valuation_date"] = iso_date(o["valuation_date"], "Data wyceny", True)
    if any(d and d > date.today().isoformat() for d in (period["end"], o["published_on"], o["valuation_date"])):
        raise ValueError("Pakiet historyczny nie może deklarować przyszłego okresu, udostępnienia ani wyceny.")
    if o["metric"] in MARKET_METRICS and o["valuation_date"] is None:
        raise ValueError("Wskaźnik rynkowy wymaga valuation_date.")
    o["currency"] = _currency(o["currency"], o["metric"] != "revenue")
    if o["scope"] == "instrument" and o["currency"] != instruments[o["isin"]]["currency"]:
        raise ValueError("Waluta obserwacji musi odpowiadać walucie instrumentu.")
    if o["published_on"] and o["published_on"] < max(period["end"], o["valuation_date"] or period["end"]):
        raise ValueError("Udostępnienie nie może poprzedzać końca okresu ani ceny użytej w wycenie.")
    for key in ("definition", "calculation", "missing_reason", "uncertainty"):
        o[key] = _text(o[key], key, key != "definition")
    value = o["value"]
    if value is None:
        if o["missing_reason"] is None:
            raise ValueError("Brak wartości wymaga missing_reason.")
    elif (type(value) not in (int, float) or abs(value) > 1e15 or not math.isfinite(value)):
        raise ValueError("Wartość musi być skończoną liczbą w zakresie ±10^15 lub null.")
    elif o["missing_reason"] is not None:
        raise ValueError("Wartość liczbowa nie może mieć missing_reason.")
    if value is not None:
        o["value"] = float(value) if value != 0 else 0.0
    if o["published_on"] is None and o["uncertainty"] is None:
        raise ValueError("Nieznana data udostępnienia wymaga wyjaśnienia uncertainty.")
    source = dict(_keys(o["source"], {"name", "url", "locator"}))
    source["name"] = _text(source["name"], "Nazwa źródła")
    source["url"] = _text(source["url"], "Adres źródła")
    url = urlsplit(source["url"])
    if url.scheme not in {"http", "https"} or not url.hostname or url.username or url.password:
        raise ValueError("Źródło wymaga adresu http(s), bez danych logowania.")
    source["locator"] = _text(source["locator"], "Strona/tabela", True)
    o["source"] = source
    return o


def logical_key(issuer_id: str, o: dict) -> str:
    return _hash([issuer_id, o["scope"], o["isin"], o["metric"], o["period"],
                  o["valuation_date"], o["definition"], o["unit"], o["currency"]])


def observation_fingerprint(issuer_id: str, o: dict) -> str:
    return _hash([issuer_id, o])


def available_on(o: dict, as_of: str) -> bool:
    return bool(o["published_on"] and o["published_on"] <= as_of
                and o["period"]["end"] <= as_of
                and (o["valuation_date"] is None or o["valuation_date"] <= as_of))


def migrate_fundamentals(conn: sqlite3.Connection) -> None:
    """Only additive DDL, in one transaction. Existing reviews stay untouched."""
    if not conn.in_transaction:
        conn.execute("BEGIN IMMEDIATE")
    conn.execute("""CREATE TABLE IF NOT EXISTS fundamental_instruments (
        isin TEXT PRIMARY KEY, issuer_id TEXT NOT NULL, issuer_name TEXT NOT NULL,
        share_class TEXT NOT NULL, currency TEXT NOT NULL, ticker TEXT)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS fundamental_observations (
        id INTEGER PRIMARY KEY, issuer_id TEXT NOT NULL, scope TEXT NOT NULL,
        isin TEXT, metric TEXT NOT NULL, period_end TEXT NOT NULL,
        logical_key TEXT NOT NULL, fingerprint TEXT NOT NULL UNIQUE,
        payload_json TEXT NOT NULL, supersedes_id INTEGER,
        imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (supersedes_id) REFERENCES fundamental_observations(id))""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_fundamental_history ON fundamental_observations(issuer_id, period_end, id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_fundamental_series ON fundamental_observations(logical_key, id DESC)")
    if "fundamental_evidence_json" not in {r["name"] for r in conn.execute("PRAGMA table_info(reviews)")}:
        conn.execute("ALTER TABLE reviews ADD COLUMN fundamental_evidence_json TEXT")


@dataclass
class ImportPlan:
    package: dict
    rows: list[dict]
    mapping_notes: list[str]

    @property
    def counts(self) -> dict[str, int]:
        return {s: sum(row["action"] == s for row in self.rows)
                for s in ("new", "duplicate", "correction")}

    @property
    def token(self) -> str:
        return _hash([self.package, [(r["fingerprint"], r["action"], r["supersedes_id"]) for r in self.rows]])


class FundamentalStore:
    def __init__(self, database: Database) -> None:
        self.db = database

    def _plan(self, package: dict, conn: sqlite3.Connection) -> ImportPlan:
        p = validate_package(package)
        issuer = p["issuer"]
        notes = []
        for i in p["instruments"]:
            known = conn.execute("SELECT * FROM fundamental_instruments WHERE isin=?", (i["isin"],)).fetchone()
            if known and (known["issuer_id"] != issuer["id"] or known["share_class"] != i["share_class"] or known["currency"] != i["currency"]):
                raise ValueError(f"ISIN {i['isin']} ma już inne przypisanie emitenta, klasy lub waluty. Import przerwany.")
            position = conn.execute("SELECT currency FROM positions WHERE UPPER(TRIM(isin))=?", (i["isin"],)).fetchone()
            if position and position["currency"] != i["currency"]:
                raise ValueError(f"Waluta {i['isin']} jest sprzeczna z zapisaną pozycją.")
            notes.append(f"{i['isin']} / {i['share_class']} / {i['currency']}: " +
                         ("znane przypisanie" if known else "NOWE przypisanie do emitenta — sprawdź"))
        seen = set()
        rows = []
        for o in p["observations"]:
            fingerprint = observation_fingerprint(issuer["id"], o)
            key = logical_key(issuer["id"], o)
            duplicate = fingerprint in seen or conn.execute("SELECT 1 FROM fundamental_observations WHERE fingerprint=?", (fingerprint,)).fetchone()
            previous = conn.execute("SELECT id FROM fundamental_observations WHERE logical_key=? ORDER BY id DESC LIMIT 1", (key,)).fetchone()
            action = "duplicate" if duplicate else "correction" if previous else "new"
            rows.append({"observation": o, "action": action, "fingerprint": fingerprint,
                         "logical_key": key, "supersedes_id": previous["id"] if previous else None})
            seen.add(fingerprint)
        for end in sorted({o["period"]["end"] for o in p["observations"]}):
            present = {o["metric"] for o in p["observations"] if o["period"]["end"] == end}
            absent = sorted(set(METRIC_FIELDS) - present)
            if absent:
                notes.append(f"Okres {end}: nie dostarczono pól {', '.join(absent)}. Nie uzupełniamy ich zerami.")
        return ImportPlan(p, rows, notes)

    def preview(self, package: dict) -> ImportPlan:
        with self.db.connection() as conn:
            return self._plan(package, conn)

    def import_package(self, package: dict, *, confirmed: bool = False,
                       expected_preview_token: str | None = None) -> dict[str, int]:
        if not confirmed:
            raise ValueError("Zapis wymaga zatwierdzenia podglądu i tożsamości emitenta.")
        with self.db.connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            plan = self._plan(package, conn)  # recheck after acquiring the write lock
            if expected_preview_token is not None and expected_preview_token != plan.token:
                raise ValueError("Historia zmieniła się od podglądu. Zamknij okno i wczytaj pakiet ponownie, aby zatwierdzić aktualny stan.")
            issuer = plan.package["issuer"]
            for i in plan.package["instruments"]:
                conn.execute("""INSERT OR IGNORE INTO fundamental_instruments
                    (isin, issuer_id, issuer_name, share_class, currency, ticker) VALUES (?,?,?,?,?,?)""",
                    (i["isin"], issuer["id"], issuer["name"], i["share_class"], i["currency"], i["ticker"]))
            for row in plan.rows:
                if row["action"] == "duplicate":
                    continue
                o = row["observation"]
                payload = {"issuer": issuer, "observation": o}
                conn.execute("""INSERT INTO fundamental_observations
                    (issuer_id, scope, isin, metric, period_end, logical_key, fingerprint, payload_json, supersedes_id)
                    VALUES (?,?,?,?,?,?,?,?,?)""", (issuer["id"], o["scope"], o["isin"], o["metric"],
                    o["period"]["end"], row["logical_key"], row["fingerprint"], canonical(payload), row["supersedes_id"]))
            return plan.counts

    def instruments(self) -> list[dict]:
        with self.db.connection() as conn:
            return [dict(r) for r in conn.execute("SELECT * FROM fundamental_instruments ORDER BY issuer_name, isin")]

    @staticmethod
    def _record(row: sqlite3.Row) -> dict:
        return {"id": row["id"], "fingerprint": row["fingerprint"], "logical_key": row["logical_key"],
                "supersedes_id": row["supersedes_id"], "imported_at": row["imported_at"], **json.loads(row["payload_json"])}

    def history(self, isin: str, *, as_of: str | None = None, all_versions: bool = False) -> list[dict]:
        if as_of is not None:
            iso_date(as_of)
        with self.db.connection() as conn:
            mapping = conn.execute("SELECT issuer_id FROM fundamental_instruments WHERE isin=?", (isin,)).fetchone()
            if not mapping:
                return []
            records = [self._record(r) for r in conn.execute("""SELECT * FROM fundamental_observations
                WHERE issuer_id=? AND (scope='company' OR isin=?) ORDER BY id""", (mapping["issuer_id"], isin))]
        if as_of is not None:
            records = [r for r in records if available_on(r["observation"], as_of)]
        if not all_versions:
            latest = {r["logical_key"]: r for r in records}
            records = list(latest.values())
        return sorted(records, key=lambda r: (r["observation"]["period"]["end"], r["id"]), reverse=True)

    def freeze_review(self, review: Review, conn: sqlite3.Connection) -> str:
        """Resolve IDs afresh and embed full copies. No later join to 'latest'."""
        reviewed_on = iso_date(review.review_date, "Data rzeczywistej rewizji")
        if reviewed_on > date.today().isoformat():
            raise ValueError("Rzeczywista rewizja nie może mieć przyszłej daty.")
        request = json.loads(review.fundamental_evidence_json) if review.fundamental_evidence_json else {}
        _keys(request, set(), {"observation_ids", "bindings"})
        selected_ids = request.get("observation_ids", [])
        bindings = request.get("bindings", {})
        if not isinstance(bindings, dict) or any(k not in METRIC_FIELDS or type(v) is not int for k, v in bindings.items()):
            raise ValueError("Niepoprawne powiązanie metryk.")
        if not isinstance(selected_ids, list) or any(type(i) is not int for i in selected_ids):
            raise ValueError("Niepoprawny wybór obserwacji.")
        if any(i not in selected_ids for i in bindings.values()):
            raise ValueError("Powiązanie wskazuje obserwację, której nie dołączono do rewizji.")
        position = conn.execute("SELECT isin, currency FROM positions WHERE id=?", (review.position_id,)).fetchone()
        if position is None:
            raise ValueError("Nie znaleziono pozycji rewizji.")
        mapping = conn.execute("SELECT issuer_id FROM fundamental_instruments WHERE isin=?", (position["isin"].upper().strip(),)).fetchone()
        evidence = []
        for obs_id in dict.fromkeys(selected_ids):
            row = conn.execute("SELECT * FROM fundamental_observations WHERE id=?", (obs_id,)).fetchone()
            if row is None or mapping is None or row["issuer_id"] != mapping["issuer_id"] or (row["scope"] == "instrument" and row["isin"] != position["isin"].upper().strip()):
                raise ValueError("Wybrane dane nie należą do emitenta/instrumentu rewizji.")
            r = self._record(row)
            if row["scope"] == "instrument" and r["observation"]["currency"] != position["currency"]:
                raise ValueError("Waluta instrumentu rewizji nie odpowiada wybranym danym.")
            if not available_on(r["observation"], reviewed_on):
                raise ValueError("Dane nie były dostępne w dniu rewizji lub nie mają daty udostępnienia.")
            evidence.append(r)
        inputs = {}
        for name in METRIC_FIELDS:
            value = review.metric_value(name)
            if value is not None and (not math.isfinite(value) or abs(value) > 1e15):
                raise ValueError("Niepoprawna ręczna wartość metryki.")
            bound = next((r for r in evidence if r["id"] == bindings.get(name)), None)
            if bound and bound["observation"]["metric"] != name:
                raise ValueError("Metryka nie zgadza się z wybraną obserwacją.")
            imported = bool(bound and bound["observation"]["value"] == value)
            inputs[name] = {"value": value, "origin": "imported" if imported else "manual",
                            "observation_id": bound["id"] if imported else None}
        return canonical({"schema_version": 1, "reviewed_on": reviewed_on,
                          "recorded_at": datetime.now(timezone.utc).isoformat(),
                          "observations": evidence, "metric_inputs": inputs})


def series_signature(record: dict) -> tuple:
    o = record["observation"]
    return (record["issuer"]["id"], o["metric"], o["scope"], o["isin"], o["definition"],
            o["unit"], o["currency"], o["period"]["basis"])

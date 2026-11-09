"""All fixtures are synthetic; every database lives in TemporaryDirectory."""
from __future__ import annotations

import copy
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from datetime import date
from unittest.mock import patch

from src.database import Database, POSITIONS_SQL, REVIEWS_SQL
from src.fundamentals import (
    available_on, canonical, migrate_fundamentals, read_package,
    validate_package, valid_isin,
)
from src.metrics_engine import fundamental_change, MetricTrend, compare_metric, sources_comparable
from src.models import Position, Review

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples/fundamentals-v1.json"
ISIN = "ZZ0000000016"
SECOND_ISIN = "ZZ0000000024"
OTHER_ISIN = "DE0005785802"


def package() -> dict:
    return json.loads(EXAMPLE.read_text())


def position(isin: str = ISIN) -> Position:
    return Position(ticker="DEMO", isin=isin, name="Synthetic", currency="EUR",
                    sector=None, thesis="Zapisana teza", initial_buy_price=20,
                    initial_buy_date="2026-01-02", quantity=5, average_cost=21,
                    current_price=25, review_date="2027-01-01")


def review(position_id: int, records: list | None = None, **kwargs) -> Review:
    selected = records or []
    return Review(position_id=position_id, review_date="2025-07-01", price_then=25,
                  return_pct=0.2, category="NEUTRALNY", instruction="TRZYMAJ",
                  fundamental_evidence_json=canonical({"observation_ids": [r["id"] for r in selected], "bindings": {}}), **kwargs)


class FundamentalFixture(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        self.db = Database(self.path / "test.db")
        self.db.init()

    def import_example(self) -> list[dict]:
        self.db.fundamentals.import_package(package(), confirmed=True)
        return self.db.fundamentals.history(ISIN)


class FundamentalTests(FundamentalFixture):

    def test_valid_example_and_many_periods_without_holdings(self):
        parsed = read_package(EXAMPLE)
        plan = self.db.fundamentals.preview(parsed)
        self.assertEqual(plan.counts, {"new": 7, "duplicate": 0, "correction": 0})
        self.assertEqual(self.db.fundamentals.instruments(), [])
        self.assertEqual(self.db.fundamentals.history(ISIN), [])
        with self.assertRaises(ValueError):
            self.db.fundamentals.import_package(parsed)
        counts = self.db.fundamentals.import_package(parsed, confirmed=True)
        self.assertEqual(counts["new"], 7)
        records = self.db.fundamentals.history(ISIN)
        self.assertEqual({r["observation"]["period"]["end"] for r in records}, {"2023-12-31", "2024-12-31"})
        self.assertEqual(self.db.count_positions(), 0)
        self.assertEqual(self.db.count_reviews(), 0)

    def test_import_does_not_change_price_quantity_or_next_review(self):
        pid = self.db.insert_position(position())
        before = self.db.get_position_by_id(pid).to_dict()
        self.import_example()
        self.assertEqual(before, self.db.get_position_by_id(pid).to_dict())
        self.assertEqual(self.db.count_reviews(), 0)

    def test_company_metrics_shared_across_classes_instrument_metrics_are_not(self):
        records = self.import_example()
        other_class = self.db.fundamentals.history(SECOND_ISIN)
        self.assertEqual(len(records), 7)
        self.assertEqual(len(other_class), 6)
        self.assertTrue(all(r["observation"]["scope"] == "company" for r in other_class))

    def test_duplicates_across_files_order_and_numeric_representation(self):
        self.import_example()
        p = package()
        p["observations"].reverse()
        next(o for o in p["observations"] if o["metric"] == "revenue" and o["value"] == 112000000)["value"] = 112000000.0
        # Key order / whitespace / filename play no role.
        path = self.path / "another-name.json"
        path.write_text(json.dumps(p, sort_keys=True))
        counts = self.db.fundamentals.import_package(read_package(path), confirmed=True)
        self.assertEqual(counts, {"new": 0, "duplicate": 7, "correction": 0})
        self.assertEqual(len(self.db.fundamentals.history(ISIN, all_versions=True)), 7)

    def test_identical_rows_inside_one_package_are_skipped(self):
        p = package()
        p["observations"].append(copy.deepcopy(p["observations"][0]))
        counts = self.db.fundamentals.import_package(p, confirmed=True)
        self.assertEqual(counts, {"new": 7, "duplicate": 1, "correction": 0})

    def test_contradictory_rows_reject_entire_package(self):
        p = package()
        duplicate = copy.deepcopy(p["observations"][0])
        duplicate["value"] = 123
        p["observations"].append(duplicate)
        with self.assertRaises(ValueError):
            self.db.fundamentals.import_package(p, confirmed=True)
        self.assertEqual(self.db.fundamentals.instruments(), [])

    def test_missing_zero_and_negative_are_distinct(self):
        p = package()
        p["observations"][1]["value"] = 0
        self.db.fundamentals.import_package(p, confirmed=True)
        values = [r["observation"]["value"] for r in self.db.fundamentals.history(ISIN)]
        self.assertIn(None, values)
        self.assertIn(0, values)
        self.assertIn(-2.5, values)
        self.assertEqual(compare_metric("roe", None, 0), MetricTrend.NO_DATA)

    def test_omitted_metrics_report_incomplete_coverage_without_inventing_values(self):
        p = package()
        p["observations"] = p["observations"][:1]
        plan = self.db.fundamentals.preview(p)
        self.assertTrue(any("nie dostarczono" in s for s in plan.mapping_notes))
        self.assertEqual(len(plan.rows), 1)

    def test_invalid_isin_and_instrument_identification(self):
        for value in [None, "DEMO", "ZZ0000000017", "ZZ000000001X"]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                valid_isin(value)
        self.assertEqual(valid_isin(" de0005785802 "), OTHER_ISIN)
        p = package()
        p["observations"][-1]["isin"] = OTHER_ISIN
        with self.assertRaises(ValueError):
            validate_package(p)

    def test_ticker_is_not_a_matching_key(self):
        pid = self.db.insert_position(position(OTHER_ISIN))  # same ticker, different security
        self.import_example()
        self.assertEqual(self.db.get_position_by_id(pid).isin, OTHER_ISIN)
        self.assertEqual(self.db.fundamentals.history(OTHER_ISIN), [])

    def test_mapping_and_existing_position_currency_conflicts_are_atomic(self):
        self.import_example()
        original = len(self.db.fundamentals.history(ISIN, all_versions=True))
        p = package()
        p["issuer"]["id"] = "isin:" + OTHER_ISIN
        with self.assertRaises(ValueError):
            self.db.fundamentals.import_package(p, confirmed=True)
        p = package()
        p["instruments"][0]["share_class"] = "inna klasa"
        with self.assertRaises(ValueError):
            self.db.fundamentals.import_package(p, confirmed=True)
        self.assertEqual(len(self.db.fundamentals.history(ISIN, all_versions=True)), original)
        self.db.insert_position(position(OTHER_ISIN))
        p = package()
        p["instruments"] = [{"isin": OTHER_ISIN, "share_class": "ordinary", "currency": "USD"}]
        p["observations"] = p["observations"][:1]
        with self.assertRaises(ValueError):
            self.db.fundamentals.import_package(p, confirmed=True)

    def test_schema_errors(self):
        cases = [
            ("version", lambda p: p.update(schema_version=2)),
            ("bool version", lambda p: p.update(schema_version=True)),
            ("unknown field", lambda p: p.update(unknown=1)),
            ("missing field", lambda p: p["observations"][0].pop("source")),
            ("bad metric", lambda p: p["observations"][0].update(metric=[])),
            ("bad scope", lambda p: p["observations"][0].update(scope={})),
            ("wrong unit", lambda p: p["observations"][0].update(unit="ratio")),
            ("nan", lambda p: p["observations"][0].update(value=float("nan"))),
            ("infinity", lambda p: p["observations"][0].update(value=float("inf"))),
            ("boolean", lambda p: p["observations"][0].update(value=True)),
            ("string number", lambda p: p["observations"][0].update(value="10")),
            ("null reason", lambda p: p["observations"][0].update(value=None)),
            ("wrong date", lambda p: p["observations"][0].update(published_on="2024-02-30")),
            ("end not publication", lambda p: p["observations"][0].update(published_on="2023-12-01")),
            ("unknown publication", lambda p: p["observations"][0].update(published_on=None)),
            ("code as URL", lambda p: p["observations"][0]["source"].update(url="javascript:alert(1)")),
            ("market data on company", lambda p: p["observations"][-1].update(scope="company", isin=None)),
            ("no valuation", lambda p: p["observations"][-1].update(valuation_date=None)),
            ("wrong currency", lambda p: p["observations"][-1].update(currency="USD")),
            ("unknown currency", lambda p: p["instruments"][0].update(currency="XYZ")),
            ("future reporting", lambda p: p["observations"][0]["period"].update(end="2999-01-01")),
            ("no observations", lambda p: p.update(observations=[])),
            ("no instruments", lambda p: p.update(instruments=[])),
        ]
        for name, mutate in cases:
            p = package()
            mutate(p)
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.db.fundamentals.import_package(p, confirmed=True)
        self.assertEqual(self.db.fundamentals.instruments(), [])

    def test_raw_json_errors(self):
        for raw in ['{"schema_version":1,"schema_version":2}', '{', 'NaN', '[]']:
            path = self.path / "invalid.json"
            path.write_text(raw)
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                read_package(path)

    def test_unknown_publication_is_stored_but_not_available_for_review(self):
        p = package()
        p["observations"] = p["observations"][:1]
        p["observations"][0].update(published_on=None, uncertainty="Nieznana data publikacji")
        self.db.fundamentals.import_package(p, confirmed=True)
        records = self.db.fundamentals.history(ISIN)
        self.assertEqual(len(records), 1)
        self.assertEqual(self.db.fundamentals.history(ISIN, as_of="2026-01-01"), [])
        pid = self.db.insert_position(position())
        with self.assertRaises(ValueError):
            self.db.insert_review(review(pid, records))
        self.assertEqual(self.db.count_reviews(), 0)

    def test_correction_is_append_only_and_as_of_keeps_previous_version(self):
        self.import_example()
        p = package()
        p["observations"] = p["observations"][:1]
        p["observations"][0].update(value=-1, published_on="2025-09-01", uncertainty="Korekta raportu")
        counts = self.db.fundamentals.import_package(p, confirmed=True)
        self.assertEqual(counts["correction"], 1)
        latest = next(r for r in self.db.fundamentals.history(ISIN) if r["observation"]["metric"] == "roe" and r["observation"]["period"]["end"] == "2023-12-31")
        self.assertIsNotNone(latest["supersedes_id"])
        earlier = self.db.fundamentals.history(ISIN, as_of="2024-07-01")
        self.assertEqual(next(r["observation"]["value"] for r in earlier if r["observation"]["metric"] == "roe"), -2.5)
        self.db.fundamentals.import_package(package(), confirmed=True)
        latest_after = next(r for r in self.db.fundamentals.history(ISIN) if r["logical_key"] == latest["logical_key"])
        self.assertEqual(latest_after["id"], latest["id"])
        self.assertEqual(len(self.db.fundamentals.history(ISIN, all_versions=True)), 8)

    def test_real_review_freezes_source_and_manual_override_and_survives_correction(self):
        pid = self.db.insert_position(position())
        records = self.import_example()
        chosen = next(r for r in records if r["observation"]["metric"] == "roe" and r["observation"]["period"]["end"] == "2024-12-31")
        r = review(pid, records, roe=99, notes="Moja rzeczywista ocena")
        r.fundamental_evidence_json = canonical({"observation_ids": [x["id"] for x in records], "bindings": {"roe": chosen["id"]}})
        request = r.fundamental_evidence_json
        self.db.insert_review_and_update_position(r, 25, "2026-07-01")
        saved = self.db.get_last_review_for_position(pid)
        frozen = saved.fundamental_evidence_json
        evidence = json.loads(frozen)
        self.assertEqual(evidence["metric_inputs"]["roe"]["origin"], "manual")
        self.assertEqual(len(evidence["observations"]), 7)
        self.assertEqual(r.fundamental_evidence_json, request)
        p = package()
        p["observations"][3]["value"] = 4.0
        p["observations"][3]["published_on"] = "2025-09-01"
        self.db.fundamentals.import_package(p, confirmed=True)
        self.assertEqual(self.db.get_last_review_for_position(pid).fundamental_evidence_json, frozen)
        self.assertEqual(self.db.get_last_review_for_position(pid).roe, 99)
        self.assertEqual(self.db.get_position_by_id(pid).review_date, "2026-07-01")

    def test_imported_binding_and_manual_negative_and_null(self):
        pid = self.db.insert_position(position())
        records = self.import_example()
        chosen = next(r for r in records if r["observation"]["metric"] == "roe" and r["observation"]["value"] == -2.5)
        r = review(pid, [chosen], roe=-2.5, debt_to_equity=None)
        r.fundamental_evidence_json = canonical({"observation_ids": [chosen["id"]], "bindings": {"roe": chosen["id"]}})
        self.db.insert_review(r)
        frozen = json.loads(self.db.get_last_review_for_position(pid).fundamental_evidence_json)
        self.assertEqual(frozen["metric_inputs"]["roe"]["origin"], "imported")
        self.assertIsNone(frozen["metric_inputs"]["debt_to_equity"]["value"])

    def test_wrong_company_or_class_or_later_publication_rejected(self):
        records = self.import_example()
        own = self.db.insert_position(position(SECOND_ISIN))
        other = self.db.insert_position(position(OTHER_ISIN))
        market = next(r for r in records if r["observation"]["scope"] == "instrument")
        for pid, selected in [(own, [market]), (other, records)]:
            with self.subTest(pid=pid), self.assertRaises(ValueError):
                self.db.insert_review(review(pid, selected))
        r = review(own, [next(r for r in records if r["observation"]["scope"] == "company")])
        r.review_date = "2023-12-31"
        with self.assertRaises(ValueError):
            self.db.insert_review(r)
        self.assertEqual(self.db.count_reviews(), 0)

    def test_failed_review_update_rolls_back_and_keeps_request(self):
        pid = self.db.insert_position(position())
        records = self.import_example()
        self.db.close_position(pid, sell_date="2026-01-03", sell_price=25)
        r = review(pid, records)
        original = r.fundamental_evidence_json
        with self.assertRaises(ValueError):
            self.db.insert_review_and_update_position(r, 25, "2026-07-01")
        self.assertEqual(self.db.count_reviews(), 0)
        self.assertEqual(r.fundamental_evidence_json, original)

    def test_neutral_period_comparison_requires_same_definition_and_period_basis(self):
        records = self.import_example()
        roe = sorted([r for r in records if r["observation"]["metric"] == "roe"], key=lambda r: r["observation"]["period"]["end"])
        self.assertIn("wzrost", fundamental_change(roe[1], roe[0]))
        changed = copy.deepcopy(roe[1])
        changed["observation"]["definition"] = "Inna definicja"
        self.assertIn("brak porównania", fundamental_change(changed, roe[0]))
        self.assertFalse(sources_comparable(changed, roe[0]))
        self.assertFalse(sources_comparable(roe[1], None))
        stub = copy.deepcopy(roe[1])
        stub["observation"]["period"]["start"] = "2024-07-01"
        self.assertIn("brak porównania", fundamental_change(stub, roe[0]))

    def test_existing_database_migration_is_additive_and_idempotent(self):
        path = self.path / "legacy.db"
        with sqlite3.connect(path) as conn:
            conn.executescript(POSITIONS_SQL + REVIEWS_SQL)
            conn.execute("ALTER TABLE positions ADD COLUMN user_note TEXT")
            conn.execute("""INSERT INTO positions
                (id,ticker,isin,currency,initial_buy_price,initial_buy_date,quantity,average_cost,current_price,review_date,user_note)
                VALUES(44,'OLD',?,'EUR',20,'2020-01-01',5,21,25,'2027-01-01','keep')""", (ISIN,))
            conn.execute("""INSERT INTO reviews(id,position_id,review_date,price_then,return_pct,category,instruction,roe,notes)
                VALUES(77,44,'2021-01-01',25,0.2,'NEUTRALNY','TRZYMAJ',NULL,'stara ocena')""")
            old_position = conn.execute("SELECT * FROM positions").fetchone()
            old_review = conn.execute("SELECT * FROM reviews").fetchone()
            position_schema = conn.execute("SELECT sql FROM sqlite_master WHERE name='positions'").fetchone()[0]
        db = Database(path)
        db.init()
        db.init()
        with db.connection() as conn:
            self.assertEqual(tuple(conn.execute("SELECT * FROM positions").fetchone()), old_position)
            row = tuple(conn.execute("SELECT * FROM reviews").fetchone())
            self.assertEqual(row[:-1], old_review)
            self.assertIsNone(row[-1])
            self.assertEqual(conn.execute("SELECT sql FROM sqlite_master WHERE name='positions'").fetchone()[0], position_schema)
            self.assertEqual(conn.execute("PRAGMA foreign_key_check").fetchall(), [])
            self.assertIsNone(conn.execute("SELECT name FROM sqlite_master WHERE name='investment_transactions'").fetchone())
        self.assertEqual(db.get_last_review_for_position(44).notes, "stara ocena")

    def test_failed_extension_migration_rolls_back_all_its_ddl(self):
        path = self.path / "failure.db"
        class FailingConnection(sqlite3.Connection):
            def execute(self, sql, parameters=()):
                if sql.startswith("ALTER TABLE reviews"):
                    raise sqlite3.OperationalError("synthetic DDL failure")
                return super().execute(sql, parameters)
        conn = sqlite3.connect(path, factory=FailingConnection)
        conn.row_factory = sqlite3.Row
        conn.executescript(REVIEWS_SQL)
        try:
            with self.assertRaises(sqlite3.OperationalError), conn:
                migrate_fundamentals(conn)
            self.assertIsNone(conn.execute("SELECT name FROM sqlite_master WHERE name='fundamental_instruments'").fetchone())
        finally:
            conn.close()

    def test_import_failure_after_first_insert_rolls_back_mapping_and_values(self):
        with self.db.connection() as conn:
            conn.execute("""CREATE TRIGGER reject_revenue BEFORE INSERT ON fundamental_observations
                WHEN NEW.metric='revenue' BEGIN SELECT RAISE(ABORT,'synthetic failure'); END""")
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.fundamentals.import_package(package(), confirmed=True)
        self.assertEqual(self.db.fundamentals.instruments(), [])
        with self.db.connection() as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM fundamental_observations").fetchone()[0], 0)

    def test_changed_preview_requires_new_confirmation(self):
        p = package()
        plan = self.db.fundamentals.preview(p)
        self.db.fundamentals.import_package(p, confirmed=True)
        with self.assertRaises(ValueError):
            self.db.fundamentals.import_package(p, confirmed=True, expected_preview_token=plan.token)
        self.assertEqual(len(self.db.fundamentals.history(ISIN)), 7)


HAS_QT = importlib.util.find_spec("PySide6") is not None


@unittest.skipUnless(HAS_QT, "PySide6 niedostępne; testy interfejsu niewykonane")
class FundamentalGuiTests(FundamentalFixture):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_gui_preview_cancel_and_explicit_confirmation(self):
        from src.ui.fundamentals_dialog import FundamentalImportDialog
        preview = FundamentalImportDialog(self.db, str(EXAMPLE))
        self.assertFalse(preview.save_button.isEnabled())
        preview.reject()
        self.assertEqual(self.db.fundamentals.instruments(), [])
        preview.confirm.setChecked(True)
        preview._save()
        self.assertEqual(len(self.db.fundamentals.history(ISIN)), 7)
        preview.close()

    def test_gui_import_to_actual_review_and_manual_negative(self):
        from src.ui.review_dialog import ReviewDialog
        pid = self.db.insert_position(position())
        records = self.import_example()
        dialog = ReviewDialog(self.db, pid)
        self.assertEqual(dialog.review_date_edit.date().toString("yyyy-MM-dd"), date.today().isoformat())
        dialog.apply_fundamental_records(records)
        self.assertEqual(dialog._metric_value("roe"), 8.5)
        dialog.metric_widgets["roe"]["spin"].setValue(-12.5)
        dialog.notes_edit.setPlainText("Nowa rzeczywista ocena")
        dialog._calculate()
        self.assertTrue(dialog.save_button.isEnabled())
        dialog._save()
        saved = self.db.get_last_review_for_position(pid)
        self.assertEqual(saved.review_date, date.today().isoformat())
        self.assertEqual(saved.roe, -12.5)
        self.assertEqual(json.loads(saved.fundamental_evidence_json)["metric_inputs"]["roe"]["origin"], "manual")
        dialog.close()

    def test_gui_history_filters_and_selection(self):
        from src.ui.fundamentals_dialog import FundamentalsDialog
        self.import_example()
        dialog = FundamentalsDialog(self.db, ISIN, "2024-07-01", choose=True)
        self.assertEqual(len(dialog.records), 3)
        dialog.select_latest()
        dialog._use_selection()
        self.assertEqual(len(dialog.selected_records), 2)
        dialog.close()


if __name__ == "__main__":
    unittest.main()

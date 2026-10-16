#!/usr/bin/env python3
"""Local sales CSV audit and static HTML report. Python 3.11+, standard library only."""

from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal, localcontext
from html import escape
import json
from pathlib import Path
import re
import sys


COLUMNS = ("order_id", "date", "customer", "amount", "currency", "status")
STATUSES = ("paid", "pending", "refunded", "cancelled")
AMOUNT_PATTERN = re.compile(r"(?:0|[1-9][0-9]{0,17})(?:\.[0-9]{1,6})?\Z")
CURRENCY_PATTERN = re.compile(r"[A-Z]{3}\Z")
DATE_PATTERN = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}\Z")


def decimal_text(value: Decimal) -> str:
    """Preserve exact value; never use float or round to a currency's minor unit."""
    return format(value, "f")


def html_text(value: object) -> str:
    return escape(str(value), quote=True)


def read_rows(source: Path) -> tuple[list[dict], list[str]]:
    rows: list[dict] = []
    with source.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle, strict=True)
        try:
            header = next(reader)
        except StopIteration:
            raise ValueError("CSV vacío: no hay cabecera.") from None
        if len(header) != len(COLUMNS) or set(header) != set(COLUMNS):
            raise ValueError(
                "Cabecera inválida. Se requiere cada columna exactamente una vez: "
                + ",".join(COLUMNS)
                + ". Se permite otro orden, pero no columnas adicionales."
            )
        while True:
            start_line = reader.line_num + 1
            try:
                raw = next(reader)
            except StopIteration:
                break
            # Preserve even empty lines, extra fields and quoted multiline records.
            values = dict(zip(header, raw))
            reasons: list[str] = []
            if len(raw) != len(header):
                reasons.append(f"número de campos: {len(raw)}; se esperaban {len(header)}")
            cleaned = {key: values.get(key, "").strip() for key in COLUMNS}
            for field in COLUMNS:
                if not cleaned[field]:
                    reasons.append(f"{field}: obligatorio")

            if cleaned["date"]:
                try:
                    if not DATE_PATTERN.fullmatch(cleaned["date"]):
                        raise ValueError
                    date.fromisoformat(cleaned["date"])
                except ValueError:
                    reasons.append("date: fecha inválida; use YYYY-MM-DD")

            amount = None
            if cleaned["amount"]:
                # Validate before Decimal construction: excludes NaN, infinity,
                # signs, exponents, separators and unlimited-size numeric input.
                if not AMOUNT_PATTERN.fullmatch(cleaned["amount"]):
                    reasons.append(
                        "amount: use decimal no negativo, hasta 18 enteros y 6 decimales"
                    )
                else:
                    amount = Decimal(cleaned["amount"])
            if cleaned["currency"] and not CURRENCY_PATTERN.fullmatch(cleaned["currency"]):
                reasons.append("currency: se requieren 3 letras mayúsculas")
            if cleaned["status"] and cleaned["status"] not in STATUSES:
                reasons.append("status: use paid, pending, refunded o cancelled")

            rows.append(
                {
                    "record": len(rows) + 1,
                    "line_start": start_line,
                    "line_end": reader.line_num,
                    "raw": raw,
                    "values": cleaned,
                    "amount": amount,
                    "reasons": reasons,
                }
            )

    by_id: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        if row["values"]["order_id"]:
            by_id[row["values"]["order_id"]].append(row)
    for order_id, matches in by_id.items():
        if len(matches) > 1:
            records = ", ".join(str(row["record"]) for row in matches)
            for row in matches:
                row["reasons"].append(
                    f"order_id duplicado {order_id!r}: registros {records}; todos excluidos"
                )
    return rows, header


def summarize(rows: list[dict]) -> dict:
    accepted = [row for row in rows if not row["reasons"]]
    rejected = [row for row in rows if row["reasons"]]
    counts = Counter(row["values"]["status"] for row in accepted)
    totals: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    paid_counts: Counter = Counter()
    # Enough precision for each allowed 24-digit amount plus every row's carry.
    # This protects exact addition even for very large, in-memory CSV batches.
    with localcontext() as context:
        context.prec = 30 + len(str(max(1, len(rows))))
        for row in accepted:
            if row["values"]["status"] == "paid":
                currency = row["values"]["currency"]
                totals[currency] += row["amount"]
                paid_counts[currency] += 1
    duplicates = Counter(row["values"]["order_id"] for row in rows if row["values"]["order_id"])
    return {
        "demonstration": True,
        "notice": "DEMOSTRACIÓN / DATOS FICTICIOS. No son ingresos reales.",
        "records": len(rows),
        "accepted": len(accepted),
        "rejected": len(rejected),
        "accepted_by_status": {status: counts[status] for status in STATUSES},
        "duplicate_ids": {key: count for key, count in sorted(duplicates.items()) if count > 1},
        "paid_by_currency": {
            currency: {"count": paid_counts[currency], "total": decimal_text(totals[currency])}
            for currency in sorted(totals)
        },
    }


def write_report(source: Path, destination: Path, rows: list[dict], summary: dict) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    totals_html = "".join(
        f"<tr><td>{html_text(currency)}</td><td>{data['count']}</td>"
        f"<td>{html_text(data['total'])}</td></tr>"
        for currency, data in summary["paid_by_currency"].items()
    ) or '<tr><td colspan="3">No hay ventas pagadas válidas.</td></tr>'
    status_html = "".join(
        f"<li><code>{html_text(status)}</code>: {count}</li>"
        for status, count in summary["accepted_by_status"].items()
    )
    trace_html = []
    for row in rows:
        accepted = not row["reasons"]
        status = "Aceptada" if accepted else "Rechazada"
        trace_html.append(
            f'<tr class="{"accepted" if accepted else "rejected"}">'
            f"<td>{row['record']}</td><td>{row['line_start']}–{row['line_end']}</td>"
            f"<td>{html_text(row['values']['order_id'])}</td><td>{status}</td>"
            f"<td>{html_text('; '.join(row['reasons']) or 'Validación correcta')}</td>"
            f"<td><pre>{html_text(json.dumps(row['raw'], ensure_ascii=False))}</pre></td></tr>"
        )
    document = f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>Demostración — informe de ventas</title>
<style>
body{{font:16px/1.55 system-ui,sans-serif;color:#192b40;background:#f3f6fa;margin:0}}
main{{max-width:1250px;margin:32px auto;padding:0 24px 40px}}
h1{{font-size:2rem;line-height:1.2}}h2{{margin-top:2rem}}
.notice{{background:#fff1c2;border-left:6px solid #b16b00;padding:16px;font-weight:700}}
.cards{{display:flex;gap:16px;flex-wrap:wrap;margin:24px 0}}
.card{{background:white;border:1px solid #d6dfea;border-radius:10px;padding:16px 24px;min-width:150px}}
.number{{display:block;font-size:2rem;font-weight:750;color:#144d80}}
.table-wrap{{overflow:auto;background:white;border:1px solid #d6dfea;border-radius:8px}}
table{{width:100%;border-collapse:collapse;font-size:.9rem}}th,td{{padding:12px;text-align:left;border-bottom:1px solid #e0e6ee;vertical-align:top}}
th{{background:#193b5a;color:white}}.rejected{{background:#fff2ef}}
pre{{white-space:pre-wrap;overflow-wrap:anywhere;min-width:240px;margin:0;font-size:.8rem}}
code{{font-size:.9em}}.muted{{color:#4e6175}}footer{{margin-top:30px}}
</style></head><body><main>
<p class="notice">DEMOSTRACIÓN / DATOS FICTICIOS. Los importes de este informe son ejemplos; no son ingresos reales.</p>
<h1>Ventas claras, con cada fila explicada</h1>
<p class="muted">Fuente local: <code>{html_text(source.name)}</code>. Validación y cálculo realizados sin red.</p>
<div class="cards">
<div class="card">Registros leídos<span class="number">{summary['records']}</span></div>
<div class="card">Aceptados<span class="number">{summary['accepted']}</span></div>
<div class="card">Rechazados<span class="number">{summary['rejected']}</span></div>
<div class="card">IDs duplicados<span class="number">{len(summary['duplicate_ids'])}</span></div>
</div>
<h2>Ventas pagadas, por divisa</h2>
<p>Solo se suman filas aceptadas con estado <code>paid</code>. Cada divisa tiene su propio total, sin conversiones. Los reembolsos no se compensan ni se calcula ingreso neto.</p>
<div class="table-wrap"><table><thead><tr><th>Divisa</th><th>Ventas pagadas</th><th>Importe exacto</th></tr></thead><tbody>{totals_html}</tbody></table></div>
<h2>Estados de las filas aceptadas</h2><ul>{status_html}</ul>
<h2>Trazabilidad completa</h2>
<p>Se conserva cada registro, incluidos los rechazados. Las líneas físicas permiten localizar registros con texto multilínea. Un ID repetido excluye todas sus apariciones, incluso si una ya tenía otro error. Los valores originales se muestran como una lista en este orden: <code>{html_text(','.join(summary['source_columns']))}</code>.</p>
<div class="table-wrap"><table><thead><tr><th>Registro</th><th>Líneas CSV</th><th>Pedido</th><th>Resultado</th><th>Razón</th><th>Valores originales</th></tr></thead><tbody>{''.join(trace_html)}</tbody></table></div>
<footer class="muted">Archivos complementarios: <code>rejected_rows.csv</code> y <code>audit.json</code>. Informe estático; no carga scripts ni recursos externos.</footer>
</main></body></html>"""
    (destination / "report.html").write_text(document, encoding="utf-8")
    with (destination / "rejected_rows.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(("record", "line_start", "line_end", "reasons", "original_fields_json"))
        for row in rows:
            if row["reasons"]:
                writer.writerow(
                    (row["record"], row["line_start"], row["line_end"],
                     "; ".join(row["reasons"]), json.dumps(row["raw"], ensure_ascii=False))
                )
    audit = {**summary, "source": source.name, "rows": [
        {key: value for key, value in row.items() if key != "amount"} for row in rows
    ]}
    (destination / "audit.json").write_text(
        json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="CSV UTF-8 de ventas")
    parser.add_argument("--output", type=Path, default=Path("output"), help="Carpeta de resultados (predeterminada: output)")
    args = parser.parse_args()
    try:
        # Read and validate before creating outputs; malformed CSV and bad headers
        # fail explicitly. Never overwrite the input with a generated artifact.
        if args.input.resolve() in {
            (args.output / name).resolve()
            for name in ("report.html", "rejected_rows.csv", "audit.json")
        }:
            raise ValueError("La ruta de entrada coincide con un archivo de salida.")
        rows, header = read_rows(args.input)
        summary = summarize(rows)
        summary["source_columns"] = header
        write_report(args.input, args.output, rows, summary)
    except (OSError, UnicodeError, csv.Error, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    print(summary["notice"])
    print(f"Registros: {summary['records']}; aceptados: {summary['accepted']}; rechazados: {summary['rejected']}")
    for currency, data in summary["paid_by_currency"].items():
        print(f"paid {currency}: {data['total']} ({data['count']} ventas)")
    print(f"Informe: {(args.output / 'report.html').resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

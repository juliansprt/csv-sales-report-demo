# Repeatable sales CSV reports — USD 125

Turn a recurring sales export into an HTML report you can regenerate with one command.

This repository is a working sample. **Every customer, order and amount in the example is fictional.** The output demonstrates the reporting workflow; it does not represent customer work or revenue earned by this service.

## What the fixed-price service includes

For **USD 125**, I adapt a Python script to one agreed CSV format, with up to 10,000 rows per run after checking a sample:

- Validate required fields, dates, amounts and order identifiers.
- Flag repeated order IDs and ambiguous rows for review.
- Calculate paid-sales totals separately for each currency.
- Generate a local HTML report, a rejected-row file and a row-level audit.
- Deliver the reusable script, run instructions and one correction within the agreed scope.

We confirm the columns, validation rules, expected output and delivery date after reviewing an anonymized sample. External integrations, hosting, scheduled operation and additional formats are outside this initial scope.

**Request a fit check:** [open a report request](https://github.com/juliansprt/csv-sales-report-demo/issues/new?template=report-request.yml). Describe the input, desired output, approximate row count and deadline. Use fictional examples in public issues; do not post customer records, account credentials or private files.

Payment is by [PayPal](https://paypal.me/julOsp?locale.x=es_XC&country.x=CO), after the scope and a preview have been agreed. Please confirm the work before paying. Any applicable payment fees and currency conversion are confirmed before accepting an order.

The service is offered through [@juliansprt](https://github.com/juliansprt). The sample was prepared with AI assistance and checked by running it. No testimonials or prior client results are claimed.

## Run the sample

Requires Python 3.11 or later. No third-party packages, network access or API keys are needed.

```sh
python sales_report.py example_sales.csv --output output
```

On Windows with the Python launcher:

```powershell
py -3 sales_report.py example_sales.csv --output output
```

Open `output/report.html` in your browser. A generated example is included in [`example-output/report.html`](example-output/report.html). The other outputs are `audit.json` and `rejected_rows.csv`. Running again replaces these three generated files; the script rejects an output path that would overwrite the input.

The example produces **16 records: 8 accepted and 8 rejected**. Its fictional paid-sales totals are **USD 200.00 across 3 orders** and **COP 500000.50 across 2 orders**. Accepted statuses are paid 5, pending 1, refunded 1 and cancelled 1. Both records with duplicate ID `FICT-006` are rejected.

## Current sample format and rules

```csv
order_id,date,customer,amount,currency,status
FICT-EXAMPLE,2026-10-01,Fictional customer,125.50,USD,paid
```

- UTF-8 CSV, comma separated. Quote fields containing commas, quotes or line breaks.
- Each of the six headers must occur exactly once; another column order is allowed. Additional columns require an agreed adaptation.
- All fields are required. Outer spaces are trimmed for validation; original fields are retained in the audit.
- Dates must be real dates in `YYYY-MM-DD` format.
- Amounts use exact decimal arithmetic, a decimal point, up to 18 integer digits and 6 fractional digits. No negative values, exponent notation, NaN or infinity.
- Currency is three uppercase letters. This checks the format, not a currency registry. Totals are never combined across currencies.
- Supported statuses are `paid`, `pending`, `refunded` and `cancelled`. Only accepted `paid` rows contribute to the totals. Refunds are not netted against sales; this is not a net-income or accounting report.
- Order IDs are case sensitive after trimming. Every occurrence of a repeated ID is rejected, with the source records listed.
- Every parsed record is accounted for, including blank or wrong-width rows. Invalid encoding, malformed CSV or invalid headers fail explicitly before new outputs are written.
- Values are escaped in the HTML. The report is static and loads no external resources.

The demonstration notice remains visible when this sample is run with another file. A commissioned version would be adapted and verified against the customer's agreed data rules.

## En español

**Automatización de un reporte CSV de ventas: 125 USD.** Incluye una fuente y un formato acordados, validaciones, pedidos repetidos, totales por divisa, reporte HTML, incidencias, código reutilizable e instrucciones. El plazo y las reglas se confirman al revisar una muestra anonimizada. Incluye una corrección dentro del alcance acordado.

[Solicitar el servicio](https://github.com/juliansprt/csv-sales-report-demo/issues/new?template=report-request.yml). Describe las columnas, cantidad aproximada de filas, resultado y plazo deseados. En una solicitud pública, utiliza datos ficticios. El cobro por PayPal se acuerda después de confirmar el trabajo y revisar una vista previa.

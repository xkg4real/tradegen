# Quant Council pages (offline copies)

All panel members in these documents are simulated, fictional composites; nothing speaks for any real firm or person.
Not investment advice: QUANTGEN is a read-only research desk with no order path.

| File | What it is | sha256 |
|---|---|---|
| `QUANTGEN_Quant_Council.html` | Verbatim copy of `QUANTGEN_Quant_Council_2026-10-03/pages/QUANTGEN_Quant_Council.html` (the council: ledger of 361 items, 34 modules, resolutions, owner decisions) | `0aa2bb10b391c87b2664e46f4bc6f0300f3965cb877bcac25059cd0358d9d3aa` |
| `QUANTGEN_Macro_Neural_Link.html` | Verbatim copy of `QUANTGEN_Quant_Council_2026-10-03/pages/QUANTGEN_Macro_Neural_Link.html` (the macro neural link: 60 research nodes, overlay-rule evidence) | `b7c71bff74a74b3acc011bf120e150626d8d0d4ade81ca0923f8f775779ccee5` |
| `council_pages_data.json` | `{"quant_council": <QC #qg-data>, "macro_neural_link": <ML #qg-data>}`, extracted once from the two pages | — |

Both pages are self-contained: data are embedded in one `<script type="application/json" id="qg-data">` block each,
there is no external script, image or `fetch(`, and fonts fall back to system fonts offline. Open them in the system
browser (operator-initiated; the app never fetches the outbound links they carry).

Extraction (reproducible, no dependencies):

```python
import re, json, pathlib
s = pathlib.Path(p).read_text(encoding="utf-8")
D = json.loads(re.search(r'<script type="application/json" id="qg-data">(.*?)</script>', s, re.S).group(1))
```

Status of the content: verdicts and numbers are indicative full-sample computations outside QUANTGEN's own gate; the
macro series are latest vintage, not as first published; the `dest` routing of the neural-link nodes is the
2 Oct pre-council routing. Nothing here is an acting input: the binding rules are the macro specification v2.0
and the rules store `data/macro/rules_v2.0.0.json`. Reports: `reports/QUANTGEN_Quant_Council_Report.md` and
`reports/QUANTGEN macro overlay research.md`.

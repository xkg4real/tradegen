# Strategy research paper build

The PDF is a retrospective computational research report, not a peer-reviewed publication or production strategy certification. It excludes private owner amounts and deployment dates.

`tools/build_strategy_paper.py` reads completed research result files, creates vector figures and a Korean/English LaTeX manuscript, and invokes XeLaTeX with shell escape disabled and task-local caches. It does not import trading modules, fetch data, select a strategy, sign, arm, or submit an order.

Required inputs: the completed `results/summary.json`, full candidate CSV, selected daily series and their protocol/data manifests. The builder refuses missing numerical evidence rather than substituting illustrative performance. The figure and table labels preserve retrospective holdout status, currency and cost assumptions.

The PDF's reference list comes from `bibliography.json`. Verification records distinguish publisher metadata/abstract checks from full-text access; no inaccessible article is described as fully read. No copyrighted full papers are bundled.

A final PDF, source `.tex`, figure PDFs, an integrity manifest and complete result CSV supplements are retained. Compilation auxiliaries and local font/TeX caches belong outside the publication files.

Completed computation: 21,408 asset/configuration pairs, six frozen selections, zero selections satisfying all preregistered exploratory conditions. Four selections had positive arithmetic mean returns, but only three had positive compound growth. All six had lower compound growth than their costed same-asset buy-and-hold benchmark. The PDF discusses cost sensitivity, exposure versus drawdown, execution lag, and benchmark-relative uncertainty.

Build from the repository root after the completed study outputs exist:

```bash
python tools/build_strategy_paper.py
```

Defaults write the publication copy here and a user artifact at `/workspace/tradegen-session/artifacts/TRADEGEN_Strategy_Research.pdf`. Use `--results`, `--output`, `--artifact`, and `--scratch` to change destinations. The generator checks result counts, source/registry hashes, and selected daily return reconciliation before rendering. Numerical evidence comes from the frozen computation commit recorded in `results/summary.json`; rebuilding the paper does not rerun it.

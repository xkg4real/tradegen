# Pre-start amendments (KRX session 2026-10-12)

| KST | What |
|---|---|
| 10:16 | PAPER_PROFILE=krx added to config.py (base profile values unchanged; the base config hash changed from ffbdfc4d489bcaf2 to fd50c3194378dc74 only because the file grew). Engine gained a generic FX translator (KRW via USD/KRW), KRX session hours and cash-venue lists; base regression script passed. |
| 10:18 | KRX model calibrated on 60 days of 5-minute bars with the same zero-intercept procedure. |

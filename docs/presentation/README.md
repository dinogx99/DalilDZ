# DalilDZ presentation materials

| File | What it is |
| --- | --- |
| [DalilDZ-presentation.pdf](DalilDZ-presentation.pdf) | 12-slide project presentation (16:9) |
| [DalilDZ-overview.png](DalilDZ-overview.png) | One-image project overview for sharing |
| [sample-evidence-report.pdf](sample-evidence-report.pdf) | Evidence report exported from the app (synthetic data) |
| [screenshots/](screenshots/) | Screenshots of the web app in English and Arabic, desktop and mobile |

`deck.html` and `overview.html` are the sources. To re-render them, open them in Chromium and
print to PDF at 1280×720 with background graphics enabled (or use Playwright `page.pdf`).

All examples use **SYNTHETIC TEST DATA**. On the screenshots, `website` shows
`SOURCE_UNAVAILABLE` because they were taken in an environment without DNS — which is exactly how
DalilDZ reports a source failure instead of claiming "not found".

# PRAGATI Prototype — SIH26103

A Streamlit prototype for an explainable infrastructure project monitoring intelligence layer.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

Keep `app.py`, `Projects_Report.xlsx`, and the nine monthly report files in the same folder. The monthly report filenames are used directly by the app.

## Features

- Overview of the current project-level snapshot
- Project Intelligence with a transparent attention screening score and indicator explanations
- Historical Memory for contextual project comparisons
- Risk Analyst with June–August 2026 portfolio-level cost, expenditure, sector, state/UT and physical-progress trends
- Methodology page explaining assumptions and limitations

## Data and interpretation boundary

The project-level workbook is a single snapshot. Its attention score is a transparent screening proxy, **not** a trained prediction or probability of failure. The June–August reports are aggregate reports; they support portfolio-level trend analysis but do not provide monthly histories for individual projects. The app therefore does not claim individual-project trajectory prediction or validated forecast accuracy.

## Monthly report mapping

- June: `Cost-Wise-Report (6).xlsx` (portfolio totals), `Cost-Wise-Report (7).xlsx` (state/UT), `Sector-Wise-Report (3).xlsx`, `Physical-Progress-Report (3).xlsx`
- July: `Cost-Wise-Report (4).xlsx` (portfolio totals), `Cost-Wise-Report (5).xlsx` (state/UT), `Sector-Wise-Report (2).xlsx`, `Physical-Progress-Report (2).xlsx`
- August: `Cost-Wise-Report (2).xlsx` (portfolio totals), `Cost-Wise-Report (3).xlsx` (state/UT), `Sector-Wise-Report (1).xlsx`, `Physical-Progress-Report (1).xlsx`

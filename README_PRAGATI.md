# PRAGATI Prototype

A Streamlit proof-of-concept for SIH26103 using the supplied PAIMANA project-level report.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

The app reads `Projects_Report.xlsx` from the same folder.

## Important prototype boundary

The supplied public project report is a current snapshot, not a longitudinal history. Therefore this prototype uses a transparent **attention/risk screening proxy** based on cost escalation, schedule revision, and expenditure–progress divergence. It does **not** claim trained future-outcome prediction or accuracy.

With multiple monthly PAIMANA/CUF snapshots, the same interface can be extended to train and evaluate longitudinal cost/schedule risk models using time-based splits.

## Suggested demo flow

1. Open Overview.
2. Pick a project in Project Intelligence.
3. Show the attention score and the evidence behind it.
4. Open Historical Memory and show comparable projects.
5. Open Methodology if asked how the prototype avoids overclaiming.

import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

st.set_page_config(page_title='PRAGATI | Infrastructure Intelligence', page_icon='📊', layout='wide')

DATA_FILE = Path(__file__).parent / 'Projects_Report.xlsx'

@st.cache_data

def load_data():
    df = pd.read_excel(DATA_FILE, skiprows=2)
    df = df.dropna(how='all').copy()
    rename = {
        'Sector Name':'sector',
        'Line Ministry':'ministry',
        'Implementing Agency':'agency',
        'Project Code':'code',
        'Project Name':'name',
        'Original Cost\n(in cr.)':'original_cost',
        'Revised Cost\n(in cr.)':'revised_cost',
        'Expenditure\n(in cr.)':'expenditure',
        'Physical Progress\n(in %)':'progress',
        'Original\nDate of Commissioning':'original_date',
        'Revised\nDate of Commissioning':'revised_date',
        'Sanction Date':'sanction_date',
    }
    df = df.rename(columns=rename)
    for c in ['original_cost','revised_cost','expenditure','progress']:
        df[c] = pd.to_numeric(df[c], errors='coerce')
    for c in ['original_date','revised_date','sanction_date']:
        df[c] = pd.to_datetime(df[c], dayfirst=True, errors='coerce')
    df['code'] = df['code'].astype(str).str.replace('.0','', regex=False).str.strip()

    df['cost_escalation_pct'] = np.where(df.original_cost > 0, (df.revised_cost/df.original_cost - 1)*100, np.nan)
    df['expenditure_share_pct'] = np.where(df.revised_cost > 0, df.expenditure/df.revised_cost*100, np.nan)
    df['progress_gap_pct'] = df.expenditure_share_pct - df.progress
    df['schedule_delay_days'] = (df.revised_date - df.original_date).dt.days
    df['schedule_delay_months'] = df.schedule_delay_days/30.44
    return df

df = load_data()

# A transparent prototype attention score, NOT a trained future-outcome model.
def add_risk_score(d):
    x = d.copy()
    # Robust caps prevent extreme outliers from dominating the score.
    cost = x.cost_escalation_pct.clip(lower=0, upper=100).fillna(0)
    delay = x.schedule_delay_months.clip(lower=0, upper=60).fillna(0)
    gap = x.progress_gap_pct.clip(lower=0, upper=50).fillna(0)
    # Scale to 0-100 components.
    cost_s = (cost/100)*100
    delay_s = (delay/60)*100
    gap_s = (gap/50)*100
    x['risk_score'] = (0.40*cost_s + 0.35*delay_s + 0.25*gap_s).clip(0,100)
    x['risk_level'] = pd.cut(x.risk_score, bins=[-0.01,30,60,100], labels=['LOW','MEDIUM','HIGH'])
    return x

df = add_risk_score(df)

st.markdown('''
<style>
.main-title {font-size: 2.15rem; font-weight: 800; margin-bottom: 0.1rem;}
.sub-title {font-size: 1.02rem; color: #536273; margin-bottom: 1.2rem;}
.card {padding: 1rem 1.1rem; border: 1px solid #e4e8ee; border-radius: 14px; background: white;}
.small {font-size: .82rem; color:#657385;}
.badge {display:inline-block; padding:.28rem .62rem; border-radius:999px; font-weight:700; font-size:.78rem;}
</style>
''', unsafe_allow_html=True)

st.markdown('<div class="main-title">PRAGATI</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Predictive Risk Analytics for Government Infrastructure Tracking & Intelligence</div>', unsafe_allow_html=True)

st.info('Prototype mode: this build uses the supplied PAIMANA project-level snapshot. The risk score is a transparent screening proxy, not a trained future-outcome prediction. Longitudinal prediction activates when multiple reporting snapshots are available.')

# Sidebar filters
st.sidebar.header('Project Filters')
sector_options = ['All'] + sorted(df['sector'].dropna().unique().tolist())
ministry_options = ['All'] + sorted(df['ministry'].dropna().unique().tolist())
sector = st.sidebar.selectbox('Sector', sector_options)
ministry = st.sidebar.selectbox('Ministry / Department', ministry_options)
min_progress, max_progress = st.sidebar.slider('Physical progress (%)', 0, 100, (0,100))

filtered = df.copy()
if sector != 'All': filtered = filtered[filtered.sector == sector]
if ministry != 'All': filtered = filtered[filtered.ministry == ministry]
filtered = filtered[filtered.progress.between(min_progress, max_progress, inclusive='both')]

# Top metrics
c1,c2,c3,c4 = st.columns(4)
c1.metric('Projects in view', f'{len(filtered):,}')
c2.metric('Original cost', f'₹{filtered.original_cost.sum()/1000:,.1f}k cr')
c3.metric('Revised cost', f'₹{filtered.revised_cost.sum()/1000:,.1f}k cr')
c4.metric('High-attention projects', f'{(filtered.risk_level == "HIGH").sum():,}')

st.divider()

# Navigation
page = st.radio('PRAGATI intelligence', ['Overview','Project Intelligence','Historical Memory','Methodology'], horizontal=True, label_visibility='collapsed')

if page == 'Overview':
    left, right = st.columns([1.55,1])
    with left:
        st.subheader('Emerging-risk landscape')
        chart = (filtered['risk_level'].value_counts().reindex(['HIGH','MEDIUM','LOW']).fillna(0).astype(int))
        st.bar_chart(chart)
        st.caption('Attention levels are based on cost escalation, schedule revision and expenditure–progress divergence in the current snapshot.')
    with right:
        st.subheader('Highest attention')
        cols = ['code','name','risk_score','risk_level','cost_escalation_pct','schedule_delay_months']
        top = filtered.sort_values('risk_score', ascending=False)[cols].head(8).copy()
        top['risk_score'] = top['risk_score'].round(1)
        top['cost_escalation_pct'] = top['cost_escalation_pct'].round(1)
        top['schedule_delay_months'] = top['schedule_delay_months'].round(1)
        st.dataframe(top, use_container_width=True, hide_index=True)

elif page == 'Project Intelligence':
    st.subheader('Project Intelligence')
    choices = filtered.sort_values('risk_score', ascending=False)
    if len(choices) == 0:
        st.warning('No projects match the current filters.')
    else:
        selected_code = st.selectbox('Select project', choices['code'].tolist(), format_func=lambda x: f"{x} — {choices.loc[choices.code==x,'name'].iloc[0][:85]}")
        p = df[df.code == selected_code].iloc[0]
        st.markdown(f'### {p["name"]}')
        st.caption(f'Project code {p.code} · {p.sector} · {p.ministry}')
        a,b,c,d = st.columns(4)
        a.metric('Physical progress', f'{p.progress:.0f}%')
        b.metric('Cost escalation', f'{p.cost_escalation_pct:+.1f}%')
        c.metric('Expenditure / revised cost', f'{p.expenditure_share_pct:.1f}%')
        d.metric('Schedule revision', f'{p.schedule_delay_months:+.1f} mo')

        st.markdown('#### PRAGATI attention signal')
        level = str(p.risk_level)
        st.progress(int(p.risk_score), text=f'{level} · prototype attention score {p.risk_score:.1f}/100')

        st.markdown('#### Why is this project being flagged?')
        reasons = []
        if p.cost_escalation_pct > 10: reasons.append(f'Cost escalation is {p.cost_escalation_pct:.1f}% above the original approved cost.')
        if p.schedule_delay_months > 3: reasons.append(f'Revised commissioning is {p.schedule_delay_months:.1f} months after the original date.')
        if p.progress_gap_pct > 10: reasons.append(f'Expenditure share ({p.expenditure_share_pct:.1f}%) is ahead of physical progress ({p.progress:.1f}%) by {p.progress_gap_pct:.1f} percentage points.')
        if not reasons: reasons.append('No strong attention signal is triggered by the current prototype rules.')
        for r in reasons: st.write('• ' + r)

        st.caption('Interpretation: these are risk indicators, not causal findings. A trained longitudinal model would require historical reporting snapshots and future-outcome labels.')

        st.markdown('#### Project facts')
        facts = pd.DataFrame({
            'Metric':['Original cost','Revised cost','Expenditure','Original commissioning','Revised commissioning','Implementing agency'],
            'Value':[f'₹{p.original_cost:,.2f} cr',f'₹{p.revised_cost:,.2f} cr',f'₹{p.expenditure:,.2f} cr',p.original_date.strftime('%d %b %Y') if pd.notna(p.original_date) else '—',p.revised_date.strftime('%d %b %Y') if pd.notna(p.revised_date) else '—',p.agency]
        })
        st.dataframe(facts, use_container_width=True, hide_index=True)

elif page == 'Historical Memory':
    st.subheader('Historical Institutional Memory')
    st.caption('Prototype analogue engine: finds projects with similar sector, progress, cost scale and expenditure share. Similarity is contextual, not proof of a common outcome.')
    selected_code = st.selectbox('Project to compare', filtered.sort_values('risk_score',ascending=False)['code'].tolist(), key='hist')
    p = df[df.code == selected_code].iloc[0]
    cand = df[df.code != selected_code].copy()
    cand = cand[cand.sector == p.sector] if (p.sector in set(cand.sector.dropna())) else cand
    if len(cand) < 5: cand = df[df.code != selected_code].copy()
    # standardized distance over four comparable features
    features = ['progress','original_cost','expenditure_share_pct','cost_escalation_pct']
    base = df[features].copy()
    med = base.median(numeric_only=True)
    mad = (base - med).abs().median(numeric_only=True).replace(0,1)
    z = ((cand[features] - p[features]) / mad).replace([np.inf,-np.inf],np.nan).fillna(0)
    cand['similarity_distance'] = np.sqrt((z**2).sum(axis=1))
    analogues = cand.sort_values('similarity_distance').head(5).copy()
    show = analogues[['code','name','sector','progress','cost_escalation_pct','expenditure_share_pct','risk_level']].copy()
    show['progress'] = show.progress.round(1)
    show['cost_escalation_pct'] = show.cost_escalation_pct.round(1)
    show['expenditure_share_pct'] = show.expenditure_share_pct.round(1)
    show.columns = ['Project Code','Project Name','Sector','Progress %','Cost Escalation %','Expenditure / Revised Cost %','Attention']
    st.dataframe(show, use_container_width=True, hide_index=True)

elif page == 'Methodology':
    st.subheader('How the prototype works')
    st.markdown('''
**Current snapshot layer**

PAIMANA project-level fields → validation → derived indicators → transparent attention score → explanation → historical analogues.

**Derived indicators**

- Cost escalation = (Revised Cost / Original Cost − 1) × 100
- Expenditure share = Expenditure / Revised Cost × 100
- Progress–expenditure gap = Expenditure share − Physical progress
- Schedule revision = Revised commissioning date − Original commissioning date

**Prototype attention score**

40% cost escalation + 35% schedule revision + 25% positive progress–expenditure gap, with robust caps to reduce outlier domination.

**What is deliberately NOT claimed**

This snapshot alone cannot establish future-overrun prediction accuracy. Longitudinal prediction requires multiple reporting periods and a future outcome definition, followed by time-based train/validation/test evaluation.
''')

st.divider()
st.caption('PRAGATI prototype · Built on the supplied PAIMANA project report · For demonstration and decision-support concept validation')

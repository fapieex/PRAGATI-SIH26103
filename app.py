import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

st.set_page_config(
    page_title='PRAGATI | Infrastructure Intelligence',
    page_icon='🇮🇳',
    layout='wide'
)

DATA_FILE = Path(__file__).parent / 'Projects_Report.xlsx'


@st.cache_data
def load_data():
    df = pd.read_excel(DATA_FILE, skiprows=2)
    df = df.dropna(how='all').copy()

    rename = {
        'Sector Name': 'sector',
        'Line Ministry': 'ministry',
        'Implementing Agency': 'agency',
        'Project Code': 'code',
        'Project Name': 'name',
        'Original Cost\n(in cr.)': 'original_cost',
        'Revised Cost\n(in cr.)': 'revised_cost',
        'Expenditure\n(in cr.)': 'expenditure',
        'Physical Progress\n(in %)': 'progress',
        'Original\nDate of Commissioning': 'original_date',
        'Revised\nDate of Commissioning': 'revised_date',
        'Sanction Date': 'sanction_date',
    }

    df = df.rename(columns=rename)

    numeric_columns = [
        'original_cost',
        'revised_cost',
        'expenditure',
        'progress'
    ]

    for c in numeric_columns:
        df[c] = pd.to_numeric(
            df[c],
            errors='coerce'
        ).astype('float64')

    for c in [
        'original_date',
        'revised_date',
        'sanction_date'
    ]:
        df[c] = pd.to_datetime(
            df[c],
            dayfirst=True,
            errors='coerce'
        )

    df['code'] = (
        df['code']
        .astype(str)
        .str.replace('.0', '', regex=False)
        .str.strip()
    )

    df['cost_escalation_pct'] = np.where(
        (df['original_cost'] > 0) &
        (df['revised_cost'] > 0),
        (
            df['revised_cost'] /
            df['original_cost'] - 1
        ) * 100,
        np.nan
    )

    df['expenditure_share_pct'] = np.where(
        df['revised_cost'] > 0,
        (
            df['expenditure'] /
            df['revised_cost']
        ) * 100,
        np.nan
    )

    df['progress_gap_pct'] = (
        df['expenditure_share_pct'] -
        df['progress']
    )

    df['schedule_delay_days'] = (
        df['revised_date'] -
        df['original_date']
    ).dt.days

    df['schedule_delay_months'] = (
        df['schedule_delay_days'] / 30.44
    )

    derived_columns = [
        'cost_escalation_pct',
        'expenditure_share_pct',
        'progress_gap_pct',
        'schedule_delay_days',
        'schedule_delay_months'
    ]

    for c in derived_columns:
        df[c] = pd.to_numeric(
            df[c],
            errors='coerce'
        ).astype('float64')

    return df


df = load_data()


# ---------------------------------------------------------
# Transparent prototype attention score
# NOT a trained future-outcome prediction model.
# ---------------------------------------------------------

def add_risk_score(d):
    x = d.copy()

    # Convert indicators to numeric
    cost = pd.to_numeric(
        x['cost_escalation_pct'],
        errors='coerce'
    )

    delay = pd.to_numeric(
        x['schedule_delay_months'],
        errors='coerce'
    )

    gap = pd.to_numeric(
        x['progress_gap_pct'],
        errors='coerce'
    )

    # Treat impossible / unusable values as unavailable
    # Negative cost escalation is not treated as a risk signal.
    cost = cost.where(cost >= 0)
    delay = delay.where(delay >= 0)
    gap = gap.where(gap >= 0)

    # Cap valid values
    cost = cost.clip(lower=0, upper=100)
    delay = delay.clip(lower=0, upper=60)
    gap = gap.clip(lower=0, upper=50)

    # Convert each valid indicator to a 0–100 contribution
    cost_s = (cost / 100) * 100
    delay_s = (delay / 60) * 100
    gap_s = (gap / 50) * 100

    # Original weights
    weights = pd.DataFrame({
        'cost': 0.40,
        'delay': 0.35,
        'gap': 0.25
    }, index=x.index)

    # Which indicators are actually available?
    valid = pd.DataFrame({
        'cost': cost.notna(),
        'delay': delay.notna(),
        'gap': gap.notna()
    }, index=x.index)

    # Weighted contributions
    weighted = pd.DataFrame({
        'cost': cost_s * weights['cost'],
        'delay': delay_s * weights['delay'],
        'gap': gap_s * weights['gap']
    }, index=x.index)

    # Remove unavailable indicators from both numerator and denominator
    weighted = weighted.where(valid, 0)

    available_weight = (
        weights.where(valid, 0)
        .sum(axis=1)
    )

    total_score = weighted.sum(axis=1)

    # Renormalize based on available indicators
    x['risk_score'] = np.where(
        available_weight > 0,
        (total_score / available_weight).clip(0, 100),
        np.nan
    )

    x['risk_score'] = x['risk_score'].astype(float)

    # Risk level
    x['risk_level'] = pd.cut(
        x['risk_score'],
        bins=[-0.01, 30, 60, 100],
        labels=['LOW', 'MEDIUM', 'HIGH']
    )

    return x


df = add_risk_score(df)


# ---------------------------------------------------------
# Monthly portfolio reports (June–August 2026)
# These are aggregate reports, not project-level histories.
# ---------------------------------------------------------
REPORT_FILES = {
    'June': {
        'cost': 'Cost-Wise-Report (6).xlsx',
        'sector': 'Sector-Wise-Report (3).xlsx',
        'progress': 'Physical-Progress-Report (3).xlsx',
        'state': 'Cost-Wise-Report (7).xlsx',
    },
    'July': {
        'cost': 'Cost-Wise-Report (4).xlsx',
        'sector': 'Sector-Wise-Report (2).xlsx',
        'progress': 'Physical-Progress-Report (2).xlsx',
        'state': 'Cost-Wise-Report (5).xlsx',
    },
    'August': {
        'cost': 'Cost-Wise-Report (2).xlsx',
        'sector': 'Sector-Wise-Report (1).xlsx',
        'progress': 'Physical-Progress-Report (1).xlsx',
        'state': 'Cost-Wise-Report (3).xlsx',
    },
}


def parse_report_number(value):
    """Convert Indian-formatted currency strings or numbers to float."""
    if pd.isna(value):
        return np.nan
    cleaned = str(value).replace('₹', '').replace(',', '').strip()
    try:
        return float(cleaned)
    except (TypeError, ValueError):
        return np.nan



def load_monthly_reports():
    rows = []
    sector_frames = {}
    progress_frames = {}
    state_frames = {}
    missing = []
    for month, files in REPORT_FILES.items():
        cost_path = Path(__file__).parent / files['cost']
        sector_path = Path(__file__).parent / files['sector']
        progress_path = Path(__file__).parent / files['progress']
        state_path = Path(__file__).parent / files['state']
        if not all(path.exists() for path in [cost_path, sector_path, progress_path, state_path]):
            missing.append(month)
            continue
        cost_raw = pd.read_excel(cost_path, header=None)
        vals = cost_raw.iloc[2].tolist()
        rows.append({
            'Month': month,
            'Original Cost (₹ cr)': parse_report_number(vals[1]),
            'Revised Cost (₹ cr)': parse_report_number(vals[2]),
            'Expenditure (₹ cr)': parse_report_number(vals[3]),
        })
        sec = pd.read_excel(sector_path, skiprows=2, header=None)
        sec = sec.iloc[:, :5].copy()
        sec.columns = ['index', 'sector', 'project_count', 'cost_text', 'expenditure']
        sec['project_count'] = pd.to_numeric(sec['project_count'], errors='coerce')
        sec['expenditure'] = pd.to_numeric(sec['expenditure'], errors='coerce')
        sec['sector'] = sec['sector'].astype(str).str.strip()
        sec = sec[sec['sector'].notna() & (sec['sector'] != '') & (sec['sector'].str.lower() != 'nan')]
        # Cost cell contains original cost followed by revised cost in parentheses.
        sec['original_cost'] = sec['cost_text'].astype(str).str.extract(r'^\s*([\d,.]+)')[0].str.replace(',', '', regex=False)
        sec['revised_cost'] = sec['cost_text'].astype(str).str.extract(r'\(([\d,.]+)\)')[0].str.replace(',', '', regex=False)
        sec['original_cost'] = pd.to_numeric(sec['original_cost'], errors='coerce')
        sec['revised_cost'] = pd.to_numeric(sec['revised_cost'], errors='coerce')
        sector_frames[month] = sec
        prog = pd.read_excel(progress_path, skiprows=2, header=None)
        prog = prog.iloc[:, :5].copy()
        prog.columns = ['index', 'progress_band', 'project_count', 'cost_text', 'expenditure']
        prog['project_count'] = pd.to_numeric(prog['project_count'], errors='coerce')
        prog['progress_band'] = prog['progress_band'].astype(str).str.strip()
        prog = prog[prog['progress_band'].notna() & (prog['progress_band'] != '') & (prog['progress_band'].str.lower() != 'nan')]
        progress_frames[month] = prog

        # The second Cost-Wise report supplied for each month is the
        # state-wise table (despite its filename).
        state = pd.read_excel(state_path, skiprows=2, header=None)
        state = state.iloc[:, :5].copy()
        state.columns = ['index', 'state', 'project_count', 'cost_text', 'expenditure']
        state['project_count'] = pd.to_numeric(state['project_count'], errors='coerce')
        state['expenditure'] = pd.to_numeric(state['expenditure'], errors='coerce')
        state['state'] = state['state'].astype(str).str.strip()
        state = state[state['state'].notna() & (state['state'] != '') & (state['state'].str.lower() != 'nan')]
        state['original_cost'] = state['cost_text'].astype(str).str.extract(r'^\s*([\d,.]+)')[0].str.replace(',', '', regex=False)
        state['revised_cost'] = state['cost_text'].astype(str).str.extract(r'\(([\d,.]+)\)')[0].str.replace(',', '', regex=False)
        state['original_cost'] = pd.to_numeric(state['original_cost'], errors='coerce')
        state['revised_cost'] = pd.to_numeric(state['revised_cost'], errors='coerce')
        state_frames[month] = state

    return pd.DataFrame(rows), sector_frames, progress_frames, state_frames, missing


monthly, monthly_sectors, monthly_progress, monthly_states, missing_months = load_monthly_reports()


# ---------------------------------------------------------
# Styling
# ---------------------------------------------------------

st.markdown(
    '''
    <style>
    .main-title {
        font-size: 2.15rem;
        font-weight: 800;
        margin-bottom: 0.1rem;
    }

    .sub-title {
        font-size: 1.02rem;
        color: #536273;
        margin-bottom: 1.2rem;
    }

    .card {
        padding: 1rem 1.1rem;
        border: 1px solid #e4e8ee;
        border-radius: 14px;
        background: white;
    }

    .small {
        font-size: .82rem;
        color: #657385;
    }

    .attention-card {
        padding: 1rem 1.2rem;
        border: 1px solid #e4e8ee;
        border-radius: 14px;
        background: white;
        min-height: 145px;
    }

    .attention-label {
        font-size: .76rem;
        font-weight: 700;
        color: #687585;
        letter-spacing: .06em;
        margin-bottom: .45rem;
    }

    .attention-badge {
        display: inline-block;
        padding: .35rem .75rem;
        border-radius: 999px;
        font-weight: 800;
        font-size: .9rem;
        margin-bottom: .5rem;
    }

    .attention-description {
        font-size: .82rem;
        color: #657385;
    }
    </style>
    ''',
    unsafe_allow_html=True
)


# ---------------------------------------------------------
# Header
# ---------------------------------------------------------

st.markdown(
    '<div class="main-title">PRAGATI</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="sub-title">'
    'Predictive Risk Analytics for Government Infrastructure '
    'Tracking & Intelligence'
    '</div>',
    unsafe_allow_html=True
)

st.info(
    'Prototype mode: project-level intelligence uses the supplied PAIMANA '
    'snapshot, while Risk Analyst compares June–August portfolio aggregates. '
    'The attention score is a transparent screening proxy, not a trained '
    'future-outcome prediction. Aggregate monthly reports do not provide '
    'individual project trajectories.'
)


# ---------------------------------------------------------
# Sidebar filters
# ---------------------------------------------------------

st.sidebar.header('Project Filters')

sector_options = (
    ['All'] +
    sorted(
        df['sector']
        .dropna()
        .unique()
        .tolist()
    )
)

ministry_options = (
    ['All'] +
    sorted(
        df['ministry']
        .dropna()
        .unique()
        .tolist()
    )
)

sector = st.sidebar.selectbox(
    'Sector',
    sector_options
)

ministry = st.sidebar.selectbox(
    'Ministry / Department',
    ministry_options
)

min_progress, max_progress = st.sidebar.slider(
    'Physical progress (%)',
    0,
    100,
    (0, 100)
)

filtered = df.copy()

if sector != 'All':
    filtered = filtered[
        filtered['sector'] == sector
    ]

if ministry != 'All':
    filtered = filtered[
        filtered['ministry'] == ministry
    ]

filtered = filtered[
    filtered['progress'].between(
        min_progress,
        max_progress,
        inclusive='both'
    )
]


# ---------------------------------------------------------
# Top metrics
# ---------------------------------------------------------

c1, c2, c3, c4 = st.columns(4)

c1.metric(
    'Projects in view',
    f'{len(filtered):,}'
)

c2.metric(
    'Original cost',
    f'₹{filtered.original_cost.sum()/1000:,.1f}k cr'
)

c3.metric(
    'Revised cost',
    f'₹{filtered.revised_cost.sum()/1000:,.1f}k cr'
)

c4.metric(
    'High-attention projects',
    f'{(filtered.risk_level == "HIGH").sum():,}'
)

st.divider()


# ---------------------------------------------------------
# Navigation
# ---------------------------------------------------------

page = st.radio(
    'PRAGATI intelligence',
    [
        'Overview',
        'Risk Analyst',
        'Project Intelligence',
        'Historical Memory',
        'Methodology'
    ],
    horizontal=True,
    label_visibility='collapsed'
)


# =========================================================
# OVERVIEW
# =========================================================

if page == 'Overview':

    left, right = st.columns([1.55, 1])

    with left:

        st.subheader('Emerging-risk landscape')

        chart = (
            filtered['risk_level']
            .value_counts()
            .reindex(['HIGH', 'MEDIUM', 'LOW'])
            .fillna(0)
            .astype(int)
        )

        st.bar_chart(chart)

        st.caption(
            'Attention levels are based on cost escalation, '
            'schedule revision and expenditure–progress divergence '
            'in the current snapshot.'
        )

    with right:

        st.subheader('Highest attention')

        cols = [
            'code',
            'name',
            'risk_score',
            'risk_level',
            'cost_escalation_pct',
            'schedule_delay_months'
        ]

        top = (
            filtered
            .sort_values(
                'risk_score',
                ascending=False
            )[cols]
            .head(8)
            .copy()
        )

        top['risk_score'] = (
            top['risk_score']
            .round(1)
        )

        top['cost_escalation_pct'] = (
            top['cost_escalation_pct']
            .round(1)
        )

        top['schedule_delay_months'] = (
            top['schedule_delay_months']
            .round(1)
        )

        st.dataframe(
            top,
            use_container_width=True,
            hide_index=True
        )


# =========================================================
# RISK ANALYST — AGGREGATE MONTHLY TRENDS
# =========================================================

elif page == 'Risk Analyst':

    st.subheader('Portfolio Risk Analyst')
    st.caption('June–August 2026 aggregate trend analysis from the supplied monthly PAIMANA reports.')

    if len(monthly) != 3:
        st.warning('One or more monthly reports are missing. Add the June, July and August report files beside app.py to enable this view.')
    else:
        ordered = monthly.set_index('Month').reindex(['June', 'July', 'August']).reset_index()
        latest = ordered.iloc[-1]
        previous = ordered.iloc[-2]

        st.info('This analysis compares portfolio-level monthly aggregates. The project-level workbook is a single snapshot, so these trends are not individual-project trajectories or trained predictions.')

        m1, m2, m3, m4 = st.columns(4)
        m1.metric('August project count', f"{int(monthly_sectors['August']['project_count'].sum()):,}", help='Sum of sector-wise project counts in the August report.')
        m2.metric('August revised cost', f"₹{latest['Revised Cost (₹ cr)']:,.0f} cr", f"{latest['Revised Cost (₹ cr)']-previous['Revised Cost (₹ cr)']:+,.0f} cr vs July")
        m3.metric('August expenditure', f"₹{latest['Expenditure (₹ cr)']:,.0f} cr", f"{latest['Expenditure (₹ cr)']-previous['Expenditure (₹ cr)']:+,.0f} cr vs July")
        m4.metric('August cost escalation', f"{(latest['Revised Cost (₹ cr)']/latest['Original Cost (₹ cr)']-1)*100:.1f}%", help='Revised cost compared with original approved cost in the monthly aggregate report.')

        st.markdown('### Portfolio trend')
        trend_metric = st.selectbox('Metric to compare', ['Original Cost (₹ cr)', 'Revised Cost (₹ cr)', 'Expenditure (₹ cr)'])
        trend = ordered.set_index('Month')[[trend_metric]]
        st.line_chart(trend, use_container_width=True)
        st.dataframe(ordered.rename(columns={
            'Original Cost (₹ cr)': 'Original cost (₹ cr)',
            'Revised Cost (₹ cr)': 'Revised cost (₹ cr)',
            'Expenditure (₹ cr)': 'Expenditure (₹ cr)'
        }).round(2), use_container_width=True, hide_index=True)

        st.markdown('### Sector movement')
        all_sectors = sorted(set().union(*[set(x['sector'].dropna()) for x in monthly_sectors.values()]))
        selected_sector = st.selectbox('Select sector', all_sectors)
        sector_rows = []
        for month in ['June', 'July', 'August']:
            part = monthly_sectors[month]
            match = part[part['sector'] == selected_sector]
            if len(match):
                r = match.iloc[0]
                sector_rows.append({'Month': month, 'Projects': r['project_count'], 'Original cost (₹ cr)': r['original_cost'], 'Revised cost (₹ cr)': r['revised_cost'], 'Expenditure (₹ cr)': r['expenditure']})
            else:
                sector_rows.append({'Month': month, 'Projects': 0, 'Original cost (₹ cr)': np.nan, 'Revised cost (₹ cr)': np.nan, 'Expenditure (₹ cr)': np.nan})
        sector_trend = pd.DataFrame(sector_rows).set_index('Month')
        sc1, sc2 = st.columns(2)
        with sc1:
            st.caption('Project count by month')
            st.bar_chart(sector_trend[['Projects']])
        with sc2:
            st.caption('Revised cost by month (₹ crore)')
            st.line_chart(sector_trend[['Revised cost (₹ cr)']])
        st.dataframe(sector_trend.reset_index().round(2), use_container_width=True, hide_index=True)

        st.markdown('### State movement')
        all_states = sorted(set().union(*[set(x['state'].dropna()) for x in monthly_states.values()]))
        if all_states:
            selected_state = st.selectbox('Select state / UT', all_states)
            state_rows = []
            for month in ['June', 'July', 'August']:
                part = monthly_states[month]
                match = part[part['state'] == selected_state]
                if len(match):
                    r = match.iloc[0]
                    state_rows.append({
                        'Month': month,
                        'Projects': r['project_count'],
                        'Original cost (₹ cr)': r['original_cost'],
                        'Revised cost (₹ cr)': r['revised_cost'],
                        'Expenditure (₹ cr)': r['expenditure']
                    })
                else:
                    state_rows.append({
                        'Month': month, 'Projects': 0,
                        'Original cost (₹ cr)': np.nan,
                        'Revised cost (₹ cr)': np.nan,
                        'Expenditure (₹ cr)': np.nan
                    })
            state_trend = pd.DataFrame(state_rows).set_index('Month')
            st.line_chart(state_trend[['Revised cost (₹ cr)']], use_container_width=True)
            st.dataframe(state_trend.reset_index().round(2), use_container_width=True, hide_index=True)
        else:
            st.caption('No state-wise data is available in the supplied reports.')

        st.markdown('### Physical-progress distribution')
        bands = list(dict.fromkeys(monthly_progress['August']['progress_band'].tolist()))
        progress_rows = []
        for band in bands:
            row = {'Progress band': band}
            for month in ['June', 'July', 'August']:
                part = monthly_progress[month]
                match = part[part['progress_band'] == band]
                row[month] = int(match['project_count'].iloc[0]) if len(match) and pd.notna(match['project_count'].iloc[0]) else 0
            progress_rows.append(row)
        progress_compare = pd.DataFrame(progress_rows).set_index('Progress band')
        st.bar_chart(progress_compare[['June', 'July', 'August']], use_container_width=True)
        st.dataframe(progress_compare.reset_index(), use_container_width=True, hide_index=True)

        st.markdown('### Interpretation')
        revised_change = latest['Revised Cost (₹ cr)'] - previous['Revised Cost (₹ cr)']
        expenditure_change = latest['Expenditure (₹ cr)'] - previous['Expenditure (₹ cr)']
        st.write(f"From July to August, reported revised cost changed by ₹{revised_change:,.0f} crore and cumulative expenditure changed by ₹{expenditure_change:,.0f} crore.")
        st.caption('These are changes in reported portfolio totals. They can reflect project additions/removals, revisions, reporting updates or expenditure; they should not be interpreted as a causal explanation or a forecast.')


# =========================================================
# PROJECT INTELLIGENCE
# =========================================================

elif page == 'Project Intelligence':

    st.subheader('Project Intelligence')

    choices = (
        filtered
        .sort_values(
            'risk_score',
            ascending=False
        )
    )

    if len(choices) == 0:

        st.warning(
            'No projects match the current filters.'
        )

    else:

        selected_code = st.selectbox(
            'Select project',
            choices['code'].tolist(),
            format_func=lambda x:
                f"{x} — "
                f"{choices.loc[choices.code == x, 'name'].iloc[0][:85]}"
        )

        p = df[
            df.code == selected_code
        ].iloc[0]

        st.markdown(
            f'### {p["name"]}'
        )

        st.caption(
            f'Project code {p.code} · '
            f'{p.sector} · '
            f'{p.ministry}'
        )

        a, b, c, d = st.columns(4)

        a.metric(
            'Physical progress',
            f'{p.progress:.0f}%'
        )

        b.metric(
            'Cost escalation',
            f'{p.cost_escalation_pct:+.1f}%'
        )

        c.metric(
            'Expenditure / revised cost',
            f'{p.expenditure_share_pct:.1f}%'
        )

        d.metric(
            'Schedule revision',
            f'{p.schedule_delay_months:+.1f} mo'
        )

        # -------------------------------------------------
        # NEW ATTENTION UI
        # -------------------------------------------------

        st.markdown(
            '#### PRAGATI attention signal'
        )

        level = str(p.risk_level)

        if level == 'HIGH':
            badge_text = '🔴 HIGH ATTENTION'
        elif level == 'MEDIUM':
            badge_text = '🟠 MEDIUM ATTENTION'
        else:
            badge_text = '🟢 LOW ATTENTION'

        left_attention, right_attention = st.columns(
            [1.4, 1]
        )

        with left_attention:

            st.markdown(
                f'''
                <div class="attention-card">
                    <div class="attention-label">
                        CURRENT ATTENTION LEVEL
                    </div>
                    <div class="attention-badge">
                        {badge_text}
                    </div>
                    <div class="attention-description">
                        Based on the current project snapshot
                        and prototype screening indicators.
                    </div>
                </div>
                ''',
                unsafe_allow_html=True
            )

        with right_attention:

            st.metric(
                'Attention score',
                f'{p.risk_score:.1f} / 100',
                help=(
                    'This is a prototype attention score, '
                    'NOT a probability of project failure.'
                )
            )

        st.progress(
            int(
                round(
                    max(
                        0,
                        min(
                            100,
                            float(p.risk_score)
                        )
                    )
                )
            ),
            text=(
                f'Prototype attention score: '
                f'{p.risk_score:.1f}/100'
            )
        )

        st.caption(
            '⚠️ This is an attention score, not a probability '
            'of project failure. A trained and calibrated ML model '
            'using longitudinal project data would generate the '
            'final predictive risk probability.'
        )

        # -------------------------------------------------
        # WHY IS THIS PROJECT RECEIVING ATTENTION?
        # -------------------------------------------------

        st.markdown(
            '#### Why is this project receiving attention?'
        )

        cost_contribution = min(
            max(
                (float(p.cost_escalation_pct) / 100) * 40
                if pd.notna(p.cost_escalation_pct)
                else 0,
                0
            ),
            40
        )

        schedule_contribution = min(
            max(
                (float(p.schedule_delay_months) / 60) * 35
                if pd.notna(p.schedule_delay_months)
                else 0,
                0
            ),
            35
        )

        gap_contribution = min(
            max(
                (float(p.progress_gap_pct) / 50) * 25
                if pd.notna(p.progress_gap_pct)
                else 0,
                0
            ),
            25
        )

        contribution_data = pd.DataFrame({
            'Indicator': [
                'Cost escalation',
                'Schedule revision',
                'Progress–expenditure divergence'
            ],
            'Attention contribution': [
                cost_contribution,
                schedule_contribution,
                gap_contribution
            ]
        })

        contribution_data[
            'Attention contribution'
        ] = contribution_data[
            'Attention contribution'
        ].round(1)

        st.dataframe(
            contribution_data,
            use_container_width=True,
            hide_index=True
        )

        reasons = []

        if (
            pd.notna(p.cost_escalation_pct)
            and p.cost_escalation_pct > 10
        ):
            reasons.append(
                f'Cost escalation is '
                f'{p.cost_escalation_pct:.1f}% '
                f'above the original approved cost.'
            )

        if (
            pd.notna(p.schedule_delay_months)
            and p.schedule_delay_months > 3
        ):
            reasons.append(
                f'Revised commissioning is '
                f'{p.schedule_delay_months:.1f} months '
                f'after the original date.'
            )

        if (
            pd.notna(p.progress_gap_pct)
            and p.progress_gap_pct > 10
        ):
            reasons.append(
                f'Expenditure share '
                f'({p.expenditure_share_pct:.1f}%) '
                f'is ahead of physical progress '
                f'({p.progress:.1f}%) by '
                f'{p.progress_gap_pct:.1f} '
                f'percentage points.'
            )

        if not reasons:
            reasons.append(
                'No strong attention signal is triggered '
                'by the current prototype rules.'
            )

        for r in reasons:
            st.write('• ' + r)

        st.caption(
            'These indicators describe why the prototype '
            'assigns attention; they are not causal findings. '
            'The final system would replace this transparent '
            'screening score with trained longitudinal ML models '
            'and calibrated risk estimates.'
        )

        # -------------------------------------------------
        # PROJECT FACTS
        # -------------------------------------------------

        st.markdown(
            '#### Project facts'
        )

        facts = pd.DataFrame({
            'Metric': [
                'Original cost',
                'Revised cost',
                'Expenditure',
                'Original commissioning',
                'Revised commissioning',
                'Implementing agency'
            ],

            'Value': [
                f'₹{p.original_cost:,.2f} cr',
                f'₹{p.revised_cost:,.2f} cr',
                f'₹{p.expenditure:,.2f} cr',

                (
                    p.original_date.strftime('%d %b %Y')
                    if pd.notna(p.original_date)
                    else '—'
                ),

                (
                    p.revised_date.strftime('%d %b %Y')
                    if pd.notna(p.revised_date)
                    else '—'
                ),

                p.agency
            ]
        })

        st.dataframe(
            facts,
            use_container_width=True,
            hide_index=True
        )


# =========================================================
# HISTORICAL MEMORY
# =========================================================

elif page == 'Historical Memory':

    st.subheader(
        'Historical Institutional Memory'
    )

    st.caption(
        'Prototype analogue engine: finds projects with similar '
        'sector, progress, cost scale and expenditure share. '
        'Similarity is contextual, not proof of a common outcome.'
    )

    historical_choices = (
        filtered
        .sort_values(
            'risk_score',
            ascending=False
        )
    )

    if len(historical_choices) == 0:

        st.warning(
            'No projects match the current filters. '
            'Adjust the sidebar filters to use Historical Memory.'
        )

    else:

        selected_code = st.selectbox(
            'Project to compare',
            historical_choices['code'].tolist(),
            key='hist'
        )

        p = df[
            df.code == selected_code
        ].iloc[0]

        cand = df[
            df['code'] != selected_code
        ].copy()

        sector_projects = cand[
            cand['sector'] == p['sector']
        ].copy()

        if len(sector_projects) >= 5:
            cand = sector_projects

        features = [
            'progress',
            'original_cost',
            'expenditure_share_pct',
            'cost_escalation_pct'
        ]

        base = (
            df[features]
            .apply(
                pd.to_numeric,
                errors='coerce'
            )
            .astype('float64')
        )

        candidate_features = (
            cand[features]
            .apply(
                pd.to_numeric,
                errors='coerce'
            )
            .astype('float64')
        )

        target_features = (
            pd.to_numeric(
                p[features],
                errors='coerce'
            )
            .astype('float64')
        )

        med = (
            base
            .median()
            .astype('float64')
        )

        mad = (
            (base - med)
            .abs()
            .median()
            .astype('float64')
        )

        mad = mad.replace(
            0,
            1.0
        )

        candidate_values = (
            candidate_features
            .to_numpy(
                dtype=np.float64
            )
        )

        target_values = (
            target_features
            .to_numpy(
                dtype=np.float64
            )
        )

        med_values = (
            med
            .to_numpy(
                dtype=np.float64
            )
        )

        mad_values = (
            mad
            .to_numpy(
                dtype=np.float64
            )
        )

        z = (
            (
                candidate_values -
                target_values
            )
            / mad_values
        )

        z = np.nan_to_num(
            z,
            nan=0.0,
            posinf=0.0,
            neginf=0.0
        )

        distances = np.sqrt(
            np.sum(
                np.square(z),
                axis=1
            )
        )

        cand['similarity_distance'] = distances

        analogues = (
            cand
            .sort_values(
                'similarity_distance'
            )
            .head(5)
            .copy()
        )

        show = analogues[
            [
                'code',
                'name',
                'sector',
                'progress',
                'cost_escalation_pct',
                'expenditure_share_pct',
                'risk_level'
            ]
        ].copy()

        show['progress'] = (
            show['progress']
            .round(1)
        )

        show['cost_escalation_pct'] = (
            show['cost_escalation_pct']
            .round(1)
        )

        show['expenditure_share_pct'] = (
            show['expenditure_share_pct']
            .round(1)
        )

        show.columns = [
            'Project Code',
            'Project Name',
            'Sector',
            'Progress %',
            'Cost Escalation %',
            'Expenditure / Revised Cost %',
            'Attention'
        ]

        st.dataframe(
            show,
            use_container_width=True,
            hide_index=True
        )


# =========================================================
# METHODOLOGY
# =========================================================

elif page == 'Methodology':

    st.subheader(
        'How the prototype works'
    )

    st.markdown(
        '''
**Current snapshot layer**

PAIMANA project-level fields → validation → derived indicators → transparent attention score → explanation → historical analogues.

**Monthly Risk Analyst**

June, July and August aggregate reports → portfolio cost/expenditure trends, sector movement and physical-progress distribution. These aggregates do not create individual-project monthly histories.

**Derived indicators**

- Cost escalation = (Revised Cost / Original Cost − 1) × 100
- Expenditure share = Expenditure / Revised Cost × 100
- Progress–expenditure gap = Expenditure share − Physical progress
- Schedule revision = Revised commissioning date − Original commissioning date

**Prototype attention score**

40% cost escalation + 35% schedule revision + 25% positive progress–expenditure gap, with robust caps to reduce outlier domination.

**What is deliberately NOT claimed**

This snapshot alone cannot establish future-overrun prediction accuracy. Longitudinal prediction requires multiple reporting periods and a future outcome definition, followed by time-based train/validation/test evaluation.
'''
    )


st.divider()

st.caption(
    'PRAGATI prototype · Built using PAIMANA data from August,july and june 2026 '
    'project report · For demonstration and decision-support '
    'concept validation'
)

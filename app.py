import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path

st.set_page_config(
    page_title='PRAGATI | Infrastructure Project Monitoring',
    page_icon='🇮🇳',
    layout='wide',
    initial_sidebar_state='expanded'
)

DATA_FILE = Path(__file__).parent / 'Projects_Report.xlsx'


# =========================================================
# DATA
# =========================================================

@st.cache_data
def load_data():

    df = pd.read_excel(
        DATA_FILE,
        skiprows=2
    )

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

    # -----------------------------------------------------
    # Cost escalation
    # -----------------------------------------------------

    df['cost_escalation_pct'] = np.where(
        (df['original_cost'] > 0) &
        (df['revised_cost'] > 0),
        (
            df['revised_cost'] /
            df['original_cost'] - 1
        ) * 100,
        np.nan
    )

    # -----------------------------------------------------
    # Expenditure share
    # -----------------------------------------------------

    df['expenditure_share_pct'] = np.where(
        df['revised_cost'] > 0,
        (
            df['expenditure'] /
            df['revised_cost']
        ) * 100,
        np.nan
    )

    # -----------------------------------------------------
    # Progress / expenditure divergence
    # -----------------------------------------------------

    df['progress_gap_pct'] = (
        df['expenditure_share_pct'] -
        df['progress']
    )

    # -----------------------------------------------------
    # Schedule revision
    # -----------------------------------------------------

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


# =========================================================
# PROTOTYPE ATTENTION SCORE
# =========================================================

def add_risk_score(d):

    x = d.copy()

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

    # Invalid indicators are unavailable,
    # not zero-risk observations.
    cost = cost.where(cost >= 0)
    delay = delay.where(delay >= 0)
    gap = gap.where(gap >= 0)

    cost = cost.clip(
        lower=0,
        upper=100
    )

    delay = delay.clip(
        lower=0,
        upper=60
    )

    gap = gap.clip(
        lower=0,
        upper=50
    )

    cost_s = cost
    delay_s = (delay / 60) * 100
    gap_s = (gap / 50) * 100

    weights = pd.DataFrame({
        'cost': 0.40,
        'delay': 0.35,
        'gap': 0.25
    }, index=x.index)

    valid = pd.DataFrame({
        'cost': cost.notna(),
        'delay': delay.notna(),
        'gap': gap.notna()
    }, index=x.index)

    weighted = pd.DataFrame({
        'cost': cost_s * weights['cost'],
        'delay': delay_s * weights['delay'],
        'gap': gap_s * weights['gap']
    }, index=x.index)

    weighted = weighted.where(
        valid,
        0
    )

    available_weight = (
        weights
        .where(valid, 0)
        .sum(axis=1)
    )

    total_score = weighted.sum(
        axis=1
    )

    x['risk_score'] = np.where(
        available_weight > 0,
        (
            total_score /
            available_weight
        ).clip(0, 100),
        np.nan
    )

    x['risk_score'] = (
        x['risk_score']
        .astype(float)
    )

    x['risk_level'] = pd.cut(
        x['risk_score'],
        bins=[
            -0.01,
            30,
            60,
            100
        ],
        labels=[
            'LOW',
            'MEDIUM',
            'HIGH'
        ]
    )

    return x


df = add_risk_score(df)


# =========================================================
# FORMATTING HELPERS
# =========================================================

def fmt_pct(value, decimals=1):

    if pd.isna(value):
        return 'Not available'

    return f'{value:+.{decimals}f}%'


def fmt_num(value, decimals=1):

    if pd.isna(value):
        return 'Not available'

    return f'{value:.{decimals}f}'


def fmt_currency(value):

    if pd.isna(value):
        return 'Not available'

    return f'₹{value:,.2f} crore'


# =========================================================
# GOVERNMENT-STYLE DESIGN
# =========================================================

st.markdown(
    '''
    <style>

    /* -------------------------------------------------
       GLOBAL
    ------------------------------------------------- */

    .stApp {
        background: #f5f6f8;
        color: #17202a;
        font-family:
            "Noto Sans",
            "Segoe UI",
            Arial,
            sans-serif;
    }

    .block-container {
        max-width: 1500px;
        padding-top: 0.8rem;
        padding-bottom: 2rem;
    }

    h1, h2, h3, h4 {
        color: #17202a !important;
        font-weight: 650 !important;
    }

    h3 {
        margin-top: 1rem !important;
    }

    /* -------------------------------------------------
       TRICOLOUR GOVERNMENT BAR
    ------------------------------------------------- */

    .tricolour-bar {
        height: 6px;
        width: 100%;
        margin-bottom: 0.9rem;
        background:
            linear-gradient(
                to right,
                #ff9933 0%,
                #ff9933 33.33%,
                #ffffff 33.33%,
                #ffffff 66.66%,
                #138808 66.66%,
                #138808 100%
            );
        border: 1px solid #d8d8d8;
    }

    /* -------------------------------------------------
       GOVERNMENT HEADER
    ------------------------------------------------- */

    .gov-header {
        background: #ffffff;
        border: 1px solid #d9dee5;
        border-top: 4px solid #1b3a63;
        padding: 0.9rem 1.15rem;
        margin-bottom: 0;
    }

    .gov-title {
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0.035em;
        color: #26384d;
        text-transform: uppercase;
    }

    .gov-ministry {
        font-size: 1.05rem;
        font-weight: 700;
        color: #17202a;
        margin-top: 0.18rem;
    }

    .gov-division {
        font-size: 0.83rem;
        color: #586777;
        margin-top: 0.12rem;
    }

    /* -------------------------------------------------
       PRAGATI BRAND PANEL
    ------------------------------------------------- */

    .brand-panel {
        background: #ffffff;
        border-left: 5px solid #1b3a63;
        border-right: 1px solid #d9dee5;
        border-bottom: 1px solid #d9dee5;
        padding: 1rem 1.15rem;
        margin-bottom: 0.8rem;
    }

    .brand-name {
        font-size: 1.85rem;
        font-weight: 800;
        letter-spacing: 0.04em;
        color: #17395f;
    }

    .brand-full {
        font-size: 0.82rem;
        color: #526273;
        margin-top: 0.1rem;
    }

    .prototype-tag {
        display: inline-block;
        margin-top: 0.55rem;
        padding: 0.22rem 0.55rem;
        border: 1px solid #b7c3d1;
        background: #f2f5f8;
        color: #435466;
        font-size: 0.69rem;
        font-weight: 700;
        letter-spacing: 0.045em;
        text-transform: uppercase;
    }

    /* -------------------------------------------------
       NAVIGATION
    ------------------------------------------------- */

    div[role="radiogroup"] {
        background: #17395f;
        padding: 0.15rem 0.35rem;
        border: 1px solid #17395f;
    }

    div[role="radiogroup"] label {
        color: #ffffff !important;
        font-size: 0.82rem !important;
        font-weight: 600 !important;
    }

    div[role="radiogroup"] label:hover {
        background: #234c78;
    }

    /* -------------------------------------------------
       SIDEBAR
    ------------------------------------------------- */

    section[data-testid="stSidebar"] {
        background: #eef1f5;
        border-right: 1px solid #d2d8df;
    }

    section[data-testid="stSidebar"] h2 {
        color: #17395f !important;
        font-size: 1rem !important;
    }

    /* -------------------------------------------------
       INFORMATION BANNER
    ------------------------------------------------- */

    .system-note {
        background: #f7f9fb;
        border: 1px solid #ccd5df;
        border-left: 4px solid #17395f;
        padding: 0.7rem 0.9rem;
        margin: 0.8rem 0 1rem 0;
        font-size: 0.78rem;
        color: #4c5d6e;
    }

    /* -------------------------------------------------
       SECTION HEADERS
    ------------------------------------------------- */

    .section-heading {
        border-left: 4px solid #ff9933;
        padding-left: 0.65rem;
        margin-top: 1.2rem;
        margin-bottom: 0.8rem;
        color: #17395f;
        font-size: 1.05rem;
        font-weight: 700;
    }

    /* -------------------------------------------------
       METRIC PANELS
    ------------------------------------------------- */

    div[data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #d8dee6;
        border-radius: 2px;
        padding: 0.7rem 0.85rem;
        min-height: 92px;
    }

    div[data-testid="stMetricLabel"] {
        color: #5c6c7c !important;
        font-size: 0.74rem !important;
        font-weight: 600 !important;
    }

    div[data-testid="stMetricValue"] {
        color: #17395f !important;
        font-size: 1.45rem !important;
        font-weight: 700 !important;
    }

    /* -------------------------------------------------
       TABLES
    ------------------------------------------------- */

    [data-testid="stDataFrame"] {
        border: 1px solid #d5dbe2;
    }

    /* -------------------------------------------------
       ATTENTION PANEL
    ------------------------------------------------- */

    .attention-panel {
        background: #ffffff;
        border: 1px solid #d4dbe3;
        border-left: 5px solid #17395f;
        padding: 1rem;
        min-height: 130px;
    }

    .attention-title {
        font-size: 0.7rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        color: #687787;
        text-transform: uppercase;
        margin-bottom: 0.45rem;
    }

    .attention-status {
        font-size: 1.1rem;
        font-weight: 800;
        color: #17395f;
        margin-bottom: 0.4rem;
    }

    .attention-description {
        color: #657484;
        font-size: 0.77rem;
    }

    .status-high {
        border-left-color: #b3261e;
    }

    .status-medium {
        border-left-color: #b26a00;
    }

    .status-low {
        border-left-color: #18794e;
    }

    /* -------------------------------------------------
       OFFICIAL NOTE
    ------------------------------------------------- */

    .official-note {
        background: #fafafa;
        border: 1px solid #d8dde3;
        padding: 0.7rem 0.85rem;
        font-size: 0.76rem;
        color: #596978;
    }

    /* -------------------------------------------------
       FOOTER
    ------------------------------------------------- */

    .footer {
        border-top: 1px solid #d4d9df;
        margin-top: 2rem;
        padding-top: 0.7rem;
        font-size: 0.7rem;
        color: #687786;
        text-align: center;
    }

    </style>
    ''',
    unsafe_allow_html=True
)


# =========================================================
# GOVERNMENT HEADER
# =========================================================

st.markdown(
    '<div class="tricolour-bar"></div>',
    unsafe_allow_html=True
)

st.markdown(
    '''
    <div class="gov-header">
        <div class="gov-title">
            Government of India
        </div>
        <div class="gov-ministry">
            Ministry of Statistics and Programme Implementation
        </div>
        <div class="gov-division">
            Infrastructure & Project Monitoring Division
        </div>
    </div>
    ''',
    unsafe_allow_html=True
)

st.markdown(
    '''
    <div class="brand-panel">
        <div class="brand-name">PRAGATI</div>
        <div class="brand-full">
            Predictive Risk Analytics for Government Infrastructure
            Tracking & Intelligence
        </div>
        <div class="prototype-tag">
            Prototype / Demonstration System
        </div>
    </div>
    ''',
    unsafe_allow_html=True
)

st.markdown(
    '''
    <div class="system-note">
        <strong>System status:</strong>
        Prototype monitoring layer using the supplied PAIMANA
        project-level snapshot. Current attention levels are based
        on transparent screening indicators and are not trained
        future-outcome predictions.
    </div>
    ''',
    unsafe_allow_html=True
)


# =========================================================
# SIDEBAR FILTERS
# =========================================================

st.sidebar.markdown(
    '## Monitoring Filters'
)

st.sidebar.caption(
    'Filter the project universe for the current analysis.'
)

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


# =========================================================
# SUMMARY
# =========================================================

st.markdown(
    '<div class="section-heading">Monitoring Summary</div>',
    unsafe_allow_html=True
)

c1, c2, c3, c4 = st.columns(4)

c1.metric(
    'Projects in current view',
    f'{len(filtered):,}'
)

c2.metric(
    'Original approved cost',
    f'₹{filtered.original_cost.sum()/1000:,.1f}k cr'
)

c3.metric(
    'Latest revised cost',
    f'₹{filtered.revised_cost.sum()/1000:,.1f}k cr'
)

c4.metric(
    'Projects requiring high attention',
    f'{(filtered.risk_level == "HIGH").sum():,}'
)


# =========================================================
# NAVIGATION
# =========================================================

page = st.radio(
    'PRAGATI modules',
    [
        'Overview',
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

    st.markdown(
        '<div class="section-heading">'
        'Infrastructure Project Monitoring Overview'
        '</div>',
        unsafe_allow_html=True
    )

    left, right = st.columns(
        [1.35, 1]
    )

    with left:

        st.markdown(
            '### Attention Distribution'
        )

        chart = (
            filtered['risk_level']
            .value_counts()
            .reindex(
                ['HIGH', 'MEDIUM', 'LOW']
            )
            .fillna(0)
            .astype(int)
        )

        st.bar_chart(chart)

        st.caption(
            'Prototype attention levels are derived from cost '
            'escalation, schedule revision and positive '
            'expenditure–progress divergence.'
        )

    with right:

        st.markdown(
            '### Projects Requiring Attention'
        )

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

        top.columns = [
            'Project Code',
            'Project',
            'Attention Score',
            'Level',
            'Cost Escalation %',
            'Schedule Revision (mo)'
        ]

        st.dataframe(
            top,
            use_container_width=True,
            hide_index=True
        )


# =========================================================
# PROJECT INTELLIGENCE
# =========================================================

elif page == 'Project Intelligence':

    st.markdown(
        '<div class="section-heading">'
        'Project Intelligence'
        '</div>',
        unsafe_allow_html=True
    )

    choices = (
        filtered
        .sort_values(
            'risk_score',
            ascending=False
        )
    )

    if len(choices) == 0:

        st.warning(
            'No projects match the selected monitoring filters.'
        )

    else:

        selected_code = st.selectbox(
            'Select Project',
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
            f'Project Code: {p.code}  |  '
            f'Sector: {p.sector}  |  '
            f'Ministry / Department: {p.ministry}'
        )

        a, b, c, d = st.columns(4)

        a.metric(
            'Physical Progress',
            (
                f'{p.progress:.0f}%'
                if pd.notna(p.progress)
                else 'Not available'
            )
        )

        b.metric(
            'Cost Escalation',
            fmt_pct(p.cost_escalation_pct)
        )

        c.metric(
            'Expenditure / Revised Cost',
            (
                f'{p.expenditure_share_pct:.1f}%'
                if pd.notna(p.expenditure_share_pct)
                else 'Not available'
            )
        )

        d.metric(
            'Schedule Revision',
            (
                f'{p.schedule_delay_months:+.1f} mo'
                if pd.notna(p.schedule_delay_months)
                else 'Not available'
            )
        )

        # -------------------------------------------------
        # ATTENTION
        # -------------------------------------------------

        st.markdown(
            '<div class="section-heading">'
            'PRAGATI Attention Assessment'
            '</div>',
            unsafe_allow_html=True
        )

        level = (
            str(p.risk_level)
            if pd.notna(p.risk_level)
            else 'UNAVAILABLE'
        )

        if level == 'HIGH':

            status_text = 'HIGH ATTENTION'
            status_class = 'status-high'

        elif level == 'MEDIUM':

            status_text = 'MEDIUM ATTENTION'
            status_class = 'status-medium'

        elif level == 'LOW':

            status_text = 'LOW ATTENTION'
            status_class = 'status-low'

        else:

            status_text = 'ASSESSMENT UNAVAILABLE'
            status_class = ''

        left_attention, right_attention = st.columns(
            [1.4, 1]
        )

        with left_attention:

            st.markdown(
                f'''
                <div class="attention-panel {status_class}">
                    <div class="attention-title">
                        Current Monitoring Status
                    </div>

                    <div class="attention-status">
                        {status_text}
                    </div>

                    <div class="attention-description">
                        Assessment based on the current project
                        snapshot and available prototype indicators.
                    </div>
                </div>
                ''',
                unsafe_allow_html=True
            )

        with right_attention:

            if pd.notna(p.risk_score):

                st.metric(
                    'Attention Score',
                    f'{p.risk_score:.1f} / 100',
                    help=(
                        'Prototype attention score. '
                        'It is not a probability of project failure.'
                    )
                )

            else:

                st.metric(
                    'Attention Score',
                    'Not available'
                )

        if pd.notna(p.risk_score):

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
                )
            )

        st.markdown(
            '''
            <div class="official-note">
                <strong>Interpretation:</strong>
                The attention score is a transparent prototype
                screening measure, not a probability of project
                failure. A trained and calibrated longitudinal
                ML model would be required for predictive risk
                probabilities.
            </div>
            ''',
            unsafe_allow_html=True
        )

        # -------------------------------------------------
        # CONTRIBUTING INDICATORS
        # -------------------------------------------------

        st.markdown(
            '<div class="section-heading">'
            'Contributing Monitoring Indicators'
            '</div>',
            unsafe_allow_html=True
        )

        cost_contribution = min(
            max(
                (
                    float(p.cost_escalation_pct) /
                    100
                ) * 40
                if pd.notna(p.cost_escalation_pct)
                else 0,
                0
            ),
            40
        )

        schedule_contribution = min(
            max(
                (
                    float(p.schedule_delay_months) /
                    60
                ) * 35
                if pd.notna(p.schedule_delay_months)
                else 0,
                0
            ),
            35
        )

        gap_contribution = min(
            max(
                (
                    float(p.progress_gap_pct) /
                    50
                ) * 25
                if pd.notna(p.progress_gap_pct)
                else 0,
                0
            ),
            25
        )

        contribution_data = pd.DataFrame({
            'Monitoring Indicator': [
                'Cost escalation',
                'Schedule revision',
                'Progress–expenditure divergence'
            ],
            'Attention Contribution': [
                cost_contribution,
                schedule_contribution,
                gap_contribution
            ]
        })

        contribution_data[
            'Attention Contribution'
        ] = (
            contribution_data[
                'Attention Contribution'
            ].round(1)
        )

        st.dataframe(
            contribution_data,
            use_container_width=True,
            hide_index=True
        )

        # -------------------------------------------------
        # REASONS
        # -------------------------------------------------

        st.markdown(
            '<div class="section-heading">'
            'Monitoring Observations'
            '</div>',
            unsafe_allow_html=True
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
                f'{p.progress_gap_pct:.1f} percentage points.'
            )

        if not reasons:

            reasons.append(
                'No strong attention signal is triggered '
                'by the current prototype rules.'
            )

        for r in reasons:
            st.write(
                '• ' + r
            )

        st.caption(
            'These indicators describe the basis of the prototype '
            'attention assessment. They are not causal findings.'
        )

        # -------------------------------------------------
        # PROJECT FACTS
        # -------------------------------------------------

        st.markdown(
            '<div class="section-heading">'
            'Project Information'
            '</div>',
            unsafe_allow_html=True
        )

        facts = pd.DataFrame({
            'Parameter': [
                'Original approved cost',
                'Latest revised cost',
                'Cumulative expenditure',
                'Original commissioning date',
                'Revised commissioning date',
                'Implementing agency'
            ],

            'Value': [
                fmt_currency(p.original_cost),
                fmt_currency(p.revised_cost),
                fmt_currency(p.expenditure),

                (
                    p.original_date.strftime('%d %b %Y')
                    if pd.notna(p.original_date)
                    else 'Not available'
                ),

                (
                    p.revised_date.strftime('%d %b %Y')
                    if pd.notna(p.revised_date)
                    else 'Not available'
                ),

                (
                    p.agency
                    if pd.notna(p.agency)
                    else 'Not available'
                )
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

    st.markdown(
        '<div class="section-heading">'
        'Historical Institutional Memory'
        '</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '''
        <div class="official-note">
            The prototype analogue engine identifies projects with
            similar sector, physical progress, cost scale and
            expenditure characteristics. Similarity is contextual
            and does not imply identical project outcomes.
        </div>
        ''',
        unsafe_allow_html=True
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
            'No projects match the selected filters.'
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

        cand[
            'similarity_distance'
        ] = distances

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

        st.markdown(
            '### Comparable Projects'
        )

        st.dataframe(
            show,
            use_container_width=True,
            hide_index=True
        )


# =========================================================
# METHODOLOGY
# =========================================================

elif page == 'Methodology':

    st.markdown(
        '<div class="section-heading">'
        'Methodology & System Limitations'
        '</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '''
### 1. Current Data Layer

PAIMANA project-level fields are processed through
validation and derived-indicator generation.

### 2. Derived Monitoring Indicators

**Cost escalation**

(Revised Cost / Original Cost − 1) × 100

**Expenditure share**

Expenditure / Revised Cost × 100

**Progress–expenditure divergence**

Expenditure share − Physical progress

**Schedule revision**

Revised commissioning date − Original commissioning date

### 3. Prototype Attention Assessment

The current demonstration uses a transparent weighted
screening approach:

- 40% — cost escalation
- 35% — schedule revision
- 25% — positive progress–expenditure divergence

Indicators that are unavailable or invalid are excluded
and the remaining weights are renormalised.

### 4. Historical Institutional Memory

Projects are compared using contextual similarity across
selected project characteristics.

### 5. Future Predictive Layer

The intended production architecture can incorporate
longitudinal PAIMANA / OCMS observations to develop:

- Cost-overrun prediction
- Schedule-overrun prediction
- Implementation-risk prediction
- Calibrated early-warning probabilities
- Explainable model outputs

### 6. Current Limitation

The present dataset is a project-level snapshot.

Therefore, this prototype does **not** claim measured
future-outcome prediction accuracy.

Longitudinal observations are required for time-based
training, validation and testing.
'''
    )


# =========================================================
# FOOTER
# =========================================================

st.markdown(
    '''
    <div class="footer">
        PRAGATI Prototype · Infrastructure Project Monitoring
        Decision-Support Concept<br>
        Demonstration system using the supplied PAIMANA
        project-level report · Not an official Government of India application
    </div>
    ''',
    unsafe_allow_html=True
)

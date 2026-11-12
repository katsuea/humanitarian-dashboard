import re
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# =========================================================
# 1. Global settings
# =========================================================

DATA_DIR = Path(__file__).resolve().parent

YEARS = list(range(2016, 2026))
DEFAULT_YEAR = 2022

COLORS = {
    "title": "#2C3E50",

    # Neutral colors for donor rankings
    "rank1": "#334155",
    "rank2": "#64748B",
    "rank3": "#94A3B8",
    "rank4to8": "#CBD5E1",

    # Other general colors
    "other": "#8C8C8C",
    "white": "#FFFFFF",
    "background": "#FFFFFF",
    "text": "#2C3E50",
    "axis": "#999999",
    "funding_line": "#B45309",
    "selected_year": "#FF6F61",
}
    
# Ranking colors: based on annual ranking position
RANK_COLORS = {
    1: COLORS["rank1"],
    2: COLORS["rank2"],
    3: COLORS["rank3"],
}

# Donor identity colors: consistent throughout the dashboard
DONOR_COLORS = {
    "United States of America, Government of": "#081D58",
    "Germany, Government of": "#1E40AF",
    "European Commission": "#60A5FA",
}

# Three major donors to display in the total funding graph
MAJOR_DONORS = [
    "United States of America, Government of",
    "Germany, Government of",
    "European Commission"
]

# =========================================================
# 2. Helper functions
# =========================================================

def parse_funding(series):
    """Convert funding strings into numeric values."""

    cleaned = (
        series.astype(str)
        .str.replace(r"[$,\s]", "", regex=True)
        .str.replace(r"^\((.*)\)$", r"-\1", regex=True)
    )

    return pd.to_numeric(cleaned, errors="coerce")


def format_money(value):
    """Display funding in millions of US dollars."""

    return f"${value / 1_000_000:,.0f}M"

# =========================================================
# 3. Load total humanitarian funding data
# =========================================================

@st.cache_data
def load_total_funding():

    filename = DATA_DIR / "Total_funding.xlsx"

    df = pd.read_excel(
        filename,
        sheet_name=1,
        header=2
    )

    df.columns = df.columns.str.strip()

    df = df[
        ["Year", "Total funding (US$)"]
    ].copy()

    df = df.rename(
        columns={"Total funding (US$)": "Funding"}
    )

    df["Year"] = pd.to_numeric(
        df["Year"], errors="coerce"
    )

    df["Funding"] = pd.to_numeric(
        df["Funding"], errors="coerce"
    )

    df = df.dropna(
        subset=["Year", "Funding"]
    )

    df = df[
        df["Year"].between(2016, 2025)
    ].copy()

    df["Year"] = df["Year"].astype(int)

    return df.sort_values("Year")

# =========================================================
# 4. Load annual donor funding Excel files
# =========================================================

@st.cache_data
def load_all_years(data_dir):

    data_dir = Path(data_dir)

    yearly_data = {}

    if not data_dir.exists():
        raise FileNotFoundError(
            f"Data folder not found: {data_dir.resolve()}"
        )

    files = [
        file
        for file in data_dir.glob("*.xlsx")
        if not file.name.startswith("~$")
    ]

    for year in YEARS:

        matches = [
            file
            for file in files
            if re.search(
                rf"(?<!\d){year}(?!\d)",
                file.stem
            )
        ]

        if not matches:
            continue

        file_path = matches[0]

        df = pd.read_excel(
            file_path,
            sheet_name=1,
            header=2
        )

        required_columns = [
            "Donor",
            "Funding (US$)"
        ]

        missing_columns = [
            col
            for col in required_columns
            if col not in df.columns
        ]

        if missing_columns:
            continue

        donors = df["Donor"]

        funding = parse_funding(
            df["Funding (US$)"]
        )

        cleaned = pd.DataFrame({
            "Donor": donors,
            "Funding": funding
        })

        cleaned = cleaned.dropna(
            subset=["Donor", "Funding"]
        )

        cleaned["Donor"] = (
            cleaned["Donor"]
            .astype(str)
            .str.strip()
        )

        cleaned = cleaned[
            cleaned["Donor"].ne("")
            & cleaned["Donor"].str.lower().ne("nan")
        ]

        # Combine duplicate donor entries.

        cleaned = (
            cleaned.groupby(
                "Donor",
                as_index=False
            )["Funding"]
            .sum()
        )

        yearly_data[year] = cleaned

    if not yearly_data:
        raise ValueError(
            "No usable donor data found. "
            "Check the Excel files, worksheets, "
            "column headers, and funding values."
        )

    return yearly_data

# =========================================================
# 4B. Extract funding for three major donors
# =========================================================

def load_major_donors(yearly_data):

    data = []

    for year, df in yearly_data.items():

        for donor in MAJOR_DONORS:

            funding = df.loc[
                df["Donor"] == donor,
                "Funding"
            ].sum()

            data.append({
                "Year": year,
                "Donor": donor,
                "Funding": funding
            })

    return pd.DataFrame(data)

# =========================================================
# 5. LEFT GRAPH: Total humanitarian funding
# =========================================================

def show_total_funding(df, selected_year, major_donors_df):

    st.markdown(
        f"""
        <h2 style="
            color: {COLORS['title']};
            font-size: 1.5rem;
            font-weight: 600;
            margin-bottom: 0.3rem;
        ">
            Humanitarian Funding Trends
        </h2>
        """,
        unsafe_allow_html=True
    )

    st.caption(
        "Lines represent total funding and contributions "
        "from the USA, Germany, and the European Commission"
        "over the 10-year period."
    )

    fig = go.Figure()

    # 1. Funding line

    fig.add_trace(
        go.Scatter(
            x=df["Year"],
            y=df["Funding"],
            mode="lines+markers",
            name="Total funding",
            line=dict(
                color=COLORS["funding_line"],
                width=2.5
            ),
            marker=dict(
                size=7,
                color=COLORS["funding_line"]
            ),
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Total funding: $%{y:,.0f}"
                "<extra></extra>"
            )
        )
    )

    # 2. Three major donor lines

    for donor in MAJOR_DONORS:

        donor_data = major_donors_df[
            major_donors_df["Donor"] == donor
        ]

        donor_color = DONOR_COLORS[donor]

        fig.add_trace(
            go.Scatter(
                x=donor_data["Year"],
                y=donor_data["Funding"],
                mode="lines+markers",
                name=donor,
                line=dict(
                    color=donor_color,
                    width=2.5
                ),
                marker=dict(
                    size=7,
                    color=donor_color
                ),
                hovertemplate=(
                    "<b>%{x}</b><br>"
                    + donor
                    + ": $%{y:,.0f}"
                    + "<extra></extra>"
                )
            )
        )

    # 3. Selected year vertical line ###################################
    fig.add_vline(
        x=selected_year,
        line_width=3,
        line_dash="dash",
        line_color=COLORS["selected_year"]
    )

    # 3. Layout

    fig.update_layout(
        height=600,
        hovermode="x unified",
        xaxis=dict(
            title="Year",
            tickmode="linear",
            dtick=1,
            range=[2015.5, 2025.5]
        ),
        yaxis=dict(
            title="Funding (US$)",
            tickformat="$.3s",
            rangemode="tozero"
        ),
        showlegend=False,
        margin=dict(
            l=20,
            r=30,
            t=40,
            b=30
        )
    )

    # 4. Display graph

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    # 5. Annual funding data table

    with st.expander("View detailed annual funding figures"):

        display_df = df.copy()

        display_df["Funding (USD)"] = (
            display_df["Funding"].map(
                lambda value: f"${value:,.0f}"
            )
        )

        display_df = display_df[
            ["Year", "Funding (USD)"]
        ]

        st.dataframe(
            display_df,
            hide_index=True,
            use_container_width=True
        )

# =========================================================
# 6. RIGHT GRAPH: Global donor rankings
# =========================================================

def show_donor_ranking(yearly_data, selected_year):

    st.markdown(
        f"""
        <h2 style="
            color: {COLORS['title']};
            font-size: 1.5rem;
            font-weight: 600;
            margin-bottom: 0.3rem;
        ">
            Donor Rankings
        </h2>
        """,
        unsafe_allow_html=True
    )

    # Selected year's donor data ########################################
    year_df = yearly_data[selected_year]

    st.markdown(
        f"""
        <h3 style="
            color:{COLORS['title']};
            font-size: 1.35rem;
            font-weight: 600;
            margin-bottom: 0.5rem
        ">
            Top 8 Donors - {selected_year}
        </h3>
        """,
        unsafe_allow_html=True
    )

    top8 = (
        year_df.sort_values(
            "Funding",
            ascending=False
        )
        .head(8)
        .copy()
        .reset_index(drop=True)
    )

    if top8.empty:
        st.warning(
            f"No donor data available for {selected_year}."
        )
        return

    top8["Rank"] = range(1, len(top8) + 1)

    def bar_color(rank):

        if rank in RANK_COLORS:
            return RANK_COLORS[rank]
    
        return COLORS["rank4to8"]

    # Reverse rows so rank 1 appears at the top.
    plot_df = top8.iloc[::-1].copy()

    plot_df["Color"] = (
        plot_df["Rank"].apply(bar_color)
    )

    plot_df["Funding label"] = (
        plot_df["Funding"].apply(format_money)
    )

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=plot_df["Funding"],
            y=plot_df["Donor"],
            orientation="h",
            marker=dict(
                color=plot_df["Color"],
                line=dict(width=0)
            ),
            text=plot_df["Funding label"],
            textposition="outside",
            textfont=dict(
                color=COLORS["title"],
                size=13
            ),
            customdata=plot_df[
                ["Rank", "Funding"]
            ].to_numpy(),
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Rank: %{customdata[0]}<br>"
                "Funding: $%{customdata[1]:,.0f}"
                "<extra></extra>"
            )
        )
    )

    max_funding = top8["Funding"].max()

    fig.update_layout(
        template="plotly_white",
        height=600,
        margin=dict(
            l=10,
            r=40,
            t=5,
            b=25
        ),
        paper_bgcolor=COLORS["background"],
        plot_bgcolor=COLORS["background"],
        font=dict(
            family="Arial, sans-serif",
            color=COLORS["title"],
            size=10
        ),
        showlegend=False,
        bargap=0.42,

        xaxis=dict(
            title="Funding (US$)",
            range=[0, max_funding * 1.28],
            showgrid=False,
            showline=True,
            linecolor=COLORS["axis"],
            zeroline=False,
            tickformat="$.3s"
        ),

        yaxis=dict(
            title=None,
            showgrid=False,
            showline=True,
            linecolor=COLORS["axis"],
            tickfont=dict(
                size=10,
                color="#595959"
            ),
            automargin=True
        )
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
        config={
            "displayModeBar": False,
            "responsive": True
        }
    )


# =========================================================
# 7. FIXED TOP 3 DONOR CARDS
# =========================================================

def show_top3_cards(top3):

    st.markdown(
        f"""
        <div style="margin-top: 5px;">
            <h3 style="
                color:{COLORS['title']};
                font-size: 1.35rem;
                font-weight: 600;
                margin-bottom: 0.5rem;
            ">
                Top 3 Donors by Cumulative Funding (2016–2025)
            </h3>
        </div>
        """,
        unsafe_allow_html=True,
    )

    card_columns = st.columns(3)

    for rank, (_, row) in enumerate(top3.iterrows(), start=1):
        with card_columns[rank - 1]:

            # Use donor identity colors, not ranking colors.
            card_color = DONOR_COLORS.get(
                row["Donor"],
                COLORS["other"]
            )
            
            st.markdown(
                f"""
                <div style="background-color: {card_color};
                            color: white;
                            padding: 15px;
                            border-radius: 10px;
                            text-align: center;
                            height: 180px;
                            box-sizing: border-box;
                            display: flex;
                            flex-direction: column;
                            justify-content: center;
                            align-items: center;
                            overflow: hidden;">
                    <h3 style="color: white; font-size: 30px;">#{rank}</h3>
                    <p style="color: white;
                              font-size: 22px;
                              font-weight: bold;
                              line-height: 1.2;
                              margin: 5px 0;
                              overflow-wrap: anywhere;">
                        {row['Donor']}
                    </p>
                    <p style="color: white; font-size: 24px;">{format_money(row['Funding'])}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

# =========================================================
# 8. MAIN FUNDING DASHBOARD
# =========================================================

def show_funding():

    # -----------------------------------------
    # Load both datasets
    # -----------------------------------------

    try:

        yearly_data = load_all_years(
            str(DATA_DIR)
        )

        total_df = load_total_funding()

        major_donors_df = load_major_donors(yearly_data)

    except FileNotFoundError as exc:

        st.error(str(exc))
        return

    except (ValueError, KeyError, ImportError) as exc:

        st.error(
            f"Could not read the funding data: {exc}"
        )
        return

    if total_df.empty:

        st.error(
            "No total funding data could be loaded."
        )
        return

    # -----------------------------------------
    # Calculate fixed cumulative top 3
    # -----------------------------------------

    all_years = []

    for year, df in yearly_data.items():

        temp = df.copy()
        temp["Year"] = year
        all_years.append(temp)

    combined = pd.concat(
        all_years,
        ignore_index=True
    )

    fixed_ranking = (
        combined.groupby(
            "Donor",
            as_index=False
        )["Funding"]
        .sum()
        .sort_values(
            "Funding",
            ascending=False
        )
        .reset_index(drop=True)
    )

    top3 = fixed_ranking.head(3)

    # -----------------------------------------
    # Dashboard title
    # -----------------------------------------

    st.markdown(
        f"""
        <h2 style="
            color: {COLORS['title']};
            font-size: 1.5rem;
            font-weight: 700;
            margin-top: 0;
            margin-bottom: 0.3rem;
        ">
            Global Humanitarian Funding Overview
        </h2>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        "Explore total humanitarian funding trends and "
        "donor contributions across 2016–2025."
    )

    # -----------------------------------------
    # ONE SHARED YEAR SLIDER
    # -----------------------------------------

    available_years = sorted(
        yearly_data.keys()
    )

    # Create the slider ##################################################
    selected_year = st.select_slider(
        "Select year",
        options=available_years,
        value=(
            DEFAULT_YEAR
            if DEFAULT_YEAR in available_years
            else available_years[0]
        ),
        format_func=lambda year: str(year),
        key="funding_year_slider"
    )

    # -----------------------------------------
    # TWO-COLUMN GRAPH DASHBOARD
    # -----------------------------------------

    col1, col2 = st.columns(
        [1, 1],
        gap="small",
        vertical_alignment="top"
    )

    # LEFT GRAPH

    with col1:
        show_total_funding(
            total_df, 
            selected_year,
            major_donors_df
        )### Pass the selected year to the left graph ###

    # RIGHT GRAPH

    with col2:
        show_donor_ranking(yearly_data, selected_year)### Pass the same selected year to the right graph ###

    # -----------------------------------------
    # FIXED TOP 3 DONOR CARDS
    # -----------------------------------------

    show_top3_cards(top3)

    # # 6. Source note

    st.markdown(
        """
        <div style="
            font-size: 0.75rem;
            color: #808080;
            line-height: 1.4;
            margin-top: 15px;
        ">
            Data Source: OCHA Financial Tracking Service (FTS)<br>
            Currency: Funding values are expressed in nominal US dollars.<br>
            Data limitations: Historical figures may be revised as new funding information is reported.
        </div>
        """,
        unsafe_allow_html=True
    )

# =========================================================
# 9. Run independently for testing
# =========================================================

if __name__ == "__main__":

    st.set_page_config(layout="wide")

    show_funding()
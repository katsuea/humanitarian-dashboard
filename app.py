import streamlit as st
import plotly.express as px
import pandas as pd
import plotly.graph_objects as go
import re
from pathlib import Path

st.set_page_config(layout="wide")

# Main Dashboard Title
st.markdown(
    """
    <div style="margin-bottom: 1.5rem;">
        <h1 style="
            color: #2C3E50;
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 0.2rem;
        ">
            Global Humanitarian Dashboard
        </h1>
        <p style="
            color: #555555;
            font-size: 1rem;
            margin-top: 0;
        ">
            Monitoring global emergencies, humanitarian needs,
            and funding trends to support informed humanitarian action.
        </p>
    </div>
    """,
    unsafe_allow_html=True
)

#Map title
st.markdown(
    """
    <h2 style="
        color: #2C3E50;
        font-size: 1.8rem;
        font-weight: 700;
        margin-top: 0;
        margin-bottom: 0;
    ">
        Global Emergencies Map
    </h2>
    """,
    unsafe_allow_html=True
)

# Map color palette
DEFAULT_EMERGENCY_COLOR = "#F2B8BE"
SELECTED_COUNTRY_COLOR = "#FF3333"

# Dataset for emergency countries (Choropleth mapping)
countries_data = pd.DataFrame({
    "ISO_Code": [
        "AFG", "COD",
        "LBN", "NPL", "PSE",
        "BFA", "CMR", "TCD",
        "MLI", "NER", "NGA",
        "SDN", "SYR", "UKR",
        "VEN", "YEM",
    ],
    "Country_Name": [
        "Afghanistan", "DR Congo",
        "Lebanon", "Nepal", "Gaza Strip (occupied Palestinian territory)",
        "Burkina Faso", "Cameroon", "Chad",
        "Mali", "Niger", "Nigeria",
        "Sudan", "Syria", "Ukraine",
        "Venezuela", "Yemen",
    ],
    "Emergency": [
        "Afghanistan Crisis", "Ebola Outbreaks in DR Congo",
        "Lebanon Crisis", "Flash Floods in Nepal", "Gaza Crisis",
        "Sahel Crisis", "Sahel Crisis", "Sahel Crisis",
        "Sahel Crisis", "Sahel Crisis", "Sahel Crisis",
        "Sudan Crisis", "Syria Crisis", "Ukraine Crisis",
        "Venezuela Crisis", "Yemen Crisis",
    ],
    "Image": [
        "afghanistan.jpg", "dr_congo.jpg",
        "lebanon.jpg", "nepal.jpg", "gaza.jpg",
        "sahel.jpg", "sahel.jpg", "sahel.jpg",
        "sahel.jpg", "sahel.jpg", "sahel.jpg",
        "sudan.jpg", "syria.jpg", "ukraine.jpg",
        "venezuela.jpg", "yemen.jpg"
    ],
    "Text": [
        "afghanistan.txt", "dr_congo.txt",
        "lebanon.txt", "nepal.txt", "gaza.txt",
        "sahel.txt", "sahel.txt", "sahel.txt", 
        "sahel.txt", "sahel.txt", "sahel.txt",
        "sudan.txt", "syria.txt", "ukraine.txt",
        "venezuela.txt", "yemen.txt"
    ],
})

# Keep the selected country across reruns.
if "selected_iso3" not in st.session_state:
    st.session_state["selected_iso3"] = None

# Create "Map_Status" (new column) in the countries_data DataFrame, and
# assigns a status to each country based on its ISO code.

selected_iso3 = st.session_state["selected_iso3"]
## {"selected_iso3": "AFG", "country_dropdown": "Afghanistan", "country_map": "Choropleth selected Point(1,2)", ...}
## {"selected_iso3": "PSE", "country_dropdown": "Palestine Gaza", ...}

countries_data["Map_Status"] = countries_data["ISO_Code"].apply(
    lambda iso: (
        "Selected"
        if iso == selected_iso3
        else "Other emergency area"
    )
)

# Create the choropleth map and configure country highlighting
fig = px.choropleth(
    countries_data,
    locations="ISO_Code",
    locationmode="ISO-3",
    color="Map_Status",
    hover_name="Country_Name",
    hover_data={
        "ISO_Code": False,
        "Map_Status": False,
        "Emergency": True,
    },
    custom_data=["ISO_Code"],
    color_discrete_map={
        "Selected": SELECTED_COUNTRY_COLOR,
        "Other emergency area": DEFAULT_EMERGENCY_COLOR,
    },
    category_orders={
        "Map_Status": ["Other emergency area", "Selected"]
    },
)

# Add a visible marker for Gaza
fig.add_trace(
    go.Scattergeo(
        lon=[34.15],
        lat=[31.50],
        mode="markers",
        marker=dict(
        size=12 if selected_iso3 == "PSE" else 9,
        color=(
            SELECTED_COUNTRY_COLOR
            if selected_iso3 == "PSE"
            else DEFAULT_EMERGENCY_COLOR
        ),
        symbol="circle",
        line=dict(width=2, color="white"),
        ),
        name="Gaza (oPt)",
        customdata=[["PSE"]],
        hovertemplate=(
            "<b>Gaza Strip (occupied Palestinian territory)</b><br>"
            "Emergency: Gaza Crisis"
            "<extra></extra>"
        ),
        hoverlabel=dict(
            bgcolor="#444444",
            bordercolor="#FFFFFF",
            font=dict(
                color="#FFFFFF",
                size=13,
            ),
            align="left",
        ),        
    )
)

# Configure geospatial parameters
fig.update_geos(
    projection_type="equal earth",
    showcountries=True,
    countrycolor="#CCCCCC",
    showland=True,
    landcolor="#F5F5F5",
    showocean=True,
    oceancolor="#E0F2FE",
    resolution=50  # Enhances border precision
)

# UI polish and removing unnecessary side legends
fig.update_layout(
    showlegend=False,
    height=650,
    margin={"r":0,"t":20,"l":0,"b":0}
)
    
######## Dropdown ###########
# Add dropdown above the map with a deliberate display order
country_options = dict(
    zip(countries_data["Country_Name"], countries_data["ISO_Code"])
)
## {"Afghanistan": "AFG", ...}

# Define the order shown in the dropdown.
country_order = [
    "Lebanon",
    "Syria",
    "Yemen",
    "Gaza Strip (occupied Palestinian territory)",
    "Afghanistan",
    "Nepal",
    "DR Congo",
    "Sudan",
    "Mali",
    "Burkina Faso",
    "Cameroon",
    "Chad",
    "Niger",
    "Nigeria",
    "Ukraine",
    "Venezuela",    
]

# Update the dorpdown's state when the map is clicked
# Reverse lookup: ISO code -> country name

iso_to_country = {
    iso: country
    for country, iso in country_options.items()
}
## {"AFG: "Afghanistan", ...}

def sync_map_selection():
    """Synchronize map clicks with the dropdown before rerunning."""
    # Retrieve the current selection state of the map.
    chart_state = st.session_state["country_map"]
    # Get the list of selected points from the map.
    points = chart_state.selection.points

    # Stop if no points are selected.
    if not points:
        return
        
    # Select the last point in the selection list.
    point = points[-1]
    # Retrieve the custom data (ISO code) associated with the point.
    customdata = point.get("customdata") 
    #no ISO code has been identified yet.
    selected_iso3 = None

    if customdata is not None and len(customdata) > 0:
        selected_iso3 = (
            customdata[0]
            if isinstance(customdata[0], str)
            else customdata[0][0]
        )

    if selected_iso3 in iso_to_country:
        st.session_state["selected_iso3"] = selected_iso3

        # Update the dropdown widget state in the callback.
        st.session_state["country_dropdown"] = (
            iso_to_country[selected_iso3]
        )

# Connect the dropdown to the selected country 
def sync_country_selection():
    selected_country = st.session_state["country_dropdown"]

    st.session_state["selected_iso3"] = (
        country_options.get(selected_country)
        if selected_country
        else None
    )

# Display the label
st.markdown(
    '<p style="font-size: 22px; margin-bottom: 0;">'
    'Countries and regions in need of emergency assistance:</p>',
    unsafe_allow_html=True
)

# Display the instruction on the next line
st.markdown(
    '<p style="font-size: 18px; color: #2C3E50; font-weight: 600; margin-top: 10px; margin-bottom: 8px;">'
    'Click a highlighted country to view details, OR</p>',
    unsafe_allow_html=True
)

selected_iso3 = st.session_state["selected_iso3"]

# Set the initial dropdown value from the current selection.
default_country = iso_to_country.get(selected_iso3, "")

if "country_dropdown" not in st.session_state:
    st.session_state["country_dropdown"] = default_country

selected_country = st.selectbox(
    " ",
    options=[""] + country_order,
    format_func=lambda x: "Select from the list" if x == "" else x,
    key="country_dropdown",
    label_visibility="collapsed",
    on_change=sync_country_selection,
)

# Enable point selection by clicking.
fig.update_layout(
    clickmode="event+select",
    # uirevision="map",
    # map_uirevision="map",
)

# Display the map and retrieve its selection state.
event = st.plotly_chart(
    fig,
    key="country_map",
    width="stretch",
    theme=None,
    on_select=sync_map_selection,
    selection_mode="points",
    # config={"scrollZoom": False},
)

# ==========================================
# 2. Details appear below the map.
# ==========================================

selected_iso3 = st.session_state["selected_iso3"]

if selected_iso3 is not None:
    matches = countries_data.loc[
        countries_data["ISO_Code"] == selected_iso3
    ]

    if matches.empty:
        st.warning(f"No details found for {selected_iso3}.")
    else:
        country = matches.iloc[0]
        image_file = country["Image"]
        text_file = country["Text"]

        # Resolve paths relative to this Python app file.
        base_folder = Path(__file__).resolve().parent
        image_path = base_folder / "assets" / image_file
        text_path = base_folder / "assets" / text_file

        st.subheader(country["Country_Name"])

        image_col, text_col = st.columns(
            [1, 2],
            gap="large",
            vertical_alignment="top",
        )

        # First column - Image
        with image_col:
            # Display the image.
            if image_path.is_file():
                st.image(
                    str(image_path),
                    width="stretch",
                )
                st.markdown(
                    f"**{country['Emergency']}**"
                )
            else:
                st.warning(f"Image not found: {image_file}")


        # Second column - Text
        with text_col:
            # Read and display the text.
            try:
                content = text_path.read_text(encoding="utf-8")
                st.markdown(content)
            except FileNotFoundError:
                st.warning(f"Text file not found: {text_file}")
            except (OSError, UnicodeError) as error:
                st.warning(f"Could not read {text_file}: {error}")

            # # Donation button for the selected emergency
            # st.link_button(
            #     "Donate now",
            #     country["Donation_URL"],
            #     type="primary",
            #     width=160,
            # )


# ==========================================
# 3. Global Funding Overview
# ==========================================
st.divider()

from funding import show_funding

show_funding()



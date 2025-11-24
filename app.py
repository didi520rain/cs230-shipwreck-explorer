"""
Name: Mandy Li
CS230: Section 08
Data:Shipwreck Database
URL:  (add Streamlit Cloud link here if you publish)

Description:
This program is an interactive data explorer for shipwrecks.
The user can:
- Filter by year range
- Filter by vessel type
- Filter by minimum lives lost
- See a map of wreck locations
- See a bar chart of wrecks by vessel type
- See a line chart of wrecks per year
- See the deadliest wrecks in a table

References:
Shipwreck CSV provided by the course.
https://docs.python.org/3/library/math.html
https://docs.streamlit.io/get-started/fundamentals/main-concepts
"""

#1. IMPORT LIBRARIES

import math                          # for simple decade/century math
import pandas as pd                  # for data handling
import numpy as np                   # for numeric helpers
import streamlit as st               # for the web app
import pydeck as pdk                 # for the map
import plotly.express as px          # for charts


#2. LOAD AND CLEAN DATA
@st.cache_data
def load_data():
    """
    Read the CSV and do basic cleaning.

    st.cache_data tells Streamlit to remember the result,
    so it doesn't re-load the file every time.
    """
    df = pd.read_csv("ShipwreckDatabase.csv")

    # Convert some columns to numbers (in case they are stored as text) #Chapter 11
    df["YEAR"] = pd.to_numeric(df["YEAR"], errors="coerce")
    df["LIVES LOST"] = pd.to_numeric(df["LIVES LOST"], errors="coerce")
    df["LATITUDE"] = pd.to_numeric(df["LATITUDE"], errors="coerce")
    df["LONGITUDE"] = pd.to_numeric(df["LONGITUDE"], errors="coerce")


    #[COLUMNS] We ADD a new helper column for lives lost with missing values filled.
    #Make a new column called LIVES_LOST_CLEAN where missing lives-lost values are treated
    #as 0 and everything is stored as whole numbers.
    df["LIVES_LOST_CLEAN"] = df["LIVES LOST"].fillna(0).astype(int)

    #[LAMBDA] We use lambda functions to make new DECADE and CENTURY columns.
    df["DECADE"] = df["YEAR"].apply(
        lambda y: int(y // 10 * 10) if pd.notna(y) else np.nan
    ) #For each value in the year column, if it’s not missing, cut it down to the nearest decade (like 1895 to 1890).
    # If the year is missing, keep it missing. Save all those decade values in a new column called DECADE

    # [LAMBDA]
    df["CENTURY"] = df["YEAR"].apply(
        lambda y: int(math.floor(y / 100) + 1) if pd.notna(y) else np.nan
    ) #For each year, figure out which century it belongs to (like 1895 becomes 19th century)
    # store that in a new column called CENTURY. Leave it missing if the year is missing

    #Create a new column called HAS_COORDS that says True when a shipwreck has both latitude and longitude
    #filled in (so we can put it on the map), and False if one or both are missing
    #[FILTER1] single-condition filter (coords must both exist)
    df["HAS_COORDS"] = df["LATITUDE"].notna() & df["LONGITUDE"].notna()

    return df


#3. HELPER FUNCTIONS

#[FUNC2P] function with 2+ parameters, one has a default value
def filter_wrecks(df, year_range, vessel_types=None, min_lives_lost=0):

    """
    Filter the shipwrecks DataFrame based on:
    - year_range (tuple: start year, end year)
    - vessel_types (list of types, or None for all types) a list of vessel types the user picked
    - min_lives_lost (minimum lives lost) if the user doesn’t choose anything, the number is 0 by default

    """

    # If no specific vessel types were chosen, then include ALL vessels, as long as vessel type is not missing.
    if not vessel_types:
        type_mask = df["VESSEL TYPE"].notna()
    else: #if they did pick Keep only the rows where VESSEL TYPE is one of the types picked
        type_mask = df["VESSEL TYPE"].isin(vessel_types)

    #(between) mask for the year range, is the YEAR of the wreck between the start and end year the user selected?
    year_mask = df["YEAR"].between(year_range[0], year_range[1])

    #did this wreck have at least the minimum number of lives lost the user typed in?
    lives_mask = df["LIVES_LOST_CLEAN"] >= min_lives_lost

    #[FILTER2] combine multiple conditions with AND only keep the rows where ALL THREE CONDITIONS are True.
    mask = year_mask & type_mask & lives_mask
    #Get only the rows where mask is True, and make a fresh copy of that data.
    filtered_df = df[mask].copy()
    return filtered_df


#[FUNCRETURN2] function returning two values
def get_year_limits(df):
    """
    Find the minimum and maximum YEAR values in the data.
    Returns (min_year, max_year).
    """
    years = df["YEAR"].dropna()#use the year column and drop years that are missing,so we get a clean list/Series of only the real year numbers.
    if years.empty:#Check if the column is empty
        return 1705, 2000  # fallback just in case
    return int(years.min()), int(years.max())


#4. INDIVIDUAL VIEW FUNCTIONS

#map
def show_map_view(filtered):
    st.header("Map of Shipwreck Locations")#header

    # Use only rows that have coordinates
    map_data = filtered[filtered["HAS_COORDS"]].copy()
    #If we filtered so much that no wrecks have coordinates left,show a message and STOP running the rest of this function.
    if map_data.empty:
        st.info("No wrecks with valid coordinates for the current filters.")
        return

    #Find the average latitude and average longitude. Use this as the spot where the map should center.
    center_lat = map_data["LATITUDE"].mean()
    center_lon = map_data["LONGITUDE"].mean()

    # Color code: green if 0 lives lost, red if > 0
    map_data["COLOR"] = map_data["LIVES_LOST_CLEAN"].apply(
        lambda x: [0, 180, 0, 160] if x == 0 else [220, 0, 0, 200]
    )#[R, G, B, transparency]

    layer = pdk.Layer(
        "ScatterplotLayer",
        data=map_data,#draw circles on the map, map_data contains only shipwrecks that have GPS coordinates.
        pickable=True,#makes the dots clickable/hoverable.
        opacity=0.8,#How see-through the dots are
        stroked=True,#Makes the circle edges sharper.
        filled=True,#If this was False → dots would be hollow.
        radius_scale=1,#How much to multiply the radius by
        radius_min_pixels=3,#Smallest size the dot is allowed to shrink to.
        radius_max_pixels=50,#Biggest size the dot is allowed to grow to.
        get_position=["LONGITUDE", "LATITUDE"],#This tells PyDeck the exact coordinates for each dot.
        get_radius="radius",#tells PyDeck which column controls the size of each dot.
        get_fill_color="COLOR",  #ed/green colors
        get_line_color=[0, 0, 0],  # black outline
    )

    view_state = pdk.ViewState(
        latitude=center_lat,#Center the map vertically on the average latitude of the wrecks.
        longitude=center_lon,#Center the map horizontally on the average longitude.
        zoom=6,#good regional view
        pitch=0,#flat/drone view of camera
    )

    tooltip = {
        "text": "{SHIP'S NAME}\nYear: {YEAR}\nType: {VESSEL TYPE}\nLives lost: {LIVES LOST}"
    }#When you hover over a dot, show a little popup box with information about that shipwreck.

    deck = pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,#When you hover over a dot, show a little popup box with information about that shipwreck.
        tooltip=tooltip,#Enable tooltips on hover.
        map_style="mapbox://styles/mapbox/streets-v11",
    )

    st.pydeck_chart(deck)#Put this PyDeck map on the Streamlit page.

    st.caption("Green dots = no lives lost, red dots = lives were lost.")#caption

#Show a bar chart of how many shipwrecks belong to each vessel type.
def show_vessel_chart_view(filtered):#making a function that takes the filtered DataFrame and draws a bar chart.
    st.header("Wrecks by Vessel Type")
#If the user filtered too much and the DataFrame has zero rows, we show a message and stop running the function.
    if filtered.empty:
        st.info("No wrecks match the current filters.")
        return

    # if it works, Count number of wrecks per vessel type
    counts = (
        filtered.groupby("VESSEL TYPE")#Group the rows by vessel type.
        ["SHIP'S NAME"].count()#Count how many shipwrecks are in each group.
        .reset_index(name="WRECK COUNT")#Turn it back into a normal DataFrame and rename the count column "WRECK COUNT".
    )

    #[SORT] sort so the biggest bar comes first
    counts = counts.sort_values("WRECK COUNT", ascending=False)

    #[CHART1] bar chart
    fig = px.bar( #Use Plotly Express to make a bar graph:
        counts,
        x="VESSEL TYPE",#X-axis: Vessel type
        y="WRECK COUNT",#Y-axis: How many times that type wrecked
        title="Number of Wrecks by Vessel Type",
    )
    fig.update_layout(
        xaxis_title="Vessel Type",
        yaxis_title="Number of Wrecks",
        showlegend=False,
    )

    st.plotly_chart(fig, use_container_width=True)#Show the bar graph on the Streamlit page.

    # #[MAXMIN] find vessel type with highest count
    max_row = counts.iloc[counts["WRECK COUNT"].idxmax()]#index location of the largest number and pull that row out
    st.write( #Show the user which vessel type had the most wrecks.
        f"The most frequently wrecked vessel type is **{max_row['VESSEL TYPE']}** "
        f"with **{int(max_row['WRECK COUNT'])}** wrecks in the current selection."
    )

    with st.expander("Show counts table"):
        st.dataframe(counts) #If the user clicks the expander, show the whole table of vessel type counts.

#show how wrecks changed year by year, using a line chart
def show_time_trend_view(filtered):
    st.header("Wrecks Over Time")
    #If the user filtered too much (no rows left), don’t try to draw a chart.
    if filtered.empty:
        st.info("No wrecks match the current filters.")
        return

    #Count wrecks per year
    yearly = (
        filtered.dropna(subset=["YEAR"])#Ignore any rows that don’t have a year.
        .groupby("YEAR")["SHIP'S NAME"]#Group all shipwrecks by year.
        .count()#Count how many shipwrecks were in each year.
        .reset_index(name="WRECK COUNT")#Turn it back into a DataFrame and name the count column “WRECK COUNT.”
    )

    #[CHART2] line chart (different from bar chart)
    fig = px.line(#Make a line chart
        yearly,
        x="YEAR",#xaxis
        y="WRECK COUNT",#yxis
        title="Number of Wrecks per Year (Filtered Selection)",
    )
    fig.update_layout(
        xaxis_title="Year",
        yaxis_title="Number of Wrecks",
    )

    st.plotly_chart(fig, use_container_width=True)#Put the chart on the page.

    st.subheader("Wrecks by Decade and Vessel Type")

    # #[PIVOTTABLE] pivot table summarizing counts
    pivot = filtered.pivot_table(
        index="DECADE",#Rows of the pivot table are DECADES:
        columns="VESSEL TYPE",#The columns of the table are vessel types
        values="SHIP'S NAME",#We are counting ship names.
        aggfunc="count",#We count how many wrecks fall into each decade/type combination.
        fill_value=0,#If no wrecks happened for that combo, show 0 instead of NaN.
    )
    st.dataframe(pivot)#Show the pivot table as a scrollable, sortable table in Streamlit.


def show_deadliest_view(filtered):
    """Show a table of the deadliest wrecks and some simple stats."""
    st.header("Deadliest Wrecks")

    if filtered.empty:
        st.info("No wrecks match the current filters.")
        return

    #Sort by lives lost (descending)
    deadly = filtered.sort_values("LIVES_LOST_CLEAN", ascending=False)

    #Top 10 deadliest
    top10 = deadly.head(10)
    #Show a table with the 10 deadliest wrecks and only the important columns.
    st.write("Top 10 deadliest wrecks in the current selection:")
    st.dataframe(
        top10[
            ["SHIP'S NAME", "YEAR", "VESSEL TYPE",
             "LOCATION LOST", "CAUSE OF LOSS", "LIVES LOST"]
        ]
    )

    st.subheader("Summary Statistics")

    # Build a dictionary of stats
    stats = {
        "Total wrecks in this selection": len(filtered),#Count how many rows are in the filtered dataset.
        "Wrecks with at least 1 life lost": int(
            (filtered["LIVES_LOST_CLEAN"] > 0).sum()#True for wrecks where someone died
        ),#sum converts True = 1, False = 0, so it counts them
        "Total lives lost in this selection": int(filtered["LIVES_LOST_CLEAN"].sum()),
        # Add up ALL lives lost across all wrecks in the selection.
        "Maximum lives lost in a single wreck": int(
            filtered["LIVES_LOST_CLEAN"].max() #Find the single deadliest wreck.
        ),
    }

    cols = st.columns(2)#Make 2 side-by-side columns to make the dashboard look clean.
    i = 0

    # #[ITERLOOP] loop through dict items
    for label, value in stats.items():#gives each (key, value) pair Put it in one of the two columns
        with cols[i % 2]:#switches between left column (0) and right column (1)
            st.metric(label=label, value=str(value))
        i += 1

    # #[DICTMETHOD] using .keys() method
    stat_names = ", ".join(stats.keys())#list of dictionary keys
    st.caption("Stats included: " + stat_names)#convert that into a readable string and show caption


#5. MAIN FUNCTION

def main():
    """Main function: sets up the page, sidebar, and decides which view to show."""
    st.set_page_config(
        page_title="Shipwreck Explorer",#Give the website a title (shows in browser tab)
        layout="wide",#Make the page layout wide, so charts look bigger
    )

    #Load the data once
    df = load_data()

    #[FUNCCALL2]
    min_year, max_year = get_year_limits(df)#Call the helper function to find the earliest and latest years in the dataset.

    #Sidebar
    st.sidebar.title("Filters")#Creates a sidebar section called “Filters.”

    #[ST2] slider for year range
    year_range = st.sidebar.slider(
        "Year of loss",
        min_value=min_year,
        max_value=max_year,
        value=(min_year, max_year),
        step=1
    )

    #[LISTCOMP] build list of vessel types (skipping blanks)
    vessel_types = sorted(
        [v for v in df["VESSEL TYPE"].dropna().unique() if str(v).strip() != ""]
    )#remove empty strings, values, keep unique one and display

    #[ST1] multiselect for vessel type
    selected_types = st.sidebar.multiselect(#Let the user choose multiple vessel types.
        "Vessel type(s)",
        options=vessel_types,
        default=vessel_types[:5] if len(vessel_types) >= 5 else vessel_types#first 5 types so something is selected.
    )

    min_lives = st.sidebar.number_input(#Let user filter for shipwrecks where at least X people died.
        "Minimum lives lost",
        min_value=0,
        max_value=int(df["LIVES_LOST_CLEAN"].max()),
        value=0,
        step=1
    )

    #[ST3] radio button to choose main view
    view_choice = st.sidebar.radio(#Let user pick between pages:
        "Choose a view",
        options=["Map", "Vessel Types", "Time Trends", "Deadliest Wrecks"],
        index=0
    )

    # Apply filters using our helper function
    #[FUNCCALL2] filter_wrecks is called here
    filtered = filter_wrecks(#Send all the selected filters to your filter_wrecks function.
        df,
        year_range=year_range,
        vessel_types=selected_types,
        min_lives_lost=min_lives
    )#Returns a new DataFrame containing only rows that match the filters.

    # -------- Main area --------
    st.title("Shipwreck Explorer")
    st.write(
        f"Showing wrecks from **{year_range[0]}** to **{year_range[1]}**, "
        f"vessel types: **{', '.join(selected_types) if selected_types else 'All'}**, "
        f"minimum lives lost: **{min_lives}**."
    )#Tell the user exactly what filters are currently applied.
    st.write(f"Number of wrecks in current selection: **{len(filtered)}**")#How many total wrecks match your filters?

    st.divider()

    # Show the chosen view
    if view_choice == "Map":
        show_map_view(filtered)
    elif view_choice == "Vessel Types":
        show_vessel_chart_view(filtered)
    elif view_choice == "Time Trends":
        show_time_trend_view(filtered)
    else:
        show_deadliest_view(filtered)


#6. RUN MAIN

if __name__ == "__main__":
    main()

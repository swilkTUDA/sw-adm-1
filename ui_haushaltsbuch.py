import streamlit as st
import pandas as pd
import datetime
import matplotlib.pyplot as plt
from azure.data.tables import TableServiceClient

# Function to load data from Azure
@st.cache_data(show_spinner=False)  # Cache the data load process
def load_data():
    AZURE_STORAGE_CONNECTION_STRING = st.secrets["HAUSHALTSBUCH_TABLE_CONNECTION"]
    TABLE_NAME = st.secrets["HAUSHALTSBUCH_TABLE_NAME"]
    service = TableServiceClient.from_connection_string(conn_str=AZURE_STORAGE_CONNECTION_STRING)
    table_client = service.get_table_client(table_name=TABLE_NAME)
    entities = table_client.list_entities()
    data = []

    for entity in entities:
        # those who have the field Datum set to - are newer entries the date format of old entries is a german format which needs to be processed differently TODO
        if "-" in entity["Datum"] and entity["EigeneKategorie"] not in ['Umbuchung', 'Kreditkarte']:

            entity['Betrag'] = entity['Betrag'].replace(",", ".")
            data.append(entity)
            
    return pd.DataFrame(data)

def render_haushaltsbuch_plots():
    if 'data' not in st.session_state:
        df = load_data()
        df['Datum'] = pd.to_datetime(df['Datum'], format='%Y-%m-%d %H:%M:%S')
        df['Betrag'] = pd.to_numeric(df['Betrag']).abs()  # Ensure 'Betrag' is numeric AND ABSOLUTE
        st.session_state['data'] = df

    df = st.session_state['data']

    if st.button("Frage Haushaltsbuch ab"):
        st.session_state.button_clicked = True
    
    if 'button_clicked' in st.session_state:
        st.sidebar.title("Filter")

        latest_date = df['Datum'].max()
        default_year = latest_date.year
        default_month = latest_date.month
        
        if "selected_year" not in st.session_state:
            st.session_state.selected_year = default_year
        if "selected_month" not in st.session_state:
            st.session_state.selected_month = default_month

        st.session_state.selected_year = st.sidebar.selectbox(
            "Select Year", 
            df['Datum'].dt.year.unique(), 
            index=list(df['Datum'].dt.year.unique()).index(st.session_state.selected_year)
        )
        st.session_state.selected_month = st.sidebar.selectbox(
            "Select Month", 
            df['Datum'].dt.month.unique(), 
            index=list(df['Datum'].dt.month.unique()).index(st.session_state.selected_month)
        )

        filtered_df = df[(df['Datum'].dt.year == st.session_state.selected_year) & (df['Datum'].dt.month == st.session_state.selected_month)]

        # Calculate the sum of expenses and income
        total_expenses = filtered_df[~filtered_df['EigeneKategorie'].isin(['Bargeld', 'Einnahme'])]['Betrag'].sum()
        total_income = filtered_df[filtered_df['EigeneKategorie'].isin(['Einnahme'])]['Betrag'].sum()

        # Display the sums
        st.write(f"Total Expenses: {total_expenses:.2f}")
        st.write(f"Total Income: {total_income:.2f}")
        # Create a datetime object using the selected year and month
        selected_date = datetime.datetime(st.session_state.selected_year, st.session_state.selected_month, 1)
        # Get the end of the selected month
        selected_date = pd.Timestamp(selected_date) + pd.offsets.MonthEnd(1)
        # List of the last 6 months
        months = pd.date_range(end=selected_date, periods=6, freq='M').to_period('M').strftime('%Y-%m').tolist()

        # Initialize a dictionary to store category sums for each month
        category_sums = {month: {} for month in months}

        for month in months:
            year, month_num = map(int, month.split('-'))
            month_df = df[(df['Datum'].dt.year == year) & (df['Datum'].dt.month == month_num)]
            for category in month_df['EigeneKategorie'].unique():
                category_total = month_df[month_df['EigeneKategorie'] == category]['Betrag'].sum()
                category_sums[f'{year}-{month_num:02d}'][category] = category_total

        # Convert the dictionary to a DataFrame
        matrix_df = pd.DataFrame(category_sums).fillna(0)

        # Display the DataFrame as a table
        st.write("Category Sums for the Last 6 Months")
        st.dataframe(matrix_df)
        # ---------- expenses per category
        st.write(f"Expenses per Category for {st.session_state.selected_year}-{st.session_state.selected_month:02d}")
        expenses = filtered_df[~filtered_df['EigeneKategorie'].isin(['Bargeld', 'Einnahme'])]
        category_grouped = expenses.groupby('EigeneKategorie').agg({'Betrag': 'sum'}).reset_index()
        category_grouped = category_grouped.sort_values(by='Betrag', ascending=False)

        # Plotting with Matplotlib
        fig, ax = plt.subplots(figsize=(10, 6))
        bars = ax.bar(category_grouped['EigeneKategorie'], category_grouped['Betrag'], color='skyblue')
        
        ax.set_xlabel('Category')
        ax.set_ylabel('Total Expenses')
        ax.set_title(f"Expenses per Category for {st.session_state.selected_year}-{st.session_state.selected_month:02d}")

        # Adding the labels
        for bar in bars:
            yval = bar.get_height()  # Get the y value of the bar
            ax.text(bar.get_x() + bar.get_width()/2, yval, round((-1.0)*yval, -1), ha='center', va='bottom')
        
        plt.xticks(rotation=45)  # Rotate category labels for better readability
        plt.tight_layout()  # Adjust layout to make room for the labels

        # Streamlit command to display the plot
        st.pyplot(fig)

        # ---- Summary of investments and Einnahme
        # Filter the data for the specific categories
        filtered_df = df[df['EigeneKategorie'].isin(['Investment', 'Einnahme'])]

        # Group by year and EigeneKategorie and calculate the sum of 'Betrag'
        annual_summary = filtered_df.groupby([df['Datum'].dt.year, 'EigeneKategorie']).agg({'Betrag': 'sum'}).reset_index()

        # Pivot the table to have years as rows and categories as columns
        summary_pivot = annual_summary.pivot(index='Datum', columns='EigeneKategorie', values='Betrag').fillna(0)

        # Display the table
        st.write("Annual Summary of 'Investment' and 'Einnahme'")
        st.table(summary_pivot)

        # ---- Monthly Average Summary per EigeneKategorie
        # Add Year and Month columns separately
        df['Year'] = df['Datum'].dt.year
        df['Month'] = df['Datum'].dt.month

        # Group by year, month, EigeneKategorie and calculate the average of 'Betrag'
        monthly_avg_summary = df.groupby(['Year', 'Month', 'EigeneKategorie']).agg({'Betrag': 'mean'}).reset_index()

        # Calculate the monthly average for each year and category
        annual_monthly_avg_summary = monthly_avg_summary.groupby(['Year', 'EigeneKategorie']).agg({'Betrag': 'mean'}).reset_index()

        # Pivot the table to have years as rows, EigeneKategorie as columns, and monthly average as cell values
        summary_pivot = annual_monthly_avg_summary.pivot(index='Year', columns='EigeneKategorie', values='Betrag').fillna(0)

        # Display the table
        st.write("Monthly Average of 'Betrag' per EigeneKategorie per Year")
        st.table(summary_pivot.T)     
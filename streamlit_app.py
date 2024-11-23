import streamlit as st
import requests
import json
from azure.storage.queue import QueueClient, TextBase64EncodePolicy
import time
import pandas as pd
import datetime
import matplotlib.pyplot as plt
from azure.data.tables import TableServiceClient


url = st.secrets["PEERBERRY_FUNCTION_AUTH_URL"]
api_key = st.secrets["PEERBERRY_FUNCTION_AUTH_API_KEY"]

st.title("SW Admin Panel for Peerberry")
tab1, tab2 = st.tabs(["Pb Invest", "Haushaltsbuch"])
with tab1:
    tfa = st.text_input("Two Factor Code", "")
    if st.button("Starte Peerberry (Queue)"):
        pb_payload = {
            "tfaCode": tfa
        }
        response = requests.post(url + api_key, json=pb_payload)
        if response.status_code == 200:
            access_key = response.json().get("access_token")
            service = QueueClient.from_connection_string(conn_str=st.secrets["QUEUE_CONNECTION_STRING"],
                                                                queue_name="peerberry-in",
                
                                                                message_encode_policy=TextBase64EncodePolicy())
            
            service.send_message(json.dumps({
                "access_token": access_key,
                "iteration": str(0),
                "max-iteration": str(10)
            }))
        else:
            st.write("Access Key nicht erhalten: FEHLER in AUTH!" )
    #-------------------------
    if st.button("Frage verfügbares Budget ab"):
        pb_payload = {
            "tfaCode": tfa
        }
        response = requests.post(url + api_key, json=pb_payload)
        if response.status_code == 200:
            access_key = response.json().get("access_token")
            url = st.secrets["PEERBERRY_FUNCTION_OVERVIEW_URL"]
            api_key = st.secrets["PEERBERRY_FUNCTION_OVERVIEW_API_KEY"]
            pb_payload = {
                    "access_token": access_key
            }
            response = requests.post(url + api_key, json=pb_payload)
            data = response.json()
            if response.status_code == 200:
                st.subheader("Main Financial Stats", divider=True)
                st.write(f"Available Money: {data['availableMoney']} {data['currencyIso']}")
                st.write(f"Invested: {data['invested']} {data['currencyIso']}")
                st.write(f"Total Profit: {data['totalProfit']} {data['currencyIso']}")
                st.write(f"Total Balance: {data['totalBalance']} {data['currencyIso']}")
                st.write(f"Net Annual Return: {data['netAnnualReturn']}%")
                st.write(f"Total Active Investments: {data['totalActiveInvestments']}")
                st.write(f"Balance Growth: {data['balanceGrowth']}%")
                st.write(f"Balance Growth Amount: {data['balanceGrowthAmount']} {data['currencyIso']}")

                # Investments by Countries
                st.subheader("Investments By Countries")
                countries = data['investmentsByCountries']

                # Convert countries data to Pandas DataFrame
                df_countries = pd.DataFrame(list(countries.items()), columns=['Country', 'Investments'])
                st.bar_chart(df_countries.set_index('Country'))

                # Plot a pie chart
                fig, ax = plt.subplots()
                ax.pie(df_countries['Investments'], labels=df_countries['Country'], autopct='%1.1f%%', startangle=140)
                st.pyplot(fig)
            
        else:
            st.write("Access Key nicht erhalten: FEHLER in AUTH!" )
with tab2:
    if st.button("Frage Haushaltsbuch ab"):
        AZURE_STORAGE_CONNECTION_STRING = st.secrets["HAUSHALTSBUCH_TABLE_CONNECTION"]
        TABLE_NAME = st.secrets["HAUSHALTSBUCH_TABLE_NAME"]

        service = TableServiceClient.from_connection_string(conn_str=AZURE_STORAGE_CONNECTION_STRING)
        table_client = service.get_table_client(table_name=TABLE_NAME)
        entities = table_client.list_entities()
        data = []

        for entity in entities:
            if  "-" in entity["Datum"] and entity["EigeneKategorie"] not in ['Umbuchung', 'Kreditkarte']:
                entity['Betrag'] = entity['Betrag'].replace(",",".")
                data.append(entity)

        df = pd.DataFrame(data)
        df['Datum'] = pd.to_datetime(df['Datum'], format='%Y-%m-%d %H:%M:%S') 
        df['Betrag'] = pd.to_numeric(df['Betrag'])  # Ensure 'Betrag' is numeric

        st.sidebar.title("Filter")
        latest_date = df['Datum'].max()
        default_year = latest_date.year
        default_month = latest_date.month
        selected_year = st.sidebar.selectbox("Select Year", df['Datum'].dt.year.unique(),index=list(df['Datum'].dt.year.unique()).index(default_year))
        selected_month = st.sidebar.selectbox("Select Month", df['Datum'].dt.month.unique(),index=list(df['Datum'].dt.month.unique()).index(default_month))

        filtered_df = df[(df['Datum'].dt.year == selected_year) & (df['Datum'].dt.month == selected_month)]
        # Calculate the sum of expenses and income
        total_expenses = filtered_df[filtered_df['Betrag'] < 0]['Betrag'].sum()
        total_income = filtered_df[filtered_df['Betrag'] > 0]['Betrag'].sum()

        # Display the sums
        st.write(f"Total Expenses: {total_expenses:.2f}")
        st.write(f"Total Income: {total_income:.2f}")

        # List of the last 6 months
        months = pd.date_range(end=latest_date, periods=6, freq='M').to_period('M').strftime('%Y-%m').tolist()

        # Initialize a dictionary to store category sums for each month
        category_sums = {month: {} for month in months}

        for month in months:
            year, month = map(int, month.split('-'))
            month_df = df[(df['Datum'].dt.year == year) & (df['Datum'].dt.month == month)]
            for category in month_df['EigeneKategorie'].unique():
                category_total = month_df[month_df['EigeneKategorie'] == category]['Betrag'].sum()
                category_sums[f'{year}-{month:02d}'][category] = category_total

        # Convert the dictionary to a DataFrame
        matrix_df = pd.DataFrame(category_sums).fillna(0)
        matrix_df = matrix_df #.transpose()

        # Display the DataFrame as a table
        st.write("Category Sums for the Last 6 Months")
        st.dataframe(matrix_df)
        
        st.write(f"Expenses per Category for {selected_year}-{selected_month:02d}")
        expenses = filtered_df[(filtered_df['Betrag'] < 0) & (df['EigeneKategorie'] != 'Einnahme')]
        category_grouped = expenses.groupby('EigeneKategorie').agg({'Betrag': 'sum'}).reset_index()
        category_grouped = category_grouped.sort_values(by='Betrag', ascending=False)
        # Plotting with Matplotlib
        fig, ax = plt.subplots(figsize=(10, 6))
        bars = ax.bar(category_grouped['EigeneKategorie'], category_grouped['Betrag'], color='skyblue')

        ax.set_xlabel('Category')
        ax.set_ylabel('Total Expenses')
        ax.set_title(f"Expenses per Category for {selected_year}-{selected_month:02d}")

        # Adding the labels
        for bar in bars:
            yval = bar.get_height()  # Get the y value of the bar
            ax.text(bar.get_x() + bar.get_width()/2, yval, round((-1.0)*yval, -1), ha='center', va='bottom')

        plt.xticks(rotation=45)  # Rotate category labels for better readability
        plt.tight_layout()  # Adjust layout to make room for the labels

        # Streamlit command to display the plot
        st.pyplot(fig)
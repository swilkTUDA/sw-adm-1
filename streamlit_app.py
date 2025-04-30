import streamlit as st
import requests
import json
from azure.storage.queue import QueueClient, TextBase64EncodePolicy
import time
import pandas as pd
import datetime
from azure.data.tables import TableServiceClient
import matplotlib.pyplot as plt
from ui_haushaltsbuch import render_haushaltsbuch_plots

url = st.secrets["PEERBERRY_FUNCTION_AUTH_URL"]
api_key = st.secrets["PEERBERRY_FUNCTION_AUTH_API_KEY"]

st.title("SW Admin Panel for Peerberry")
tab1, tab2, tab3 = st.tabs(["Pb Invest", "Haushaltsbuch", "Tourenrechner"])
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
    render_haushaltsbuch_plots()

with tab3:
    
    st.title("Ersparnisrechner für Fahrten")
    AZURE_STORAGE_CONNECTION_STRING = st.secrets["HAUSHALTSBUCH_TABLE_CONNECTION"]
    TABLE_NAME = st.secrets["TOURENRECHNER_TABLE_NAME"]
    service = TableServiceClient.from_connection_string(conn_str=AZURE_STORAGE_CONNECTION_STRING)
    table_client = service.get_table_client(table_name=TABLE_NAME)
    PARTITION_KEY = "default"
    ROW_KEY = "trips"

    try:
        entity = table_client.get_entity(partition_key=PARTITION_KEY, row_key=ROW_KEY)
        fahrten_arbeit_initial = int(entity['fahrten_arbeit'])
        fahrten_studio_initial = int(entity['fahrten_studio'])
    except Exception as e:
        st.error(f"Fehler beim Laden der Initialwerte: {e}")
        fahrten_arbeit_initial = 0
        fahrten_studio_initial = 0
    # Eingabe der Anzahl der Fahrten zur Arbeit und zum Studio
    fahrten_arbeit = st.number_input("Anzahl der Fahrten zur Arbeit", min_value=0, step=1, value=fahrten_arbeit_initial)
    fahrten_studio = st.number_input("Anzahl der Fahrten zum Studio", min_value=0, step=1, value=fahrten_studio_initial)
    # Distanzen in Kilometern
    distanz_arbeit = 22
    distanz_studio = 12
    benzin_preis_pro_km = 1.9 * 7.5 / 100 # 1,9 euro pro l bei 7,5 liter pro 100 kn

    # Berechnung der Ersparnis in Euro
    ersparnis_arbeit = fahrten_arbeit * (distanz_arbeit * benzin_preis_pro_km+8) 
    ersparnis_studio = fahrten_studio * distanz_studio * benzin_preis_pro_km

    # Gesamtersparnis
    gesamt_ersparnis = ersparnis_arbeit + ersparnis_studio

    # Anzeige der Ersparnis
    st.write(f"Ersparnis durch Fahrten zur Arbeit: {ersparnis_arbeit:.2f} Euro")
    st.write(f"Ersparnis durch Fahrten zum Studio: {ersparnis_studio:.2f} Euro")
    st.write(f"Gesamtersparnis: {gesamt_ersparnis:.2f} Euro")

    def save_values_to_azure(fahrten_arbeit, fahrten_studio):
        try:
            entity = {
                'PartitionKey': PARTITION_KEY,
                'RowKey': ROW_KEY,
                'fahrten_arbeit': fahrten_arbeit,
                'fahrten_studio': fahrten_studio
            }
            table_client.upsert_entity(entity)
            st.success("Daten erfolgreich gespeichert!")
        except Exception as e:
            st.error(f"Fehler beim Speichern der Daten: {e}")

    # Button zum Speichern der Werte
    if st.button("Werte speichern"):
        save_values_to_azure(fahrten_arbeit, fahrten_studio)
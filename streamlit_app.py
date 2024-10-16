import streamlit as st
import requests
import json
from azure.storage.queue import QueueClient, TextBase64EncodePolicy
import time
import pandas as pd
import datetime
import matplotlib.pyplot as plt


url = st.secrets["PEERBERRY_FUNCTION_AUTH_URL"]
api_key = st.secrets["PEERBERRY_FUNCTION_AUTH_API_KEY"]

st.title("SW Admin Panel for Peerberry")
tab1, tab2 = st.tabs(["Pb Invest", "Andere"])
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
                "max-iteration": str(30)
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
                ax.axis('equal')  # Equal aspect ratio ensures the pie chart is circular.
                st.pyplot(fig)
            iteration = 0
            st.subheader("Budget [€]", divider=True)
            while iteration < 40:
                url = st.secrets["PEERBERRY_FUNCTION_BUDGET_URL"]
                api_key = st.secrets["PEERBERRY_FUNCTION_BUDGET_API_KEY"]
                pb_payload = {
                    "access_token": access_key
                }
                response = requests.post(url + api_key, json=pb_payload)
                if response.status_code == 200:
                
                    st.write(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " - Available: "+ response.json().get("available_money")+"€")
                    time.sleep(30)
                else:
                    st.write("Error in budget request: "+str(response))
                    break
                iteration += 1
        else:
            st.write("Access Key nicht erhalten: FEHLER in AUTH!" )
with tab2:
    st.write("Not implemented yet")
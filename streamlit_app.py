import streamlit as st
import requests
import json
from azure.storage.queue import QueueClient, TextBase64EncodePolicy
import time
import datetime


url = st.secrets["PEERBERRY_FUNCTION_AUTH_URL"]
api_key = st.secrets["PEERBERRY_FUNCTION_AUTH_API_KEY"]

st.title("SW Admin Panel for Peerberry")
tfa = st.text_input("Two Factor Code", "")


if st.button("Starte Peerberry"):
    pb_payload = {
        "tfaCode": tfa
    }
    response = requests.post(url + api_key, json=pb_payload)
    if response.status_code == 200:
        access_key = response.json().get("access_token")
        iteration = 0
        while iteration < 12:
            url = st.secrets["PEERBERRY_FUNCTION_INVEST_URL"]
            api_key = st.secrets["PEERBERRY_FUNCTION_INVEST_API_KEY"]
            pb_payload = {
                "access_token": access_key
            }
            response = requests.post(url + api_key, json=pb_payload)
            st.write("Iteration "+str(iteration)+" completed!" )
            if response.status_code == 200:
                st.write("Result of the iteration: "+json.dumps(response.json()))
            else:
                st.write("Error in invest: "+str(response))
                break
            iteration += 1
    else:
        st.write("Access Key nicht erhalten: FEHLER in AUTH!" )
    
# ---------------------
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

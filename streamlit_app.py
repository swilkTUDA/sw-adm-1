import streamlit as st
import requests
import os
import json

url = "https://peerberryinvestsw.azurewebsites.net/api/peerberry_auth?code="
api_key = st.secrets["PEERBERRY_FUNCTION_AUTH_API_KEY"]

st.title("SW Admin Panel for Peerberry")
tfa = st.text_input("Two Factor Code", "")
if st.button("Starte Peerberry"):
    pb_payload = {
        "tfaCode": tfa
    }
    response = requests.post(url + api_key, json=pb_payload)
    if response.status_code == 200:
        access_key = response.get("access_token")
        iteration = 0
        while iteration < 12:
            url = "https://peerberryinvestsw.azurewebsites.net/api/peerberry_invest?code="
            api_key = st.secrets["PEERBERRY_FUNCTION_INVEST_API_KEY"]
            pb_payload = {
                "access_key": access_key
            }
            response = requests.post(url + api_key, json=pb_payload)
            st.write("Iteration "+str(iteration)+" completed!" )
            st.write("Result of the iteration: "+json.dumps(response))
            iteration += 1
    else:
        st.write("Access Key nicht erhalten: FEHLER in AUTH!" )
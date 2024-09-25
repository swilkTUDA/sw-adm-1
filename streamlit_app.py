import streamlit as st
import requests
import os
import json

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
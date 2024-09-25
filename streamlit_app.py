import streamlit as st
import requests
import os

url = "https://peerberryinvestsw.azurewebsites.net/api/peerberryinvesthttptrigger?code="
api_key = st.secrets["PEERBERRY_FUNCTION_API_KEY"]

st.title("SW Admin Panel for Peerberry")
tfa = st.text_input("Two Factor Code", "000000")
if st.button("Starte Peerberry"):
    pb_payload = {
        "tfaCode": tfa
    }
    response = requests.post(url + api_key, json=pb_payload)
    
    st.write("Daten übertragen: " + str(response))
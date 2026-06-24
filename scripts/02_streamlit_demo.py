"""Beispiel einer kleinen Streamlit-Web-App."""

import streamlit as st

st.set_page_config(page_title="Demo", page_icon="✨")

st.title("✨ Streamlit-Demo")
st.write("Diese Mini-App läuft im Browser – komplett auf deinem Rechner.")

name = st.text_input("Wie heißt du?")
if name:
    st.success(f"Hallo {name}! Schön, dich zu sehen. 👋")

zahl = st.slider("Wähle eine Zahl", 0, 100, 42)
st.metric("Deine Zahl", zahl, delta=zahl - 50)

st.divider()
st.caption("Tipp: Den Code dieser Datei findest du in `scripts/02_streamlit_demo.py`.")

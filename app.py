import streamlit as st
from wedding_planner.db import Base, engine
from wedding_planner.ui.pages import auth, app

st.set_page_config(page_title="EverAfter AI", page_icon="💍", layout="wide")
Base.metadata.create_all(bind=engine)

if "user_id" not in st.session_state:
    auth()
else:
    app()

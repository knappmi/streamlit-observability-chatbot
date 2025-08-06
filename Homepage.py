import streamlit as st

st.set_page_config(page_title="ANF Streamlit Service", page_icon="⚡")

ask_jarvis = st.Page("app/agentic_ai/1_Ask_Jarvis.py", title="Ask Jarvis", icon="🤖")
sre_bot = st.Page("app/agentic_ai/2_SRE_Bot.py", title="SRE Bot", icon="🤖")
getting_started = st.Page("app/docs/Getting_started.py", title="Getting Started", icon="📚")
sp = st.navigation(
    {"AgenticAI": [ask_jarvis, sre_bot],
     "Docs": [getting_started]
     },
    
    position="top",
)

sp.run()


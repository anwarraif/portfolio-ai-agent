import streamlit as st
from phi.assistant import Assistant
from phi.llm.openai import OpenAIChat
from phi.tools.yfinance import YFinanceTools

# 1. Set page config as the first Streamlit command
st.set_page_config(
    page_title="Agen Investasi",
    page_icon="../../favicon.ico",
    layout="wide"
)

# 2. Custom CSS for purple styling
st.markdown(
    """
    <style>
    /* Make text inputs have a purple border */
    .stTextInput input {
        border: 1px solid #800080 !important;
    }
    /* Make buttons purple */
    .stButton button {
        background-color: #800080 !important;
        color: #ffffff !important;
        border: none !important;
    }
    /* Make slider track purple */
    .stSlider > div[data-baseweb="slider"] > div {
        background-color: #800080 !important;
    }
    /* Footer style */
    .footer {
        text-align: center;
        margin-top: 20px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# 3. Display the logo in the sidebar
st.sidebar.image("logo.png", use_container_width=True)

# 4. Sidebar title
st.sidebar.title("Agen Investasi")

# 5. Sidebar input for OpenAI API key
openai_api_key = st.sidebar.text_input("Masukkan API OpenAI", type="password")

# 6. Optional slider for historical data range
history_range = st.sidebar.slider("Rentang data historis (hari)", 30, 365, 90)

# 7. Page caption
st.caption("AI Agen untuk membandingkan kinerja beberapa saham dan menghasilkan laporan secara terperinci.")

# 8. Define a system prompt to frame AI as a financial expert & data scientist
system_prompt = (
    "You are an expert financial analyst, proficient in Python and data "
    "visualizations. Your goal is to provide professional, data-driven insights "
    "on the stock market. Please note you are not a financial advisor, and users "
    "should conduct their own research."
)

# 9. Initialize the assistant if API key is provided
if openai_api_key:
    assistant = Assistant(
        llm=OpenAIChat(
            model="gpt-4o",
            api_key=openai_api_key,
            system_prompt=system_prompt
        ),
        tools=[
            YFinanceTools(
                stock_price=True,
                analyst_recommendations=True,
                company_info=True,
                company_news=True
            )
        ],
        show_tool_calls=True,
    )

    # 10. Multi-select drop-down for stocks (up to 4)
    available_stocks = [
        "AAPL", "AMZN", "TSLA", "MSFT", "GOOGL", "META", "NFLX", "NVDA", 
        "BABA", "BAC", "JPM", "WMT", "DIS", "V", "MA"
    ]
    selected_stocks = st.multiselect(
        "Pilih simbol saham (2 hingga 4)",
        options=available_stocks,
        max_selections=4
    )

    # 11. Button to trigger comparison
    if st.button("Bandingkan"):
        if len(selected_stocks) < 2:
            st.warning("Pilih minimal 2 simbol saham untuk dibandingkan.")
        else:
            # Build the query using selected symbols
            stock_list = ", ".join(selected_stocks)
            query = (
                f"Bandingkan {stock_list} selama {history_range} hari. "
                "Tampilkan hasil dalam format tabel. Gunakan semua tools yang tersedia."
            )
            response = assistant.run(query, stream=False)
            st.write(response)

# 12. Footer for disclaimer & copyright
st.markdown(
    """
    <div class="footer" style="padding-top: 10px;">
        <span class="disclaimer-icon" 
              title="Disclaimer: AI may not always provide accurate or complete information. 
                     Agentic AI x Corporate Learning Division">
              ℹ️
        </span>
        <span>All rights reserved. © 2025 Patria & Co.</span>
    </div>
    """,
    unsafe_allow_html=True
)

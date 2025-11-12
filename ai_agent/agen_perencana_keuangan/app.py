from textwrap import dedent
from phi.assistant import Assistant
from phi.tools.serpapi_tools import SerpApiTools
import streamlit as st
from phi.llm.openai import OpenAIChat

# Set up the Streamlit app
# st.title("AI Perencana Keuangan Pribadi 💰")
# st.caption("Kelola keuangan Anda dengan AI Personal Finance Manager dengan membuat anggaran yang dipersonalisasi, rencana investasi, dan strategi tabungan menggunakan GPT-4o")

st.set_page_config(
    page_title="AI Perencana Keuangan Pribadi",
    page_icon="../../favicon.ico",
    layout="wide"
)
st.caption("💰 Kelola keuangan Anda dengan AI Personal Finance Manager dengan membuat anggaran yang dipersonalisasi, rencana investasi, dan strategi tabungan menggunakan GPT-4o.")

# Get OpenAI API key from user
openai_api_key = st.text_input("Masukkan API OpenAI untuk mengakses GPT-4o", type="password")

# Get SerpAPI key from the user
serp_api_key = st.text_input("Masukkan API Serp untuk fungsi Pencarian", type="password")

if openai_api_key and serp_api_key:
    researcher = Assistant(
        name="Researcher",
        role="Mencari saran keuangan, peluang investasi, dan strategi tabungan berdasarkan preferensi pengguna",
        llm=OpenAIChat(model="gpt-4o", api_key=openai_api_key),
        description=dedent(
            """\
        Kamu adalah peneliti keuangan kelas dunia. Berdasarkan tujuan keuangan dan situasi keuangan pengguna saat ini, buatlah daftar istilah pencarian untuk menemukan saran keuangan, peluang investasi, dan strategi menabung yang relevan. Kemudian, telusuri setiap istilah di web, analisis hasilnya, dan tampilkan 10 hasil yang paling relevan.
        """
        ),
        instructions=[
            "Mengingat tujuan keuangan dan situasi keuangan pengguna saat ini, pertama-tama buat daftar 3 istilah pencarian yang terkait dengan tujuan tersebut.",
            "Untuk setiap istilah pencarian, `search_google` dan analisis hasilnya.",
            "Dari semua hasil pencarian, tampilkan 10 hasil yang paling relevan dengan preferensi pengguna.",
            "Ingat: kualitas hasil itu penting.",
        ],
        tools=[SerpApiTools(api_key=serp_api_key)],
        add_datetime_to_instructions=True,
    )
    planner = Assistant(
        name="Planner",
        role="Menghasilkan rencana keuangan yang dipersonalisasi berdasarkan preferensi pengguna dan hasil penelitian",
        llm=OpenAIChat(model="gpt-4o", api_key=openai_api_key),
        description=dedent(
            """\
        Anda adalah perencana keuangan senior. Dengan mempertimbangkan tujuan keuangan pengguna, situasi keuangan saat ini, dan daftar hasil penelitian, tujuan Anda adalah membuat rencana keuangan yang dipersonalisasi yang memenuhi kebutuhan dan preferensi pengguna.
        """
        ),
        instructions=[
            "Mengingat tujuan keuangan pengguna, situasi keuangan saat ini, dan daftar hasil penelitian, buatlah rencana keuangan pribadi yang mencakup anggaran yang disarankan, rencana investasi, dan strategi tabungan.",
            "Pastikan rencana tersebut terstruktur dengan baik, informatif, dan menarik.",
            "Pastikan Anda memberikan rencana yang bernuansa dan seimbang, dengan mengutip fakta jika memungkinkan.",
            "Ingat: kualitas rencana itu penting.",
            "Fokus pada kejelasan, koherensi, dan kualitas keseluruhan.",
            "Jangan pernah mengarang fakta atau menjiplak. Selalu berikan atribusi yang tepat.",
        ],
        add_datetime_to_instructions=True,
        add_chat_history_to_prompt=True,
        num_history_messages=3,
    )

    # Input fields for the user's financial goals and current financial situation
    financial_goals = st.text_input("Apa tujuan keuangan kamu?")
    current_situation = st.text_area("Jelaskan situasi keuangan kamu saat ini")

    if st.button("Buat Rencana Keuangan"):
        with st.spinner("Processing..."):
            # Get the response from the assistant
            response = planner.run(f"Tujuan keuangan: {financial_goals}, Situasi saat ini: {current_situation}", stream=False)
            st.write(response)

# Import the required libraries
from textwrap import dedent
from phi.assistant import Assistant
from phi.tools.serpapi_tools import SerpApiTools
from phi.tools.newspaper4k import Newspaper4k as NewspaperToolkit
import streamlit as st
from phi.llm.openai import OpenAIChat

# Set up the Streamlit app
st.set_page_config(
    page_title="Agen Jurnalis AI",
    page_icon="../../favicon.ico",
    layout="wide"
)

# Main title and description
st.title("Agen Jurnalis AI 🗞️")
st.caption("Hasilkan artikel berkualitas tinggi dengan Agen Jurnalis AI dengan meneliti, menulis, dan mengedit artikel berkualitas secara otomatis menggunakan GPT-4o")

# Display the image
st.image("E:/Work/Patria&Co/AI_Agent/patria&co.png", caption="Patria & Co", width=200)

# Sidebar for API keys
st.sidebar.title("Konfigurasi API")
st.sidebar.markdown("Silakan masukkan kunci API Anda di bawah ini:")
openai_api_key = st.sidebar.text_input("Kunci API OpenAI", type="password", help="Masukkan kunci API OpenAI untuk mengakses GPT-4o")
serp_api_key = st.sidebar.text_input("Kunci API Serp", type="password", help="Masukkan kunci API Serp untuk fungsi Pencarian")

# Check if API keys are provided
if openai_api_key and serp_api_key:
    # Initialize assistants
    searcher = Assistant(
        name="Pencari",
        role="Mencari URL teratas berdasarkan topik",
        llm=OpenAIChat(model="gpt-4o", api_key=openai_api_key),
        description=dedent(
            """\
        Anda adalah jurnalis kelas dunia untuk New York Times. Diberikan sebuah topik, buatlah daftar 3 istilah pencarian
        untuk menulis artikel tentang topik tersebut. Kemudian cari di web untuk setiap istilah, analisis hasilnya
        dan kembalikan 10 URL yang paling relevan.
        """
        ),
        instructions=[
            "Diberikan sebuah topik, pertama buat daftar 3 istilah pencarian yang terkait dengan topik tersebut.",
            "Untuk setiap istilah pencarian, `search_google` dan analisis hasilnya."
            "Dari hasil semua pencarian, kembalikan 10 URL yang paling relevan dengan topik tersebut.",
            "Ingat: Anda menulis untuk New York Times, jadi kualitas sumber sangat penting.",
        ],
        tools=[SerpApiTools(api_key=serp_api_key)],
        add_datetime_to_instructions=True,
    )
    writer = Assistant(
        name="Penulis",
        role="Mengambil teks dari URL dan menulis artikel berkualitas tinggi",
        llm=OpenAIChat(model="gpt-4o", api_key=openai_api_key),
        description=dedent(
            """\
        Anda adalah penulis senior untuk New York Times. Diberikan sebuah topik dan daftar URL,
        tujuan Anda adalah menulis artikel berkualitas tinggi yang layak untuk NYT tentang topik tersebut.
        """
        ),
        instructions=[
            "Diberikan sebuah topik dan daftar URL, pertama baca artikel menggunakan `get_article_text`."
            "Kemudian tulis artikel berkualitas tinggi yang layak untuk NYT tentang topik tersebut."
            "Artikel harus terstruktur dengan baik, informatif, dan menarik",
            "Pastikan panjangnya setidaknya sepanjang cerita sampul NYT -- minimal 15 paragraf.",
            "Pastikan Anda memberikan opini yang bernuansa dan seimbang, mengutip fakta jika memungkinkan.",
            "Ingat: Anda menulis untuk New York Times, jadi kualitas artikel sangat penting.",
            "Fokus pada kejelasan, koherensi, dan kualitas keseluruhan.",
            "Jangan pernah membuat fakta atau menjiplak. Selalu berikan atribusi yang tepat.",
        ],
        tools=[NewspaperToolkit()],
        add_datetime_to_instructions=True,
        add_chat_history_to_prompt=True,
        num_history_messages=3,
    )

    editor = Assistant(
        name="Editor",
        llm=OpenAIChat(model="gpt-4o", api_key=openai_api_key),
        team=[searcher, writer],
        description="Anda adalah editor senior NYT. Diberikan sebuah topik, tujuan Anda adalah menulis artikel yang layak untuk NYT.",
        instructions=[
            "Diberikan sebuah topik, minta jurnalis pencari untuk mencari URL yang paling relevan untuk topik tersebut.",
            "Kemudian berikan deskripsi topik dan URL kepada penulis untuk mendapatkan draf artikel.",
            "Edit, koreksi, dan perbaiki artikel untuk memastikan memenuhi standar tinggi New York Times.",
            "Artikel harus sangat artikulatif dan ditulis dengan baik. "
            "Fokus pada kejelasan, koherensi, dan kualitas keseluruhan.",
            "Pastikan artikel menarik dan informatif.",
            "Ingat: Anda adalah penjaga akhir sebelum artikel diterbitkan.",
        ],
        add_datetime_to_instructions=True,
        markdown=True,
    )

    # Input field for the report query
    st.markdown("### Masukkan Topik Artikel")
    query = st.text_input("Apa yang Anda ingin jurnalis AI tulis dalam Artikel?", help="Masukkan topik yang ingin Anda eksplorasi dalam artikel.")

    if query:
        with st.spinner("Memproses..."):
            # Get the response from the assistant
            response = editor.run(query, stream=False)
            st.markdown("### Hasil Artikel")
            st.write(response)
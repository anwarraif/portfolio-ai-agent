import streamlit as st
import openai
import os
import requests

# Streamlit app setup
st.set_page_config(
    page_title="Asisten Rapat 📝",
    page_icon="../../favicon.ico",
    layout="wide"
)

st.title("Asisten Rapat 📝")
st.sidebar.header("API Keys")
openai_api_key = st.sidebar.text_input("OpenAI API Key", type="password")
serper_api_key = st.sidebar.text_input("Serp API Key", type="password")

# Check if API keys are set
if openai_api_key and serper_api_key:
    # Set API key for OpenAI
    openai.api_key = openai_api_key
    os.environ["SERPER_API_KEY"] = serper_api_key

    # Helper functions
    def call_openai(prompt, model="gpt-4", temperature=0.7):
        """
        Call OpenAI API with the given prompt.
        """
        try:
            response = openai.ChatCompletion.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
            )
            return response['choices'][0]['message']['content'].strip()
        except Exception as e:
            st.error(f"Error: {e}")
            return None

    def search_serper(query):
        """
        Call Serper API to perform a search query.
        """
        try:
            url = "https://google.serper.dev/search"
            headers = {"X-API-KEY": serper_api_key}
            payload = {"q": query}
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            return data.get("organic", [])
        except Exception as e:
            st.error(f"Error accessing Serper API: {e}")
            return []

    # Input fields
    company_name = st.text_input("Masukkan nama perusahaan:")
    meeting_objective = st.text_input("Masukkan tujuan rapat:")
    attendees = st.text_area("Masukkan peserta rapat dan peran mereka (satu per baris):")
    meeting_duration = st.number_input("Durasi rapat (dalam menit):", min_value=15, max_value=180, value=60, step=15)
    focus_areas = st.text_input("Masukkan area fokus atau kekhawatiran khusus:")

    # Generate meeting preparation content when user clicks the button
    if st.button("Siapkan Rapat"):
        with st.spinner("Asisten AI sedang mempersiapkan materi rapat..."):
            # Use Serper for context
            company_search_results = search_serper(company_name)
            context_analysis = call_openai(f"""
            Analisis konteks untuk rapat dengan {company_name}:
            1. Tujuan rapat: {meeting_objective}
            2. Peserta rapat: {attendees}
            3. Durasi rapat: {meeting_duration} menit
            4. Area fokus atau kekhawatiran: {focus_areas}

            Hasil pencarian untuk {company_name}:
            {company_search_results}

            Lakukan riset mendalam tentang {company_name}, termasuk:
            - Berita terbaru dan rilis pers
            - Produk atau layanan utama
            - Pesaing utama

            Berikan ringkasan komprehensif tentang temuan Anda, soroti informasi yang paling relevan dengan konteks rapat. Gunakan format markdown dengan heading dan subheading yang sesuai.
            """)

            industry_analysis = call_openai(f"""
            Berdasarkan analisis konteks rapat dengan {company_name} dan tujuan rapat "{meeting_objective}", berikan analisis industri yang mendalam:
            1. Tren dan perkembangan utama di industri
            2. Peluang dan ancaman potensial
            3. Posisi pasar {company_name}

            Pastikan analisis relevan dengan tujuan rapat dan peran peserta. Gunakan format markdown dengan heading dan subheading yang sesuai.
            """)

            strategy_development = call_openai(f"""
            Berdasarkan analisis konteks dan wawasan industri, buat strategi rapat dan agenda yang terperinci untuk rapat berdurasi {meeting_duration} menit dengan {company_name}. Sertakan:
            1. Agenda waktu dengan tujuan jelas untuk setiap bagian
            2. Poin diskusi utama untuk setiap item agenda
            3. Peserta yang bertanggung jawab untuk setiap bagian
            4. Strategi untuk mengatasi area fokus atau kekhawatiran: {focus_areas}

            Pastikan strategi dan agenda selaras dengan tujuan rapat: {meeting_objective}.
            Gunakan format markdown dengan heading dan subheading yang sesuai.
            """)

            executive_brief = call_openai(f"""
            Sintesis semua informasi yang telah dikumpulkan menjadi sebuah ringkasan eksekutif yang komprehensif namun singkat untuk rapat dengan {company_name}:
            1. Ringkasan eksekutif satu halaman yang mencakup:
               - Tujuan rapat
               - Daftar peserta dan peran mereka
               - Poin-poin penting tentang {company_name} dan konteks industri yang relevan
               - 3-5 tujuan strategis utama rapat
               - Gambaran struktur rapat dan topik utama
            2. Poin diskusi utama, masing-masing didukung oleh data atau statistik yang relevan.
            3. Antisipasi pertanyaan potensial dari peserta dan sediakan jawaban berbasis data.
            4. Rekomendasi strategis dan langkah berikutnya.

            Format output menggunakan markdown dengan heading utama (H1), heading bagian (H2), dan subheading (H3) yang sesuai.
            """)

        # Display results
        if context_analysis:
            st.markdown("## 📌 Analisis Konteks Rapat")
            st.markdown(context_analysis)

        if industry_analysis:
            st.markdown("## 🌍 Analisis Industri")
            st.markdown(industry_analysis)

        if strategy_development:
            st.markdown("## 📝 Strategi dan Agenda Rapat")
            st.markdown(strategy_development)

        if executive_brief:
            st.markdown("## 📋 Ringkasan Eksekutif")
            st.markdown(executive_brief)

    st.sidebar.markdown("""
    ## Cara menggunakan aplikasi ini:
    1. Masukkan API Key OpenAI dan Serper di sidebar.
    2. Isi informasi rapat yang diminta.
    3. Klik 'Siapkan Rapat' untuk menghasilkan paket persiapan rapat.

    Proses ini dapat memakan waktu beberapa menit. Harap bersabar!
    """)
else:
    st.warning("Harap masukkan semua API Key di sidebar untuk melanjutkan.")

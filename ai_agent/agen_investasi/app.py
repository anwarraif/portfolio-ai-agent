# Import the required libraries
import streamlit as st
from phi.assistant import Assistant
from phi.llm.openai import OpenAIChat
from phi.tools.yfinance import YFinanceTools
import time

# Set up the Streamlit app
st.set_page_config(
    page_title="Agen Investasi AI",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 2rem 0;
        background: linear-gradient(90deg, #1f4037 0%, #99f2c8 100%);
        margin: -1rem -1rem 2rem -1rem;
        border-radius: 10px;
        color: white;
    }
    
    .stTextInput > div > div > input {
        border-radius: 10px;
        border: 2px solid #e0e0e0;
        padding: 0.5rem;
        font-size: 16px;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: #1f4037;
        box-shadow: 0 0 0 0.2rem rgba(31, 64, 55, 0.25);
    }
    
    .stock-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 4px solid #1f4037;
        margin: 1rem 0;
    }
    
    .comparison-section {
        background: #f8f9fa;
        padding: 2rem;
        border-radius: 10px;
        margin: 2rem 0;
    }
    
    .feature-box {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        text-align: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        margin: 0.5rem;
    }
    
    .status-success {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        padding: 0.75rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    
    .status-warning {
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        color: #856404;
        padding: 0.75rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div class="main-header">
    <h1>📈 Agen Investasi AI</h1>
    <p>Platform AI canggih untuk analisis dan perbandingan saham</p>
</div>
""", unsafe_allow_html=True)

# Sidebar for API key and settings
with st.sidebar:
    st.header("🔧 Pengaturan")
    
    # API Key input
    st.subheader("🔑 Konfigurasi API")
    openai_api_key = st.text_input(
        "OpenAI API Key", 
        type="password",
        help="Masukkan API key OpenAI Anda untuk menggunakan layanan AI"
    )
    
    if openai_api_key:
        st.markdown('<div class="status-success">✅ API Key berhasil dikonfigurasi</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="status-warning">⚠️ Masukkan API Key untuk melanjutkan</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Features section
    st.subheader("🎯 Fitur Analisis")
    features = [
        "📊 Harga Saham Real-time",
        "📈 Rekomendasi Analis",
        "🏢 Informasi Perusahaan",
        "📰 Berita Terkini"
    ]
    
    for feature in features:
        st.markdown(f"• {feature}")
    
    st.markdown("---")
    
    # Help section
    st.subheader("❓ Bantuan")
    with st.expander("Cara Menggunakan"):
        st.write("""
        1. Masukkan OpenAI API Key di kolom yang tersedia
        2. Pilih atau ketik simbol saham yang ingin dibandingkan
        3. Klik tombol 'Bandingkan Saham' untuk mendapatkan analisis
        4. Tunggu hingga AI selesai menganalisis dan memberikan laporan
        """)
    
    with st.expander("Contoh Simbol Saham"):
        st.write("""
        **Saham Amerika:**
        - AAPL (Apple)
        - GOOGL (Google)
        - MSFT (Microsoft)
        - TSLA (Tesla)
        
        **Saham Indonesia:**
        - BBCA.JK (Bank BCA)
        - TLKM.JK (Telkom)
        - ASII.JK (Astra International)
        """)

# Main content area
if openai_api_key:
    # Stock input section
    st.header("🔍 Pilih Saham untuk Dibandingkan")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        <div class="stock-card">
            <h4>📍 Saham Pertama</h4>
        </div>
        """, unsafe_allow_html=True)
        
        # Popular stocks for first selection
        popular_stocks_1 = ["", "AAPL", "GOOGL", "MSFT", "TSLA", "BBCA.JK", "TLKM.JK"]
        stock1_option = st.selectbox(
            "Pilih dari daftar populer:",
            popular_stocks_1,
            key="stock1_select"
        )
        
        stock1_manual = st.text_input(
            "Atau ketik simbol saham:",
            placeholder="Contoh: AAPL, BBCA.JK",
            key="stock1_input"
        )
        
        stock1 = stock1_manual if stock1_manual else stock1_option
        
        if stock1:
            st.success(f"✅ Saham terpilih: {stock1}")
    
    with col2:
        st.markdown("""
        <div class="stock-card">
            <h4>📍 Saham Kedua</h4>
        </div>
        """, unsafe_allow_html=True)
        
        # Popular stocks for second selection
        popular_stocks_2 = ["", "GOOGL", "AAPL", "MSFT", "TSLA", "TLKM.JK", "BBCA.JK"]
        stock2_option = st.selectbox(
            "Pilih dari daftar populer:",
            popular_stocks_2,
            key="stock2_select"
        )
        
        stock2_manual = st.text_input(
            "Atau ketik simbol saham:",
            placeholder="Contoh: GOOGL, TLKM.JK",
            key="stock2_input"
        )
        
        stock2 = stock2_manual if stock2_manual else stock2_option
        
        if stock2:
            st.success(f"✅ Saham terpilih: {stock2}")
    
    # Analysis section
    if stock1 and stock2:
        st.markdown("---")
        
        # Comparison preview
        st.markdown(f"""
        <div class="comparison-section">
            <h3 style="text-align: center; color: #1f4037;">
                🆚 Perbandingan: {stock1} vs {stock2}
            </h3>
            <p style="text-align: center; color: #666;">
                AI akan menganalisis kedua saham menggunakan data real-time dan memberikan rekomendasi investasi
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # Analysis button
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            analyze_button = st.button(
                "🚀 Mulai Analisis Perbandingan",
                use_container_width=True,
                type="primary"
            )
        
        if analyze_button:
            try:
                # Create an instance of the Assistant
                with st.spinner("🤖 Menginisialisasi AI Assistant..."):
                    assistant = Assistant(
                        llm=OpenAIChat(model="gpt-4o", api_key=openai_api_key),
                        tools=[YFinanceTools(
                            stock_price=True, 
                            analyst_recommendations=True, 
                            company_info=True, 
                            company_news=True
                        )],
                        show_tool_calls=True,
                    )
                
                # Progress bar
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # Simulate analysis steps
                steps = [
                    "Mengambil data harga saham...",
                    "Menganalisis rekomendasi analis...",
                    "Mengumpulkan informasi perusahaan...",
                    "Mencari berita terkini...",
                    "Menyusun laporan perbandingan..."
                ]
                
                for i, step in enumerate(steps):
                    status_text.text(step)
                    progress_bar.progress((i + 1) / len(steps))
                    time.sleep(1)
                
                # Get the response from the assistant
                status_text.text("🔍 Menghasilkan analisis mendalam...")
                query = f"""
                Bandingkan saham {stock1} dengan {stock2}. 
                Berikan analisis komprehensif yang mencakup:
                1. Performa harga dan tren
                2. Rekomendasi analis
                3. Informasi fundamental perusahaan
                4. Berita dan perkembangan terkini
                5. Kesimpulan dan rekomendasi investasi
                
                Gunakan semua tools yang tersedia dan berikan laporan dalam bahasa Indonesia.
                """
                
                response = assistant.run(query, stream=False)
                
                # Clear progress indicators
                progress_bar.empty()
                status_text.empty()
                
                # Display results
                st.success("✅ Analisis selesai!")
                
                # Results section
                st.markdown("## 📋 Laporan Analisis Perbandingan")
                
                # Create tabs for organized display
                tab1, tab2, tab3 = st.tabs(["📊 Hasil Analisis", "🔧 Detail Tools", "📖 Ringkasan"])
                
                with tab1:
                    st.markdown("### 🤖 Analisis AI Assistant")
                    st.write(response)
                
                with tab2:
                    st.markdown("### 🛠️ Tools yang Digunakan")
                    st.info("Analisis ini menggunakan:")
                    tools_used = [
                        "📈 YFinance - Data harga real-time",
                        "📊 Rekomendasi analis profesional", 
                        "🏢 Informasi fundamental perusahaan",
                        "📰 Berita dan update terkini"
                    ]
                    for tool in tools_used:
                        st.write(f"• {tool}")
                
                with tab3:
                    st.markdown("### 📝 Ringkasan Perbandingan")
                    st.info(f"Perbandingan antara {stock1} dan {stock2} telah selesai dianalisis menggunakan AI dengan data terkini dari berbagai sumber finansial.")
                
            except Exception as e:
                st.error(f"❌ Terjadi kesalahan: {str(e)}")
                st.info("💡 Pastikan API key valid dan simbol saham benar")

else:
    # Welcome screen when no API key
    st.markdown("""
    <div style="text-align: center; padding: 3rem;">
        <h2>🔑 Masukkan API Key untuk Memulai</h2>
        <p style="font-size: 18px; color: #666;">
            Untuk menggunakan Agen Investasi AI, silakan masukkan OpenAI API Key di sidebar kiri.
        </p>
        <br>
        <div style="display: flex; justify-content: center; gap: 2rem; flex-wrap: wrap;">
            <div class="feature-box">
                <h4>📊 Analisis Real-time</h4>
                <p>Data harga dan performa terkini</p>
            </div>
            <div class="feature-box">
                <h4>🤖 AI-Powered</h4>
                <p>Analisis cerdas dengan GPT-4</p>
            </div>
            <div class="feature-box">
                <h4>📈 Rekomendasi Expert</h4>
                <p>Insight dari analis profesional</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 1rem;">
    <p>🤖 Powered by AI • 📈 Real-time Financial Data • 🔒 Secure & Private</p>
</div>
""", unsafe_allow_html=True)
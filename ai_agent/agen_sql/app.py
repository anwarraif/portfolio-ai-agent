"""
Agen AI Database Chinook dengan Interface Streamlit
Implementasi single file untuk analisis database SQLite dengan integrasi OpenAI
"""

import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import streamlit as st
import openai
import json
import re
import os
import sys
from typing import Dict, Any, List, Tuple
import io
import base64
from datetime import datetime
import warnings

# Menghilangkan warning untuk output yang lebih bersih
warnings.filterwarnings('ignore')

# Konfigurasi - PERBARUI NILAI-NILAI INI
DATABASE_PATH = "chinook.db"  # Path ke file chinook.db Anda

class AgenDatabaseChinook:
    def __init__(self, db_path: str, openai_api_key: str):
        """
        Inisialisasi Agen AI Database Chinook
        
        Args:
            db_path: Path ke database SQLite chinook.db
            openai_api_key: API key OpenAI
        """
        self.db_path = db_path
        
        # Validasi database ada
        if not os.path.exists(db_path):
            raise FileNotFoundError(f"File database tidak ditemukan: {db_path}")
        
        # Inisialisasi klien OpenAI
        try:
            self.openai_client = openai.OpenAI(api_key=openai_api_key)
        except Exception as e:
            raise Exception(f"Gagal menginisialisasi klien OpenAI: {str(e)}")
        
        # Set style matplotlib untuk visualisasi yang lebih baik
        plt.style.use('default')
        sns.set_palette("husl")
        plt.rcParams['figure.facecolor'] = 'white'
        plt.rcParams['axes.facecolor'] = 'white'
        
        # Dapatkan informasi skema database
        self.schema_info = self._dapatkan_info_skema()
        
    def _dapatkan_info_skema(self) -> str:
        """Dapatkan informasi skema database yang komprehensif"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Dapatkan semua nama tabel
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            
            schema_info = "=== SKEMA DATABASE CHINOOK ===\n\n"
            
            for table in tables:
                table_name = table[0]
                schema_info += f"📋 Tabel: {table_name}\n"
                
                # Dapatkan info kolom dengan detail
                cursor.execute(f"PRAGMA table_info({table_name});")
                columns = cursor.fetchall()
                
                for col in columns:
                    col_name = col[1]
                    col_type = col[2]
                    not_null = " NOT NULL" if col[3] else ""
                    pk = " PRIMARY KEY" if col[5] else ""
                    schema_info += f"  • {col_name} ({col_type}){not_null}{pk}\n"
                
                # Dapatkan jumlah baris
                cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
                row_count = cursor.fetchone()[0]
                schema_info += f"  📊 Baris: {row_count:,}\n\n"
            
            # Tambahkan informasi relasi
            schema_info += """
=== RELASI KUNCI ===
• Artist (ArtistId) → Album (ArtistId)
• Album (AlbumId) → Track (AlbumId)  
• Track (TrackId) → InvoiceLine (TrackId)
• InvoiceLine (InvoiceId) → Invoice (InvoiceId)
• Invoice (CustomerId) → Customer (CustomerId)
• Customer (SupportRepId) → Employee (EmployeeId)
• Track (GenreId) → Genre (GenreId)
• Track (MediaTypeId) → MediaType (MediaTypeId)
• Playlist ↔ Track (many-to-many via PlaylistTrack)
"""
            
            conn.close()
            return schema_info
            
        except Exception as e:
            return f"Error mendapatkan info skema: {str(e)}"
    
    def eksekusi_query_sql(self, query: str) -> pd.DataFrame:
        """Eksekusi query SQL dan kembalikan hasil sebagai DataFrame"""
        try:
            conn = sqlite3.connect(self.db_path)
            df = pd.read_sql_query(query, conn)
            conn.close()
            return df
        except Exception as e:
            raise Exception(f"Error eksekusi SQL: {str(e)}")
    
    def generate_query_sql(self, pertanyaan_user: str) -> str:
        """Generate query SQL berdasarkan pertanyaan user menggunakan OpenAI"""
        
        system_prompt = f"""Anda adalah seorang ahli SQL yang bekerja dengan database toko musik Chinook.

{self.schema_info}

ATURAN PENTING:
1. Generate HANYA query SQL, tanpa penjelasan atau formatting
2. Gunakan sintaks SQLite yang benar
3. Selalu gunakan aliases tabel untuk kejelasan
4. Sertakan klausa LIMIT yang sesuai untuk hasil besar (default: LIMIT 20)
5. Gunakan fungsi agregat saat ditanya tentang total, jumlah, atau ranking
6. JOIN tabel dengan benar berdasarkan relasi yang ditunjukkan di atas
7. Format nilai monetary dengan tepat
8. Urutkan hasil secara logis (biasanya DESC untuk ranking, ASC untuk nama)

POLA UMUM:
- Untuk query "top/terbaik": ORDER BY [metrik] DESC LIMIT N
- Untuk analisis penjualan: SUM(il.UnitPrice * il.Quantity) 
- Untuk analisis customer: JOIN Customer c ON i.CustomerId = c.CustomerId
- Untuk analisis artist/album: JOIN Artist ar ON al.ArtistId = ar.ArtistId

Kembalikan hanya query SQL, siap untuk dieksekusi."""

        user_prompt = f"Generate query SQL untuk menjawab: {pertanyaan_user}"
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=500
            )
            
            sql_query = response.choices[0].message.content.strip()
            
            # Bersihkan query - hapus formatting markdown jika ada
            sql_query = re.sub(r'```sql\n?', '', sql_query)
            sql_query = re.sub(r'```\n?', '', sql_query)
            sql_query = sql_query.strip()
            
            # Hapus semicolon di akhir jika ada
            if sql_query.endswith(';'):
                sql_query = sql_query[:-1]
            
            return sql_query
            
        except Exception as e:
            raise Exception(f"Error generating query SQL: {str(e)}")
    
    def perlu_buat_visualisasi(self, pertanyaan: str, df: pd.DataFrame) -> bool:
        """Tentukan apakah visualisasi perlu dibuat"""
        # Kata kunci yang menyarankan visualisasi
        kata_kunci_viz = [
            'chart', 'grafik', 'plot', 'visualisasi', 'tampilkan', 'perlihatkan',
            'top', 'teratas', 'terbawah', 'tertinggi', 'terendah', 'paling', 'terbanyak',
            'bandingkan', 'perbandingan', 'tren', 'distribusi', 'penjualan',
            'revenue', 'pendapatan', 'populer', 'terbaik', 'terburuk', 'ranking'
        ]
        
        pertanyaan_lower = pertanyaan.lower()
        ada_kata_viz = any(kata in pertanyaan_lower for kata in kata_kunci_viz)
        
        # Cek apakah data cocok untuk visualisasi
        ada_data_numerik = len(df.select_dtypes(include=['float64', 'int64']).columns) > 0
        ukuran_cocok = 2 <= len(df) <= 50  # Tidak terlalu kecil atau besar
        ada_kategori = len(df.select_dtypes(include=['object']).columns) > 0
        
        return ada_kata_viz and ada_data_numerik and ukuran_cocok
    
    def buat_visualisasi(self, df: pd.DataFrame, pertanyaan: str) -> plt.Figure:
        """Buat visualisasi yang sesuai berdasarkan data dan pertanyaan"""
        try:
            # Setup plot dengan styling yang lebih baik
            fig, ax = plt.subplots(figsize=(12, 6))
            plt.style.use('default')
            
            # Dapatkan tipe kolom
            kolom_numerik = df.select_dtypes(include=['float64', 'int64']).columns.tolist()
            kolom_kategori = df.select_dtypes(include=['object']).columns.tolist()
            
            # Pilih tipe visualisasi berdasarkan struktur data
            if len(kolom_numerik) >= 1 and len(kolom_kategori) >= 1:
                # Bar chart untuk data kategori vs numerik
                self._buat_bar_chart(df, kolom_kategori[0], kolom_numerik[0], ax)
                
            elif len(kolom_numerik) >= 2:
                # Scatter plot untuk dua kolom numerik
                self._buat_scatter_plot(df, kolom_numerik[0], kolom_numerik[1], ax)
                
            elif len(kolom_numerik) == 1:
                # Histogram untuk satu kolom numerik
                self._buat_histogram(df, kolom_numerik[0], ax)
                
            else:
                # Count plot sederhana untuk data kategori
                self._buat_count_plot(df, kolom_kategori[0] if kolom_kategori else df.columns[0], ax)
            
            # Terapkan styling yang konsisten
            plt.tight_layout()
            ax.grid(True, alpha=0.3, linestyle='--')
            
            return fig
            
        except Exception as e:
            st.error(f"Error membuat visualisasi: {str(e)}")
            return None
    
    def _buat_bar_chart(self, df: pd.DataFrame, x_col: str, y_col: str, ax):
        """Buat bar chart dengan styling"""
        # Batasi ke 15 teratas untuk keterbacaan
        if len(df) > 15:
            df_viz = df.nlargest(15, y_col)
        else:
            df_viz = df.copy()
        
        # Buat bar chart dengan warna custom
        colors = plt.cm.Set3(range(len(df_viz)))
        bars = ax.bar(range(len(df_viz)), df_viz[y_col], color=colors, 
                     alpha=0.8, edgecolor='black', linewidth=0.5)
        
        # Kustomisasi chart
        ax.set_title(f'{y_col} berdasarkan {x_col}', fontsize=16, fontweight='bold', pad=20)
        ax.set_xlabel(x_col, fontsize=12, fontweight='semibold')
        ax.set_ylabel(y_col, fontsize=12, fontweight='semibold')
        
        # Set label sumbu x dengan rotasi jika perlu
        labels = [str(label)[:25] + '...' if len(str(label)) > 25 else str(label) 
                 for label in df_viz[x_col]]
        ax.set_xticks(range(len(df_viz)))
        ax.set_xticklabels(labels, rotation=45, ha='right')
        
        # Tambahkan label nilai pada bar
        for i, (bar, value) in enumerate(zip(bars, df_viz[y_col])):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2, height + max(df_viz[y_col])*0.01,
                   f'{value:,.1f}' if isinstance(value, float) else f'{value:,}',
                   ha='center', va='bottom', fontweight='bold', fontsize=9)
    
    def _buat_scatter_plot(self, df: pd.DataFrame, x_col: str, y_col: str, ax):
        """Buat scatter plot dengan styling"""
        scatter = ax.scatter(df[x_col], df[y_col], alpha=0.7, s=60, 
                           c=range(len(df)), cmap='viridis', edgecolors='black', linewidths=0.5)
        ax.set_title(f'{y_col} vs {x_col}', fontsize=16, fontweight='bold', pad=20)
        ax.set_xlabel(x_col, fontsize=12, fontweight='semibold')
        ax.set_ylabel(y_col, fontsize=12, fontweight='semibold')
        plt.colorbar(scatter, ax=ax, label='Indeks Data Point')
    
    def _buat_histogram(self, df: pd.DataFrame, col: str, ax):
        """Buat histogram dengan styling"""
        ax.hist(df[col], bins=min(20, len(df[col].unique())), 
               alpha=0.7, color='skyblue', edgecolor='black', linewidth=1)
        ax.set_title(f'Distribusi {col}', fontsize=16, fontweight='bold', pad=20)
        ax.set_xlabel(col, fontsize=12, fontweight='semibold')
        ax.set_ylabel('Frekuensi', fontsize=12, fontweight='semibold')
    
    def _buat_count_plot(self, df: pd.DataFrame, col: str, ax):
        """Buat count plot untuk data kategori"""
        value_counts = df[col].value_counts().head(15)
        colors = plt.cm.Set2(range(len(value_counts)))
        bars = ax.bar(range(len(value_counts)), value_counts.values, 
                     color=colors, alpha=0.8, edgecolor='black', linewidth=0.5)
        
        ax.set_title(f'Jumlah {col}', fontsize=16, fontweight='bold', pad=20)
        ax.set_xlabel(col, fontsize=12, fontweight='semibold')
        ax.set_ylabel('Jumlah', fontsize=12, fontweight='semibold')
        ax.set_xticks(range(len(value_counts)))
        ax.set_xticklabels(value_counts.index, rotation=45, ha='right')
        
        # Tambahkan label nilai
        for bar, value in zip(bars, value_counts.values):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(value_counts)*0.01,
                   str(value), ha='center', va='bottom', fontweight='bold')
    
    def proses_pertanyaan(self, pertanyaan: str) -> Tuple[str, str, pd.DataFrame, plt.Figure]:
        """Proses pertanyaan user dan kembalikan jawaban, query, data, dan visualisasi"""
        try:
            # Generate dan eksekusi query SQL
            sql_query = self.generate_query_sql(pertanyaan)
            df = self.eksekusi_query_sql(sql_query)
            
            # Format respons teks
            if df.empty:
                response = "❌ Tidak ada hasil yang ditemukan untuk query Anda."
                visualization = None
            else:
                response = self._format_response(df, pertanyaan)
                
                # Buat visualisasi jika sesuai
                if self.perlu_buat_visualisasi(pertanyaan, df):
                    visualization = self.buat_visualisasi(df, pertanyaan)
                else:
                    visualization = None
            
            return response, sql_query, df, visualization
            
        except Exception as e:
            error_msg = f"❌ **Error:** {str(e)}"
            return error_msg, "", pd.DataFrame(), None
    
    def _format_response(self, df: pd.DataFrame, pertanyaan: str) -> str:
        """Format teks respons"""
        response = f"✅ **Hasil Query** ({len(df)} record ditemukan)"
        
        # Tambahkan statistik ringkasan untuk kolom numerik
        kolom_numerik = df.select_dtypes(include=['float64', 'int64']).columns
        if len(kolom_numerik) > 0:
            response += "\n\n📊 **Statistik Ringkasan:**"
            for col in kolom_numerik[:3]:  # Batasi ke 3 kolom numerik pertama
                values = df[col]
                response += f"\n• **{col}:** Total = {values.sum():,.2f}, Rata-rata = {values.mean():.2f}, Maksimum = {values.max():,.2f}"
        
        return response

@st.cache_resource
def inisialisasi_agen(api_key):
    """Inisialisasi agen dengan caching untuk performa"""
    try:
        return AgenDatabaseChinook(DATABASE_PATH, api_key)
    except Exception as e:
        st.error(f"Error inisialisasi agen: {str(e)}")
        return None

def main():
    """Fungsi utama untuk menjalankan aplikasi Streamlit"""
    
    # Konfigurasi halaman
    st.set_page_config(
        page_title="🎵 Agen AI Database Chinook",
        page_icon="🎵",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Header utama
    st.title("🎵 Agen AI Database Chinook")
    st.markdown("**Tanyakan apapun tentang database toko musik Chinook dalam bahasa natural!**")
    
    # Validasi konfigurasi database
    if not os.path.exists(DATABASE_PATH):
        st.error(f"""
        ❌ **File database tidak ditemukan:** `{DATABASE_PATH}`
        
        📥 **Silakan unduh database Chinook:**
        1. Kunjungi: https://www.sqlitetutorial.net/sqlite-sample-database/
        2. Unduh chinook.db
        3. Letakkan di direktori yang sama dengan script ini
        """)
        st.stop()
    
    # Sidebar dengan input API key dan informasi
    with st.sidebar:
        st.header("🔑 Konfigurasi API")
        
        # Input API Key
        api_key = st.text_input(
            "OpenAI API Key:",
            type="password",
            placeholder="Masukkan API key OpenAI Anda",
            help="Dapatkan API key dari https://platform.openai.com/api-keys"
        )
        
        # Validasi API key
        if not api_key:
            st.error("⚠️ **API key OpenAI diperlukan untuk melanjutkan!**")
            st.info("🔑 Silakan masukkan API key OpenAI Anda di atas.")
            st.stop()
        
        # Test koneksi API
        if st.button("🧪 Test Koneksi API"):
            with st.spinner("Testing koneksi..."):
                try:
                    test_client = openai.OpenAI(api_key=api_key)
                    # Test simple completion
                    test_response = test_client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[{"role": "user", "content": "Hello"}],
                        max_tokens=5
                    )
                    st.success("✅ Koneksi API berhasil!")
                except Exception as e:
                    st.error(f"❌ Koneksi API gagal: {str(e)}")
        
        st.markdown("---")
        st.header("📚 Panduan Penggunaan")
        st.header("📚 Panduan Penggunaan")
        
        st.subheader("💡 Tips untuk hasil terbaik:")
        st.markdown("""
        - Gunakan istilah spesifik seperti "10 teratas", "tertinggi", "total penjualan"
        - Minta perbandingan: "bandingkan penjualan berdasarkan genre"
        - Minta visualisasi: "tampilkan chart dari..."
        - Spesifik dalam apa yang ingin dilihat
        """)
        
        st.subheader("🎯 Contoh pertanyaan:")
        contoh_pertanyaan = [
            "Tampilkan 10 artis terlaris berdasarkan total pendapatan",
            "Genre musik apa yang paling populer berdasarkan jumlah track?",
            "Customer mana yang paling banyak berbelanja?",
            "Tampilkan total penjualan berdasarkan negara",
            "Track mana yang paling panjang dalam database?",
            "Karyawan mana yang mengelola customer terbanyak?",
            "Album mana yang paling mahal?",
            "Playlist mana yang memiliki track terbanyak?"
        ]
        
        for i, pertanyaan in enumerate(contoh_pertanyaan, 1):
            if st.button(f"💬 Contoh {i}", key=f"example_{i}", help=pertanyaan):
                st.session_state.pertanyaan_input = pertanyaan
        
        st.markdown("---")
        st.subheader("📊 Database Info")
        st.info("Database meliputi: Artis, Album, Track, Customer, Invoice, Karyawan, Genre, Playlist dan lainnya!")
        
        # Tampilkan info database
        if st.checkbox("🔍 Lihat Skema Database"):
            with st.expander("Skema Database Chinook"):
                st.text(agen.schema_info)
        
        # History query
        st.markdown("---")
        st.subheader("📚 History Query")
        if st.session_state.query_history:
            st.markdown("**Query terakhir yang dijalankan:**")
            
            # Tampilkan 5 query terakhir
            for i, (timestamp, question, query) in enumerate(reversed(st.session_state.query_history[-5:]), 1):
                with st.expander(f"🕐 {timestamp} - {question[:30]}..."):
                    st.code(query, language='sql')
                    if st.button(f"🔄 Jalankan Ulang", key=f"rerun_{i}"):
                        st.session_state.pertanyaan_input = question
                        st.rerun()
        else:
            st.info("Belum ada history query. Mulai bertanya untuk melihat history!")
        
        if st.session_state.query_history:
            if st.button("🗑️ Hapus History"):
                st.session_state.query_history = []
                st.success("History telah dihapus!")
    
    # Inisialisasi agen setelah API key tersedia
    agen = inisialisasi_agen(api_key)
    if agen is None:
        st.stop()
    
    # Area input utama
    st.subheader("💬 Tanyakan Sesuatu")
    
    # Initialize session state untuk input dan history
    if 'pertanyaan_input' not in st.session_state:
        st.session_state.pertanyaan_input = ""
    if 'query_history' not in st.session_state:
        st.session_state.query_history = []
    
    # Input form
    with st.form("form_pertanyaan", clear_on_submit=False):
        pertanyaan = st.text_area(
            "Ketik pertanyaan Anda di sini:",
            value=st.session_state.pertanyaan_input,
            height=100,
            placeholder="Contoh: Tampilkan 10 artis terlaris berdasarkan total pendapatan"
        )
        
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            submit_button = st.form_submit_button("🚀 Tanya", type="primary")
        with col2:
            clear_button = st.form_submit_button("🗑️ Hapus")
    
    # Handle clear button
    if clear_button:
        st.session_state.pertanyaan_input = ""
        st.rerun()
    
    # Proses pertanyaan
    if submit_button and pertanyaan.strip():
        with st.spinner("🤖 Menganalisis pertanyaan dan menghasilkan query..."):
            try:
                response, sql_query, df, visualization = agen.proses_pertanyaan(pertanyaan)
                
                # Simpan ke history
                timestamp = datetime.now().strftime("%H:%M:%S")
                st.session_state.query_history.append((timestamp, pertanyaan, sql_query))
                
                # Reset input
                st.session_state.pertanyaan_input = ""
                
                # Tampilkan hasil
                st.subheader("📋 Hasil Analisis")
                
                # Response text
                st.markdown(response)
                
                # SQL Query yang digunakan - sebagai form output terpisah
                st.subheader("🔍 Query SQL yang Digunakan")
                
                # Container untuk query dengan styling
                query_container = st.container()
                with query_container:
                    # Tampilkan query dalam code block
                    st.code(sql_query, language='sql')
                    
                    # Form untuk copy dan edit query
                    with st.form("form_query_output", clear_on_submit=False):
                        st.markdown("**📝 Edit atau Copy Query:**")
                        
                        # Text area untuk edit query
                        edited_query = st.text_area(
                            "Query SQL (dapat diedit):",
                            value=sql_query,
                            height=120,
                            help="Anda dapat mengedit query ini dan menjalankannya secara manual"
                        )
                        
                        col1, col2, col3 = st.columns([1, 1, 2])
                        with col1:
                            run_edited_query = st.form_submit_button("🏃 Jalankan Query", type="primary")
                        with col2:
                            copy_query = st.form_submit_button("📋 Copy Query")
                        
                        # Info tambahan
                        st.info("💡 **Tips:** Anda dapat mengedit query di atas dan menjalankannya untuk mendapatkan hasil yang berbeda.")
                
                # Handle edited query execution
                if run_edited_query and edited_query.strip():
                    if edited_query.strip() != sql_query.strip():
                        st.markdown("---")
                        st.subheader("🔄 Hasil Query yang Diedit")
                        
                        with st.spinner("🤖 Menjalankan query yang diedit..."):
                            try:
                                edited_df = agen.eksekusi_query_sql(edited_query)
                                
                                if edited_df.empty:
                                    st.warning("⚠️ Query yang diedit tidak menghasilkan data.")
                                else:
                                    st.success(f"✅ Query berhasil dijalankan! ({len(edited_df)} record ditemukan)")
                                    
                                    # Tampilkan data hasil edited query
                                    st.dataframe(edited_df, use_container_width=True)
                                    
                                    # Download button untuk edited query
                                    csv_edited = edited_df.to_csv(index=False)
                                    st.download_button(
                                        label="📥 Download hasil query edit sebagai CSV",
                                        data=csv_edited,
                                        file_name=f"chinook_edited_query_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                        mime="text/csv"
                                    )
                                    
                                    # Cek apakah perlu visualisasi untuk edited query
                                    if agen.perlu_buat_visualisasi("visualisasi hasil edit", edited_df):
                                        st.subheader("📈 Visualisasi Query yang Diedit")
                                        edited_viz = agen.buat_visualisasi(edited_df, "visualisasi hasil edit")
                                        if edited_viz is not None:
                                            st.pyplot(edited_viz)
                                    
                            except Exception as e:
                                st.error(f"❌ Error menjalankan query yang diedit: {str(e)}")
                    else:
                        st.info("💡 Query tidak berubah. Tidak ada yang dijalankan.")
                
                # Handle copy query (show notification)
                if copy_query:
                    st.success("📋 Query telah disalin! Anda dapat paste di SQL editor lain.")
                    # Note: Actual copy to clipboard requires additional JavaScript, 
                    # so we just show the notification
                
                # Tampilkan data jika ada
                if not df.empty:
                    st.subheader("📊 Data Hasil")
                    
                    # Opsi tampilan data
                    col1, col2 = st.columns([3, 1])
                    with col2:
                        show_full = st.checkbox("Tampilkan semua data", value=False)
                    
                    if show_full or len(df) <= 20:
                        st.dataframe(df, use_container_width=True)
                    else:
                        st.dataframe(df.head(10), use_container_width=True)
                        st.info(f"Menampilkan 10 dari {len(df)} baris. Centang 'Tampilkan semua data' untuk melihat semua.")
                    
                    # Download button
                    csv = df.to_csv(index=False)
                    st.download_button(
                        label="📥 Download data sebagai CSV",
                        data=csv,
                        file_name=f"chinook_query_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
                
                # Tampilkan visualisasi jika ada
                if visualization is not None:
                    st.subheader("📈 Visualisasi")
                    st.pyplot(visualization)
                    
                    # Option to download visualization
                    img_buffer = io.BytesIO()
                    visualization.savefig(img_buffer, format='png', dpi=300, bbox_inches='tight')
                    st.download_button(
                        label="📥 Download chart sebagai PNG",
                        data=img_buffer.getvalue(),
                        file_name=f"chinook_chart_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
                        mime="image/png"
                    )
                
            except Exception as e:
                st.error(f"❌ Terjadi kesalahan: {str(e)}")
    
    elif submit_button and not pertanyaan.strip():
        st.warning("⚠️ Silakan masukkan pertanyaan terlebih dahulu.")
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666; margin-top: 2rem;'>
        <p>🎵 Agen AI Database Chinook | Powered by OpenAI & Streamlit</p>
        <p><small>Analisis database toko musik dengan kekuatan AI</small></p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
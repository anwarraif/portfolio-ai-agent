import os
import json
import re
import sys
import io
import contextlib
import warnings
from typing import Optional, List, Any, Tuple
from PIL import Image
import streamlit as st
import pandas as pd
import base64
from io import BytesIO
from together import Together
from e2b_code_interpreter import Sandbox
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.express as px

warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

pattern = re.compile(r"```python\n(.*?)\n```", re.DOTALL)

def code_interpret(e2b_code_interpreter: Sandbox, code: str) -> Optional[List[Any]]:
    with st.spinner('Executing code in E2B sandbox...'):
        # Enhanced code to ensure proper visualization output
        enhanced_code = f"""
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go
import base64
from io import BytesIO

# Set matplotlib backend to Agg for non-interactive plotting
import matplotlib
matplotlib.use('Agg')

# Original user code
{code}

# Auto-save matplotlib figures if any were created
import matplotlib.pyplot as plt
if plt.get_fignums():
    for i, fig_num in enumerate(plt.get_fignums()):
        fig = plt.figure(fig_num)
        buf = BytesIO()
        fig.savefig(buf, format='png', dpi=300, bbox_inches='tight')
        buf.seek(0)
        img_str = base64.b64encode(buf.read()).decode()
        print(f"MATPLOTLIB_PLOT_{{i}}: {{img_str}}")
        buf.close()
        plt.close(fig)
"""
        
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()

        with contextlib.redirect_stdout(stdout_capture), contextlib.redirect_stderr(stderr_capture):
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                exec = e2b_code_interpreter.run_code(enhanced_code)

        stdout_output = stdout_capture.getvalue()
        stderr_output = stderr_capture.getvalue()

        if stderr_output:
            print("[Code Interpreter Warnings/Errors]", file=sys.stderr)
            print(stderr_output, file=sys.stderr)

        if stdout_output:
            print("[Code Interpreter Output]", file=sys.stdout)
            print(stdout_output, file=sys.stdout)

        if exec.error:
            print(f"[Code Interpreter ERROR] {exec.error}", file=sys.stderr)
            return None, stdout_output
        
        return exec.results, stdout_output

def match_code_blocks(llm_response: str) -> str:
    match = pattern.search(llm_response)
    if match:
        code = match.group(1)
        return code
    return ""

def extract_matplotlib_plots(stdout_output: str) -> List[str]:
    """Extract base64 encoded matplotlib plots from stdout"""
    plot_pattern = r"MATPLOTLIB_PLOT_\d+: ([A-Za-z0-9+/=]+)"
    matches = re.findall(plot_pattern, stdout_output)
    return matches

def chat_with_llm(e2b_code_interpreter: Sandbox, user_message: str, dataset_path: str) -> Tuple[Optional[List[Any]], str, List[str]]:
    # Enhanced system prompt for better visualization
    system_prompt = f"""Kamu adalah ilmuwan data Python dan pakar visualisasi data. Kamu diberi kumpulan data di jalur '{dataset_path}' dan juga kueri pengguna.

INSTRUKSI PENTING:
1. Selalu gunakan variabel jalur kumpulan data '{dataset_path}' dalam kode untuk membaca file CSV
2. Untuk visualisasi, gunakan matplotlib, seaborn, atau plotly
3. Jika membuat plot matplotlib/seaborn, pastikan untuk memanggil plt.show() di akhir
4. Jika membuat plot plotly, pastikan untuk memanggil fig.show()
5. Berikan penjelasan singkat tentang visualisasi yang dibuat
6. Jika ada analisis statistik, tampilkan hasilnya dengan jelas

Contoh struktur kode yang baik:
```python
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Baca data
df = pd.read_csv('{dataset_path}')

# Analisis data
print("Dataset Info:")
print(df.info())
print("\\nFirst 5 rows:")
print(df.head())

# Buat visualisasi
plt.figure(figsize=(10, 6))
# ... kode visualisasi ...
plt.title('Judul Grafik')
plt.xlabel('Label X')
plt.ylabel('Label Y')
plt.show()
```"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    with st.spinner('Mendapatkan respons dari model Together AI LLM...'):
        client = Together(api_key=st.session_state.together_api_key)
        response = client.chat.completions.create(
            model=st.session_state.model_name,
            messages=messages,
        )

        response_message = response.choices[0].message
        python_code = match_code_blocks(response_message.content)
        
        if python_code:
            code_interpreter_results, stdout_output = code_interpret(e2b_code_interpreter, python_code)
            matplotlib_plots = extract_matplotlib_plots(stdout_output)
            return code_interpreter_results, response_message.content, matplotlib_plots
        else:
            st.warning("Gagal mencocokkan kode Python dalam respons model")
            return None, response_message.content, []

def upload_dataset(code_interpreter: Sandbox, uploaded_file) -> str:
    dataset_path = f"./{uploaded_file.name}"
    
    try:
        # Convert uploaded file to bytes
        file_bytes = uploaded_file.getvalue()
        code_interpreter.files.write(dataset_path, file_bytes)
        return dataset_path
    except Exception as error:
        st.error(f"Error during file upload: {error}")
        raise error

def display_results(code_results, matplotlib_plots):
    """Display various types of results including visualizations"""
    
    # Display matplotlib plots from stdout
    if matplotlib_plots:
        st.subheader("📊 Visualisasi:")
        for i, plot_data in enumerate(matplotlib_plots):
            try:
                png_data = base64.b64decode(plot_data)
                image = Image.open(BytesIO(png_data))
                st.image(image, caption=f"Visualisasi {i+1}", use_container_width=True)
            except Exception as e:
                st.error(f"Error displaying matplotlib plot {i+1}: {e}")
    
    # Display other results
    if code_results:
        st.subheader("📈 Hasil Analisis:")
        for i, result in enumerate(code_results):
            try:
                if hasattr(result, 'png') and result.png:
                    # E2B PNG results
                    png_data = base64.b64decode(result.png)
                    image = Image.open(BytesIO(png_data))
                    st.image(image, caption=f"Generated Visualization {i+1}", use_container_width=True)
                    
                elif hasattr(result, 'figure'):
                    # Matplotlib figures
                    fig = result.figure
                    st.pyplot(fig)
                    
                elif hasattr(result, 'show'):
                    # Plotly figures
                    st.plotly_chart(result, use_container_width=True)
                    
                elif isinstance(result, (pd.DataFrame, pd.Series)):
                    # Pandas DataFrames/Series
                    st.dataframe(result, use_container_width=True)
                    
                elif isinstance(result, (dict, list)):
                    # JSON-like data
                    st.json(result)
                    
                else:
                    # Other text results
                    st.text(str(result))
                    
            except Exception as e:
                st.error(f"Error displaying result {i+1}: {e}")
                st.text(f"Raw result: {result}")

def main():
    """Main Streamlit application."""
    st.set_page_config(
        page_title="🤖 AI Data Visualization Agent 📊",
        page_icon="📈",
        layout="wide"
    )
    
    st.title("🤖 AI Data Visualization Agent 📊")
    st.markdown("Upload dataset CSV dan ajukan pertanyaan untuk mendapatkan analisis dan visualisasi otomatis!")

    # Initialize session state variables
    if 'together_api_key' not in st.session_state:
        st.session_state.together_api_key = ''
    if 'e2b_api_key' not in st.session_state:
        st.session_state.e2b_api_key = ''
    if 'model_name' not in st.session_state:
        st.session_state.model_name = ''

    with st.sidebar:
        st.header("⚙️ API Key dan Konfigurasi")
        
        st.session_state.together_api_key = st.text_input(
            "🔑 API Key Together AI", 
            type="password",
            help="Masukkan API key dari Together AI"
        )
        st.info("💡 Dapatkan $1 free credit dari Together AI")
        st.markdown("🔗 [Dapatkan API Key Together AI](https://api.together.ai/signin)")
        
        st.session_state.e2b_api_key = st.text_input(
            "🔑 API Key E2B", 
            type="password",
            help="Masukkan API key dari E2B untuk code execution"
        )
        st.markdown("🔗 [Dapatkan API Key E2B](https://e2b.dev/docs/legacy/getting-started/api-key)")
        
        # Model selection
        model_options = {
            "Meta-Llama 3.1 405B": "meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo",
            "DeepSeek V3": "deepseek-ai/DeepSeek-V3",
            "Qwen 2.5 7B": "Qwen/Qwen2.5-7B-Instruct-Turbo",
            "Meta-Llama 3.3 70B": "meta-llama/Llama-3.3-70B-Instruct-Turbo"
        }
        
        selected_model = st.selectbox(
            "🧠 Pilih Model AI",
            options=list(model_options.keys()),
            index=0
        )
        st.session_state.model_name = model_options[selected_model]
        
        st.markdown("---")
        st.markdown("### 📝 Tips Penggunaan:")
        st.markdown("""
        - Upload file CSV dengan data yang ingin dianalisis
        - Ajukan pertanyaan spesifik tentang data
        - Minta visualisasi tertentu (bar chart, line plot, dll)
        - Tanyakan statistik deskriptif atau korelasi
        """)

    # Main content area
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("📤 Upload Dataset")
        uploaded_file = st.file_uploader(
            "Pilih file CSV", 
            type="csv",
            help="Upload file CSV yang ingin dianalisis"
        )
    
    if uploaded_file is not None:
        with col2:
            st.subheader("👀 Preview Dataset")
            df = pd.read_csv(uploaded_file)
            
            # Dataset info
            st.write(f"**Shape:** {df.shape[0]} baris, {df.shape[1]} kolom")
            
            show_full = st.checkbox("Tampilkan dataset lengkap", help="Toggle untuk melihat semua data")
            if show_full:
                st.dataframe(df, use_container_width=True)
            else:
                st.write("**Preview (5 baris pertama):**")
                st.dataframe(df.head(), use_container_width=True)
        
        st.markdown("---")
        
        # Query section
        st.subheader("💬 Tanyakan tentang Data Anda")
        
        # Predefined example questions
        example_questions = [
            "Buatkan visualisasi distribusi dari semua kolom numerik",
            "Tampilkan korelasi antar variabel dalam bentuk heatmap",
            "Buat grafik perbandingan rata-rata untuk setiap kategori",
            "Analisis trend data dan buat line chart",
            "Buat histogram untuk kolom yang paling menarik",
            "Custom question..."
        ]
        
        selected_question = st.selectbox(
            "Atau pilih pertanyaan contoh:",
            options=example_questions,
            index=5
        )
        
        if selected_question == "Custom question...":
            query = st.text_area(
                "Tulis pertanyaan Anda:",
                placeholder="Contoh: Buatkan bar chart untuk membandingkan penjualan per kategori produk",
                height=100
            )
        else:
            query = st.text_area(
                "Edit pertanyaan jika diperlukan:",
                value=selected_question,
                height=100
            )
        
        # Analysis button
        if st.button("🚀 Analisis Data", type="primary", use_container_width=True):
            if not st.session_state.together_api_key or not st.session_state.e2b_api_key:
                st.error("❌ Silakan masukkan kedua API key di sidebar kiri.")
            elif not query.strip():
                st.error("❌ Silakan masukkan pertanyaan tentang data Anda.")
            else:
                try:
                    with Sandbox(api_key=st.session_state.e2b_api_key) as code_interpreter:
                        # Upload dataset
                        dataset_path = upload_dataset(code_interpreter, uploaded_file)
                        
                        # Get analysis and visualizations
                        code_results, llm_response, matplotlib_plots = chat_with_llm(
                            code_interpreter, query, dataset_path
                        )
                        
                        # Display results
                        st.markdown("---")
                        
                        # AI Response
                        st.subheader("🤖 Respons AI:")
                        st.markdown(llm_response)
                        
                        # Display visualizations and results
                        if code_results or matplotlib_plots:
                            display_results(code_results, matplotlib_plots)
                        else:
                            st.warning("⚠️ Tidak ada hasil visualisasi yang dihasilkan. Coba pertanyaan lain atau periksa format data.")
                            
                except Exception as e:
                    st.error(f"❌ Error saat menjalankan analisis: {str(e)}")
                    st.info("💡 Coba dengan pertanyaan yang lebih sederhana atau periksa format data CSV Anda.")

if __name__ == "__main__":
    main()
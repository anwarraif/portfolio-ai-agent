import streamlit as st
import openai
from PIL import Image
import tempfile
import os
import torch
from transformers import BlipProcessor, BlipForConditionalGeneration

st.set_page_config(
    page_title="Agen Investasi",
    page_icon="../../favicon.ico",
    layout="wide"
)

# Sidebar for API key input
with st.sidebar:
    st.header("🔑 API Configuration")
    openai_api_key = st.text_input(
        "OpenAI API Key",
        type="password",
        placeholder="Enter your OpenAI API key here...",
        help="Get your API key from: https://platform.openai.com/api-keys"
    )
    
    if openai_api_key:
        st.success("✅ API Key provided")
        # Set the API key for the session
        os.environ["OPENAI_API_KEY"] = openai_api_key
    else:
        st.warning("⚠️ Please enter your OpenAI API key to continue")
    
    st.markdown("---")
    st.markdown("**Language Settings:**")
    language_option = st.selectbox(
        "Output Language / Bahasa Output:",
        ["🇮🇩 Bahasa Indonesia", "🇺🇸 English"],
        index=0
    )
    
    use_indonesian = language_option == "🇮🇩 Bahasa Indonesia"
    
    st.markdown("---")
    st.markdown("**Installation Requirements:**")
    st.code("""
pip install streamlit
pip install openai
pip install transformers
pip install torch
pip install Pillow
    """, language="bash")
    
    st.markdown("---")
    st.markdown("**Model Information:**")
    st.info("Using BLIP for image captioning + GPT-4 for analysis")

# Inisialisasi model BLIP untuk deskripsi gambar
@st.cache_resource
def initialize_blip():
    processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
    model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")
    return processor, model

def generate_image_caption(image, processor, model):
    """Menghasilkan deskripsi gambar menggunakan BLIP"""
    try:
        inputs = processor(image, return_tensors="pt")
        outputs = model.generate(**inputs)
        caption = processor.decode(outputs[0], skip_special_tokens=True)
        return caption
    except Exception as e:
        return f"Error generating image description: {str(e)}"

def translate_to_indonesian(text, client):
    """Translate English text to Indonesian using OpenAI"""
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{
                "role": "user", 
                "content": f"Translate this English text to natural Indonesian language. Only return the translation, no additional text: {text}"
            }],
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Translation error: {str(e)}"

# Main content area
st.header("Image Analysis & AI Reasoning Tool")

# Check if API key is provided
if not openai_api_key:
    st.error("⚠️ Please enter your OpenAI API key in the sidebar to use this application.")
    st.stop()

# Initialize BLIP model
try:
    with st.spinner("Loading BLIP model..."):
        processor, model = initialize_blip()
    st.success("✅ BLIP model loaded successfully!")
except Exception as e:
    st.error(f"❌ Failed to load BLIP model: {str(e)}")
    st.stop()

# Initialize OpenAI Client
try:
    client = openai.OpenAI(api_key=openai_api_key)
except Exception as e:
    st.error(f"❌ Failed to initialize OpenAI client: {str(e)}")
    st.stop()

if use_indonesian:
    st.write(
        "Upload gambar dan berikan tugas berbasis penalaran untuk Agen AI. "
        "Agen AI akan menganalisis konten gambar dan merespons berdasarkan input."
    )
else:
    st.write(
        "Upload an image and provide reasoning-based tasks for the AI Agent. "
        "The AI Agent will analyze the image content and respond based on your input."
    )

# Upload gambar
upload_label = "📸 Upload Gambar" if use_indonesian else "📸 Upload Image"
uploaded_file = st.file_uploader(upload_label, type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    try:
        # Simpan file sementara
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            temp_path = tmp_file.name

        # Tampilkan gambar yang diupload
        caption_text = "Gambar yang di-upload" if use_indonesian else "Uploaded Image"
        st.image(uploaded_file, caption=caption_text, use_container_width=True)

        # Deskripsikan konten gambar menggunakan BLIP
        image = Image.open(uploaded_file).convert("RGB")
        
        analysis_text = "🔍 Analyzing image content..." if not use_indonesian else "🔍 Menganalisis konten gambar..."
        with st.spinner(analysis_text):
            # Generate English caption first
            english_caption = generate_image_caption(image, processor, model)
            
            # Translate to Indonesian if needed
            if use_indonesian:
                indonesian_caption = translate_to_indonesian(english_caption, client)
                display_caption = indonesian_caption
            else:
                display_caption = english_caption

        description_header = "###Deskripsi Gambar:" if use_indonesian else "###Image Description:"
        st.markdown(description_header)
        st.markdown(f"**{display_caption}**")

        # Input tugas/pertanyaan dari pengguna
        if use_indonesian:
            task_placeholder = "Misalnya: 'Apa maksud dari gambar ini?' atau 'Jelaskan konteks gambar ini.'"
            task_label = "📝 Masukkan tugas/pertanyaan Anda untuk Agen AI:"
            task_help = "Anda dapat bertanya tentang konten gambar dan mendapatkan analisis bertenaga AI"
        else:
            task_placeholder = "For example: 'What is the meaning of this image?' or 'Explain the context of this image.'"
            task_label = "📝 Enter your task/question for the AI Agent:"
            task_help = "You can ask questions about the image content and get AI-powered analysis"
            
        task_input = st.text_area(
            task_label,
            placeholder=task_placeholder,
            help=task_help
        )

        button_text = "Analisis Gambar" if use_indonesian else "Analyze Image"
        if st.button(button_text) and task_input:
            if not task_input:
                warning_text = "Silakan masukkan pertanyaan Anda." if use_indonesian else "Please enter your question."
                st.warning(warning_text)
            else:
                try:
                    spinner_text = "AI sedang berpikir..." if use_indonesian else "AI is thinking..."
                    with st.spinner(spinner_text):
                        # Prepare prompt in the selected language
                        if use_indonesian:
                            prompt = f"""
                            Berikut adalah deskripsi gambar:
                            "{display_caption}"

                            Tugas:
                            {task_input}

                            Instruksi kepada AI:
                            1. Analisis deskripsi gambar di atas dan hubungkan dengan tugas yang diberikan.
                            2. Berikan jawaban yang terstruktur dan informatif dalam bahasa Indonesia.
                            3. Jika perlu, berikan penjelasan tambahan yang relevan.
                            4. Fokus pada informasi praktis dan actionable.
                            5. Pastikan semua respons dalam bahasa Indonesia yang natural dan mudah dipahami.
                            """
                        else:
                            prompt = f"""
                            Here is the image description:
                            "{display_caption}"

                            Task:
                            {task_input}

                            Instructions for AI:
                            1. Analyze the image description above and connect it with the given task.
                            2. Provide a structured and informative answer in English.
                            3. If necessary, provide additional relevant explanations.
                            4. Focus on practical and actionable information.
                            """

                        # Panggil OpenAI API
                        response = client.chat.completions.create(
                            model="gpt-4",
                            messages=[{"role": "user", "content": prompt}],
                            temperature=0.7,
                        )

                        # Ambil respons AI
                        result = response.choices[0].message.content.strip()

                        # Tampilkan respons dari AI
                        results_header = "Hasil Analisis" if use_indonesian else "Analysis Results"
                        st.subheader(results_header)
                        
                        # Display image description
                        desc_header = "Deskripsi Gambar" if use_indonesian else "Image Description"
                        with st.expander(desc_header, expanded=True):
                            blip_label = "**Analisis Model BLIP:**" if use_indonesian else "**BLIP Model Analysis:**"
                            st.markdown(f"{blip_label} {display_caption}")
                            
                            # Show original English caption if Indonesian is selected
                            if use_indonesian:
                                st.markdown(f"**Original (English):** {english_caption}")
                        
                        # Display AI reasoning
                        reasoning_header = "Penalaran & Respons AI" if use_indonesian else "AI Reasoning & Response"
                        with st.expander(reasoning_header, expanded=True):
                            st.markdown(result)

                except Exception as e:
                    error_text = f"⚠️ Terjadi kesalahan selama analisis: {str(e)}" if use_indonesian else f"⚠️ An error occurred during analysis: {str(e)}"
                    st.error(error_text)
                finally:
                    # Hapus file sementara
                    if os.path.exists(temp_path):
                        os.unlink(temp_path)

    except Exception as e:
        error_text = f"⚠️ Terjadi kesalahan saat memproses gambar: {str(e)}" if use_indonesian else f"⚠️ An error occurred while processing the image: {str(e)}"
        st.error(error_text)
else:
    info_text = "Silakan upload gambar untuk memulai analisis." if use_indonesian else "Please upload an image to begin analysis."
    st.info(info_text)

st.markdown("""
    <style>
    .stTextArea textarea {
        height: 100px;
    }
    </style>
    """, unsafe_allow_html=True)
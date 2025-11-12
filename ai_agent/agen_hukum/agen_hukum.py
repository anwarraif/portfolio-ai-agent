import streamlit as st
from phi.agent import Agent
from phi.knowledge.pdf import PDFKnowledgeBase, PDFReader
from phi.vectordb.qdrant import Qdrant
from phi.tools.duckduckgo import DuckDuckGo
from phi.model.openai import OpenAIChat
from phi.embedder.openai import OpenAIEmbedder
import tempfile
import os
import requests

st.set_page_config(
    page_title="Analisis Dokumen Hukum",
    page_icon="favicon.ico",
    layout="wide"
)

def init_session_state():
    """Inisialisasi variabel session state"""
    if 'openai_api_key' not in st.session_state:
        st.session_state.openai_api_key = None
    if 'qdrant_api_key' not in st.session_state:
        st.session_state.qdrant_api_key = None
    if 'qdrant_url' not in st.session_state:
        st.session_state.qdrant_url = None
    if 'vector_db' not in st.session_state:
        st.session_state.vector_db = None
    if 'legal_team' not in st.session_state:
        st.session_state.legal_team = None
    if 'knowledge_base' not in st.session_state:
        st.session_state.knowledge_base = None
    if 'language' not in st.session_state:
        st.session_state.language = "Indonesia"

def validate_qdrant_connection(url, api_key):
    """Validasi koneksi Qdrant sebelum inisialisasi"""
    try:
        # Bersihkan URL dan siapkan untuk testing
        clean_url = url.rstrip('/')
        if not clean_url.startswith(('http://', 'https://')):
            clean_url = f"https://{clean_url}"
        
        # Test berbagai format endpoint
        test_endpoints = [
            f"{clean_url}/collections",
            f"{clean_url}/api/collections",
            f"{clean_url}",
        ]
        
        headers = {
            'api-key': api_key,
            'Content-Type': 'application/json'
        }
        
        for endpoint in test_endpoints:
            try:
                response = requests.get(endpoint, headers=headers, timeout=10)
                if response.status_code in [200, 401]:  # 200 = sukses, 401 = masalah auth tapi endpoint ada
                    return True, f"Koneksi berhasil ke {endpoint}"
                elif response.status_code == 404:
                    continue
                else:
                    return False, f"HTTP {response.status_code}: {response.text}"
            except requests.exceptions.RequestException as e:
                continue
        
        return False, "Semua endpoint mengembalikan 404. Silakan periksa format URL Qdrant Anda."
        
    except Exception as e:
        return False, f"Error validasi koneksi: {str(e)}"

def init_qdrant():
    """Inisialisasi database vektor Qdrant dengan validasi"""
    if not st.session_state.qdrant_api_key:
        raise ValueError("API key Qdrant tidak disediakan")
    if not st.session_state.qdrant_url:
        raise ValueError("URL Qdrant tidak disediakan")
    
    # Validasi koneksi terlebih dahulu
    is_valid, message = validate_qdrant_connection(
        st.session_state.qdrant_url, 
        st.session_state.qdrant_api_key
    )
    
    if not is_valid:
        raise ValueError(f"Koneksi Qdrant gagal: {message}")
    
    try:
        # Bersihkan URL untuk inisialisasi Qdrant
        clean_url = st.session_state.qdrant_url.rstrip('/')
        if not clean_url.startswith(('http://', 'https://')):
            clean_url = f"https://{clean_url}"
        
        return Qdrant(          
            collection="legal_knowledge",
            url=clean_url,
            api_key=st.session_state.qdrant_api_key,
            https=True,
            timeout=30,
            distance="cosine"
        )
    except Exception as e:
        raise ValueError(f"Gagal inisialisasi Qdrant: {str(e)}")

def process_document(uploaded_file, vector_db: Qdrant):
    """Proses dokumen, buat embedding dan simpan di database vektor Qdrant"""
    if not st.session_state.openai_api_key:
        raise ValueError("API key OpenAI tidak disediakan")
        
    os.environ['OPENAI_API_KEY'] = st.session_state.openai_api_key
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_file_path = os.path.join(temp_dir, uploaded_file.name)
        with open(temp_file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        try:
            embedder = OpenAIEmbedder(
                model="text-embedding-3-small",
                api_key=st.session_state.openai_api_key
            )
            
            # Buat knowledge base dengan konfigurasi Qdrant eksplisit
            knowledge_base = PDFKnowledgeBase(
                path=temp_dir, 
                vector_db=vector_db, 
                reader=PDFReader(chunk=True),
                embedder=embedder,
                recreate_vector_db=False  # Ubah ke False untuk menghindari masalah recreasi
            )
            knowledge_base.load()     
            return knowledge_base      
        except Exception as e:
            raise Exception(f"Error memproses dokumen: {str(e)}")

def create_legal_agents(knowledge_base):
    """Buat dan kembalikan agen-agen hukum"""
    use_indonesian = st.session_state.language == "Indonesia"
    
    if use_indonesian:
        legal_researcher = Agent(
            name="Peneliti Hukum",
            role="Spesialis penelitian hukum",
            model=OpenAIChat(model="gpt-4o"),
            tools=[DuckDuckGo()],
            knowledge=knowledge_base,
            search_knowledge=True,
            instructions=[
                "Temukan dan kutip kasus hukum dan preseden yang relevan",
                "Berikan ringkasan penelitian detail dengan sumber",
                "Referensikan bagian spesifik dari dokumen yang diunggah",
                "Selalu cari knowledge base untuk informasi yang relevan",
                "Berikan respons dalam bahasa Indonesia yang natural dan profesional"
            ],
            show_tool_calls=True,
            markdown=True
        )

        contract_analyst = Agent(
            name="Analis Kontrak",
            role="Spesialis analisis kontrak",
            model=OpenAIChat(model="gpt-4o"),
            knowledge=knowledge_base,
            search_knowledge=True,
            instructions=[
                "Tinjau kontrak secara menyeluruh",
                "Identifikasi ketentuan kunci dan masalah potensial",
                "Referensikan klausul spesifik dari dokumen",
                "Berikan respons dalam bahasa Indonesia yang natural dan profesional"
            ],
            markdown=True
        )

        legal_strategist = Agent(
            name="Ahli Strategi Hukum", 
            role="Spesialis strategi hukum",
            model=OpenAIChat(model="gpt-4o"),
            knowledge=knowledge_base,
            search_knowledge=True,
            instructions=[
                "Kembangkan strategi hukum yang komprehensif",
                "Berikan rekomendasi yang dapat ditindaklanjuti",
                "Pertimbangkan baik risiko maupun peluang",
                "Berikan respons dalam bahasa Indonesia yang natural dan profesional"
            ],
            markdown=True
        )

        # Tim Agen Hukum
        legal_team = Agent(
            name="Pemimpin Tim Hukum",
            role="Koordinator tim hukum",
            model=OpenAIChat(model="gpt-4o"),
            team=[legal_researcher, contract_analyst, legal_strategist],
            knowledge=knowledge_base,
            search_knowledge=True,
            instructions=[
                "Koordinasikan analisis antar anggota tim",
                "Berikan respons yang komprehensif",
                "Pastikan semua rekomendasi disertai sumber yang tepat",
                "Referensikan bagian spesifik dari dokumen yang diunggah",
                "Selalu cari knowledge base sebelum mendelegasikan tugas",
                "Berikan respons dalam bahasa Indonesia yang natural dan profesional"
            ],
            show_tool_calls=True,
            markdown=True
        )
    else:
        legal_researcher = Agent(
            name="Legal Researcher",
            role="Legal research specialist",
            model=OpenAIChat(model="gpt-4o"),
            tools=[DuckDuckGo()],
            knowledge=knowledge_base,
            search_knowledge=True,
            instructions=[
                "Find and cite relevant legal cases and precedents",
                "Provide detailed research summaries with sources",
                "Reference specific sections from the uploaded document",
                "Always search the knowledge base for relevant information"
            ],
            show_tool_calls=True,
            markdown=True
        )

        contract_analyst = Agent(
            name="Contract Analyst",
            role="Contract analysis specialist",
            model=OpenAIChat(model="gpt-4o"),
            knowledge=knowledge_base,
            search_knowledge=True,
            instructions=[
                "Review contracts thoroughly",
                "Identify key terms and potential issues",
                "Reference specific clauses from the document"
            ],
            markdown=True
        )

        legal_strategist = Agent(
            name="Legal Strategist", 
            role="Legal strategy specialist",
            model=OpenAIChat(model="gpt-4o"),
            knowledge=knowledge_base,
            search_knowledge=True,
            instructions=[
                "Develop comprehensive legal strategies",
                "Provide actionable recommendations",
                "Consider both risks and opportunities"
            ],
            markdown=True
        )

        # Legal Agent Team
        legal_team = Agent(
            name="Legal Team Lead",
            role="Legal team coordinator",
            model=OpenAIChat(model="gpt-4o"),
            team=[legal_researcher, contract_analyst, legal_strategist],
            knowledge=knowledge_base,
            search_knowledge=True,
            instructions=[
                "Coordinate analysis between team members",
                "Provide comprehensive responses",
                "Ensure all recommendations are properly sourced",
                "Reference specific parts of the uploaded document",
                "Always search the knowledge base before delegating tasks"
            ],
            show_tool_calls=True,
            markdown=True
        )
    
    return legal_team

def main():
    init_session_state()

    with st.sidebar:
        # Language selection at top of sidebar
        language = st.selectbox(
            "Pilih Bahasa / Select Language",
            ["Indonesia", "English"],
            index=0 if st.session_state.language == "Indonesia" else 1
        )
        st.session_state.language = language
        use_indonesian = language == "Indonesia"
        
        st.divider()

    # Main title based on language
    if use_indonesian:
        st.title("Tim Agen AI Hukum")
    else:
        st.title("AI Legal Agent Team")

    with st.sidebar:
        if use_indonesian:
            st.header("Konfigurasi API")
        else:
            st.header("API Configuration")
   
        openai_key = st.text_input(
            "OpenAI API Key",
            type="password",
            value=st.session_state.openai_api_key if st.session_state.openai_api_key else "",
            help="Masukkan API key OpenAI Anda" if use_indonesian else "Enter your OpenAI API key"
        )
        if openai_key:
            st.session_state.openai_api_key = openai_key

        qdrant_key = st.text_input(
            "Qdrant API Key",
            type="password",
            value=st.session_state.qdrant_api_key if st.session_state.qdrant_api_key else "",
            help="Masukkan API key Qdrant Anda" if use_indonesian else "Enter your Qdrant API key"
        )
        if qdrant_key:
            st.session_state.qdrant_api_key = qdrant_key

        # Qdrant URL dengan default dan help yang lebih baik
        qdrant_url = st.text_input(
            "Qdrant URL",
            value=st.session_state.qdrant_url if st.session_state.qdrant_url else "",
            placeholder="https://your-cluster.qdrant.io:6333",
            help="Masukkan URL instance Qdrant Anda (sertakan https:// dan port jika diperlukan)" if use_indonesian else "Enter your Qdrant instance URL (include https:// and port if needed)"
        )
        if qdrant_url:
            st.session_state.qdrant_url = qdrant_url

        # Test koneksi Qdrant
        if st.session_state.qdrant_api_key and st.session_state.qdrant_url:
            button_text = "Test Koneksi Qdrant" if use_indonesian else "Test Qdrant Connection"
            if st.button(button_text):
                spinner_text = "Menguji koneksi..." if use_indonesian else "Testing connection..."
                with st.spinner(spinner_text):
                    is_valid, message = validate_qdrant_connection(
                        st.session_state.qdrant_url,
                        st.session_state.qdrant_api_key
                    )
                    if is_valid:
                        st.success(f"Berhasil: {message}" if use_indonesian else f"Success: {message}")
                    else:
                        st.error(f"Gagal: {message}" if use_indonesian else f"Failed: {message}")
                        if use_indonesian:
                            st.info("""
                            Format URL umum:
                            - https://your-cluster.qdrant.io:6333
                            - https://your-cluster.us-east-1.aws.qdrant.io:6333
                            - http://localhost:6333 (untuk lokal)
                            """)
                        else:
                            st.info("""
                            Common URL formats:
                            - https://your-cluster.qdrant.io:6333
                            - https://your-cluster.us-east-1.aws.qdrant.io:6333
                            - http://localhost:6333 (for local)
                            """)

        # Inisialisasi Qdrant jika kredensial disediakan
        if all([st.session_state.qdrant_api_key, st.session_state.qdrant_url]):
            if not st.session_state.vector_db:
                try:
                    spinner_text = "Menghubungkan ke Qdrant..." if use_indonesian else "Connecting to Qdrant..."
                    with st.spinner(spinner_text):
                        st.session_state.vector_db = init_qdrant()
                        success_text = "Berhasil terhubung ke Qdrant!" if use_indonesian else "Successfully connected to Qdrant!"
                        st.success(success_text)
                except Exception as e:
                    error_text = f"Gagal terhubung ke Qdrant: {str(e)}" if use_indonesian else f"Failed to connect to Qdrant: {str(e)}"
                    st.error(error_text)
                    info_text = "Silakan periksa format URL dan API key Anda" if use_indonesian else "Please check your URL format and API key"
                    st.info(info_text)

        st.divider()

        # Bagian upload dokumen
        if all([st.session_state.openai_api_key, st.session_state.vector_db]):
            header_text = "Upload Dokumen" if use_indonesian else "Document Upload"
            st.header(header_text)
            
            label_text = "Upload Dokumen Hukum" if use_indonesian else "Upload Legal Document"
            uploaded_file = st.file_uploader(label_text, type=['pdf'])
            
            if uploaded_file:
                button_text = "Proses Dokumen" if use_indonesian else "Process Document"
                if st.button(button_text):
                    spinner_text = "Memproses dokumen..." if use_indonesian else "Processing document..."
                    with st.spinner(spinner_text):
                        try:
                            knowledge_base = process_document(uploaded_file, st.session_state.vector_db)
                            st.session_state.knowledge_base = knowledge_base
                            
                            # Inisialisasi agen
                            st.session_state.legal_team = create_legal_agents(knowledge_base)
                            
                            success_text = "Dokumen berhasil diproses dan tim diinisialisasi!" if use_indonesian else "Document processed and team initialized!"
                            st.success(success_text)
                                
                        except Exception as e:
                            error_text = f"Error memproses dokumen: {str(e)}" if use_indonesian else f"Error processing document: {str(e)}"
                            st.error(error_text)
                            info_text = "Silakan periksa koneksi Qdrant Anda dan coba lagi" if use_indonesian else "Please check your Qdrant connection and try again"
                            st.info(info_text)

            st.divider()
            header_text = "Opsi Analisis" if use_indonesian else "Analysis Options"
            st.header(header_text)
            
            if use_indonesian:
                analysis_options = [
                    "Tinjauan Kontrak",
                    "Penelitian Hukum", 
                    "Penilaian Risiko",
                    "Pemeriksaan Kepatuhan",
                    "Pertanyaan Khusus"
                ]
            else:
                analysis_options = [
                    "Contract Review",
                    "Legal Research",
                    "Risk Assessment", 
                    "Compliance Check",
                    "Custom Query"
                ]
                
            label_text = "Pilih Jenis Analisis" if use_indonesian else "Select Analysis Type"
            analysis_type = st.selectbox(label_text, analysis_options)
        else:
            warning_text = "Silakan konfigurasi semua kredensial API untuk melanjutkan" if use_indonesian else "Please configure all API credentials to proceed"
            st.warning(warning_text)

    # Area konten utama
    if not all([st.session_state.openai_api_key, st.session_state.vector_db]):
        info_text = "Silakan konfigurasi kredensial API Anda di sidebar untuk memulai" if use_indonesian else "Please configure your API credentials in the sidebar to begin"
        st.info(info_text)
    elif not st.session_state.knowledge_base:
        info_text = "Silakan upload dan proses dokumen hukum untuk memulai analisis" if use_indonesian else "Please upload and process a legal document to begin analysis"
        st.info(info_text)
    elif st.session_state.legal_team:
        # Konfigurasi analisis
        if use_indonesian:
            analysis_configs = {
                "Tinjauan Kontrak": {
                    "query": "Tinjau kontrak ini dan identifikasi ketentuan kunci, kewajiban, dan masalah potensial.",
                    "agents": ["Analis Kontrak"],
                    "description": "Analisis kontrak detail yang berfokus pada ketentuan dan kewajiban"
                },
                "Penelitian Hukum": {
                    "query": "Teliti kasus dan preseden yang relevan terkait dokumen ini.",
                    "agents": ["Peneliti Hukum"],
                    "description": "Penelitian tentang kasus hukum dan preseden yang relevan"
                },
                "Penilaian Risiko": {
                    "query": "Analisis risiko hukum potensial dan kewajiban dalam dokumen ini.",
                    "agents": ["Analis Kontrak", "Ahli Strategi Hukum"],
                    "description": "Analisis risiko gabungan dan penilaian strategis"
                },
                "Pemeriksaan Kepatuhan": {
                    "query": "Periksa dokumen ini untuk masalah kepatuhan regulasi.",
                    "agents": ["Peneliti Hukum", "Analis Kontrak", "Ahli Strategi Hukum"],
                    "description": "Analisis kepatuhan komprehensif"
                },
                "Pertanyaan Khusus": {
                    "query": None,
                    "agents": ["Peneliti Hukum", "Analis Kontrak", "Ahli Strategi Hukum"],
                    "description": "Analisis khusus menggunakan semua agen yang tersedia"
                }
            }
        else:
            analysis_configs = {
                "Contract Review": {
                    "query": "Review this contract and identify key terms, obligations, and potential issues.",
                    "agents": ["Contract Analyst"],
                    "description": "Detailed contract analysis focusing on terms and obligations"
                },
                "Legal Research": {
                    "query": "Research relevant cases and precedents related to this document.",
                    "agents": ["Legal Researcher"],
                    "description": "Research on relevant legal cases and precedents"
                },
                "Risk Assessment": {
                    "query": "Analyze potential legal risks and liabilities in this document.",
                    "agents": ["Contract Analyst", "Legal Strategist"],
                    "description": "Combined risk analysis and strategic assessment"
                },
                "Compliance Check": {
                    "query": "Check this document for regulatory compliance issues.",
                    "agents": ["Legal Researcher", "Contract Analyst", "Legal Strategist"],
                    "description": "Comprehensive compliance analysis"
                },
                "Custom Query": {
                    "query": None,
                    "agents": ["Legal Researcher", "Contract Analyst", "Legal Strategist"],
                    "description": "Custom analysis using all available agents"
                }
            }

        st.header(f"Analisis {analysis_type}" if use_indonesian else f"{analysis_type} Analysis")
        st.info(f"Deskripsi: {analysis_configs[analysis_type]['description']}" if use_indonesian else f"Description: {analysis_configs[analysis_type]['description']}")
        
        agents_text = "Agen AI Hukum Aktif" if use_indonesian else "Active Legal AI Agents"
        st.write(f"{agents_text}: {', '.join(analysis_configs[analysis_type]['agents'])}")

        # Bagian query pengguna
        custom_query_text = "Pertanyaan Khusus" if use_indonesian else "Custom Query"
        if analysis_type == custom_query_text:
            label_text = "Masukkan pertanyaan spesifik Anda:" if use_indonesian else "Enter your specific query:"
            help_text = "Tambahkan pertanyaan atau poin spesifik yang ingin Anda analisis" if use_indonesian else "Add any specific questions or points you want to analyze"
            user_query = st.text_area(label_text, help=help_text)
        else:
            user_query = None

        button_text = "Analisis Dokumen" if use_indonesian else "Analyze Document"
        if st.button(button_text):
            if analysis_type == custom_query_text and not user_query:
                warning_text = "Silakan masukkan pertanyaan" if use_indonesian else "Please enter a query"
                st.warning(warning_text)
            else:
                spinner_text = "Menganalisis dokumen..." if use_indonesian else "Analyzing document..."
                with st.spinner(spinner_text):
                    try:
                        # Pastikan API key OpenAI diset
                        os.environ['OPENAI_API_KEY'] = st.session_state.openai_api_key
                        
                        # Gabungkan query predefinisi dan pengguna
                        if analysis_type != custom_query_text:
                            if use_indonesian:
                                combined_query = f"""
                                Menggunakan dokumen yang diunggah sebagai referensi:
                                
                                Tugas Analisis Utama: {analysis_configs[analysis_type]['query']}
                                Area Fokus: {', '.join(analysis_configs[analysis_type]['agents'])}
                                
                                Silakan cari knowledge base dan berikan referensi spesifik dari dokumen.
                                Berikan respons dalam bahasa Indonesia yang natural dan profesional.
                                """
                            else:
                                combined_query = f"""
                                Using the uploaded document as reference:
                                
                                Primary Analysis Task: {analysis_configs[analysis_type]['query']}
                                Focus Areas: {', '.join(analysis_configs[analysis_type]['agents'])}
                                
                                Please search the knowledge base and provide specific references from the document.
                                """
                        else:
                            if use_indonesian:
                                combined_query = f"""
                                Menggunakan dokumen yang diunggah sebagai referensi:
                                
                                {user_query}
                                
                                Silakan cari knowledge base dan berikan referensi spesifik dari dokumen.
                                Area Fokus: {', '.join(analysis_configs[analysis_type]['agents'])}
                                Berikan respons dalam bahasa Indonesia yang natural dan profesional.
                                """
                            else:
                                combined_query = f"""
                                Using the uploaded document as reference:
                                
                                {user_query}
                                
                                Please search the knowledge base and provide specific references from the document.
                                Focus Areas: {', '.join(analysis_configs[analysis_type]['agents'])}
                                """

                        response = st.session_state.legal_team.run(combined_query)
                        
                        # Tampilkan hasil dalam tab
                        if use_indonesian:
                            tab_labels = ["Analisis", "Poin Kunci", "Rekomendasi"]
                        else:
                            tab_labels = ["Analysis", "Key Points", "Recommendations"]
                        
                        tabs = st.tabs(tab_labels)
                        
                        with tabs[0]:
                            header_text = "### Analisis Detail" if use_indonesian else "### Detailed Analysis"
                            st.markdown(header_text)
                            if response.content:
                                st.markdown(response.content)
                            else:
                                for message in response.messages:
                                    if message.role == 'assistant' and message.content:
                                        st.markdown(message.content)
                        
                        with tabs[1]:
                            header_text = "### Poin Kunci" if use_indonesian else "### Key Points"
                            st.markdown(header_text)
                            
                            if use_indonesian:
                                key_points_prompt = f"""Berdasarkan analisis sebelumnya:    
                                {response.content}
                                
                                Silakan ringkas poin-poin kunci dalam bentuk bullet points.
                                Fokus pada wawasan dari: {', '.join(analysis_configs[analysis_type]['agents'])}
                                Berikan respons dalam bahasa Indonesia yang natural dan profesional."""
                            else:
                                key_points_prompt = f"""Based on this previous analysis:    
                                {response.content}
                                
                                Please summarize the key points in bullet points.
                                Focus on insights from: {', '.join(analysis_configs[analysis_type]['agents'])}"""
                            
                            key_points_response = st.session_state.legal_team.run(key_points_prompt)
                            if key_points_response.content:
                                st.markdown(key_points_response.content)
                            else:
                                for message in key_points_response.messages:
                                    if message.role == 'assistant' and message.content:
                                        st.markdown(message.content)
                        
                        with tabs[2]:
                            header_text = "### Rekomendasi" if use_indonesian else "### Recommendations"
                            st.markdown(header_text)
                            
                            if use_indonesian:
                                recommendations_prompt = f"""Berdasarkan analisis sebelumnya:
                                {response.content}
                                
                                Apa rekomendasi kunci Anda berdasarkan analisis, langkah terbaik yang harus diambil?
                                Berikan rekomendasi spesifik dari: {', '.join(analysis_configs[analysis_type]['agents'])}
                                Berikan respons dalam bahasa Indonesia yang natural dan profesional."""
                            else:
                                recommendations_prompt = f"""Based on this previous analysis:
                                {response.content}
                                
                                What are your key recommendations based on the analysis, the best course of action?
                                Provide specific recommendations from: {', '.join(analysis_configs[analysis_type]['agents'])}"""
                            
                            recommendations_response = st.session_state.legal_team.run(recommendations_prompt)
                            if recommendations_response.content:
                                st.markdown(recommendations_response.content)
                            else:
                                for message in recommendations_response.messages:
                                    if message.role == 'assistant' and message.content:
                                        st.markdown(message.content)

                    except Exception as e:
                        error_text = f"Error selama analisis: {str(e)}" if use_indonesian else f"Error during analysis: {str(e)}"
                        st.error(error_text)
    else:
        info_text = "Silakan upload dokumen hukum untuk memulai analisis" if use_indonesian else "Please upload a legal document to begin analysis"
        st.info(info_text)

if __name__ == "__main__":
    main()
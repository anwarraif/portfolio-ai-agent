from typing import List, Literal, Dict, Optional
from agency_swarm import Agent, Agency, set_openai_key, BaseTool
from pydantic import Field, BaseModel
import streamlit as st

class AnalyzeProjectRequirements(BaseTool):
    project_name: str = Field(..., description="Nama Proyek")
    project_description: str = Field(..., description="Deskripsi dan tujuan proyek")
    project_type: Literal["Aplikasi Web", "Aplikasi Mobile", "Pengembangan API", 
                         "Analisis Data", "Solusi AI/ML", "Lainnya"] = Field(..., 
                         description="Jenis proyek")
    budget_range: Literal["Rp150jt-Rp375jt", "Rp375jt-Rp750jt", "Rp750jt-Rp1.5M", "Rp1.5M+"] = Field(..., 
                         description="Rentang anggaran untuk proyek")

    class ToolConfig:
        name = "analisis_proyek"
        description = "Menganalisis kebutuhan dan kelayakan proyek"
        one_call_at_a_time = True

    def run(self) -> str:
        """Menganalisis proyek dan menyimpan hasil dalam shared state"""
        if self._shared_state.get("analisis_proyek", None) is not None:
            raise ValueError("Analisis proyek sudah ada. Silakan lanjut ke spesifikasi teknis.")
        
        analysis = {
            "nama": self.project_name,
            "jenis": self.project_type,
            "kompleksitas": "tinggi",
            "jangka_waktu": "6 bulan",
            "kelayakan_anggaran": "sesuai rentang",
            "kebutuhan": ["Arsitektur yang dapat diskalakan", "Keamanan", "Integrasi API"]
        }
        
        self._shared_state.set("analisis_proyek", analysis)
        return "Analisis proyek selesai. Silakan lanjut ke spesifikasi teknis."

class CreateTechnicalSpecification(BaseTool):
    architecture_type: Literal["monolithic", "microservices", "serverless", "hybrid"] = Field(
        ..., 
        description="Jenis arsitektur yang diusulkan"
    )
    core_technologies: str = Field(
        ..., 
        description="Daftar teknologi dan framework utama (dipisahkan dengan koma)"
    )
    scalability_requirements: Literal["tinggi", "sedang", "rendah"] = Field(
        ..., 
        description="Kebutuhan skalabilitas"
    )

    class ToolConfig:
        name = "buat_spesifikasi_teknis"
        description = "Membuat spesifikasi teknis berdasarkan analisis proyek"
        one_call_at_a_time = True

    def run(self) -> str:
        """Membuat spesifikasi teknis berdasarkan analisis"""
        analisis_proyek = self._shared_state.get("analisis_proyek", None)
        if analisis_proyek is None:
            raise ValueError("Silakan analisis kebutuhan proyek terlebih dahulu menggunakan tool AnalyzeProjectRequirements.")
        
        spec = {
            "nama_proyek": analisis_proyek["name"],
            "arsitektur": self.architecture_type,
            "teknologi": self.core_technologies.split(","),
            "skalabilitas": self.scalability_requirements
        }
        
        self._shared_state.set("spesifikasi_teknis", spec)
        return f"Spesifikasi teknis telah dibuat untuk {analisis_proyek['name']}."

def init_session_state() -> None:
    """Initialize session state variables"""
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    if 'api_key' not in st.session_state:
        st.session_state.api_key = None

def main() -> None:
    # st.set_page_config(page_title="AI Services Agency", layout="wide")
    st.set_page_config(
        page_title="AI Services Agency",
        page_icon="../../favicon.ico",
        layout="wide"
    )    
    
    st.title("🤖 AI Services Agency")
    init_session_state()
    
    # API Configuration
    with st.sidebar:
        st.header("🔑 Konfihurasi API")
        openai_api_key = st.text_input(
            "OpenAI API Key",
            type="password",
            help="Masukan API Key OpenAI untuk melanjutkan."
        )

        if openai_api_key:
            st.session_state.api_key = openai_api_key
            st.success("API Key diterima!")
        else:
            st.warning("⚠️ Silakan masukkan Kunci API OpenAI Anda untuk melanjutkan")
            st.markdown("[Dapatkan kunci API di sini](https://platform.openai.com/api-keys)")
            return
        
    # Initialize agents with the provided API key
    set_openai_key(st.session_state.api_key)
    api_headers = {"Authorization": f"Bearer {st.session_state.api_key}"}
    
    # Project Input Form
    with st.form("project_form"):
        st.subheader("Rincian Proyek")
        
        project_name = st.text_input("Nama Proyek")
        project_description = st.text_area(
            "Deskripsi Proyek",
            help="Jelaskan proyek, tujuannya, dan persyaratan spesifik apa pun"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            project_type = st.selectbox(
                "Jenis Proyek",
                ["Web Application", "Mobile App", "API Development", 
                 "Data Analytics", "AI/ML Solution", "Other"]
            )
            timeline = st.selectbox(
                "Perkiraan Waktu",
                ["1-2 bulan", "3-4 bulan", "5-6 bulan", "6+ bulan"]
            )
        
        with col2:
            budget_range = st.selectbox(
                "Kisaran Harga",
                ["Rp150 juta-Rp375 juta", "Rp375 juta-Rp750 juta", 
                              "Rp750 juta-Rp1,5 miliar", "Rp1,5 miliar+"]
            )
            priority = st.selectbox(
                "Prioritas Proyek",
                ["tinggi", "sedang", "rendah"]
            )
        
        tech_requirements = st.text_area(
            "Persyaratan Teknis (opsional)",
            help="Persyaratan teknis atau preferensi khusus apa pun"
        )
        
        special_considerations = st.text_area(
            "Pertimbangan Khusus (opsional)",
            help="Informasi tambahan atau persyaratan khusus apa pun"
        )
        
        submitted = st.form_submit_button("Analisis Proyek")
        
        if submitted and project_name and project_description:
            try:
                # Set OpenAI key
                set_openai_key(st.session_state.api_key)
                
                # Create agents
                ceo = Agent(
                    name="Project Director",
                    description="Kamu adalah seorang CEO beberapa perusahaan di masa lalu dan memiliki banyak pengalaman dalam mengevaluasi proyek dan membuat keputusan strategis.",
                    instructions="""
                    Kamu adalah CEO berpengalaman yang mengevaluasi proyek. Ikuti langkah-langkah berikut dengan ketat:

                    1. PERTAMA, gunakan alat AnalyzeProjectRequirements dengan:
                        - project_name: Nama dari detail proyek
                        - project_description: Deskripsi lengkap proyek
                        - project_type: Jenis proyek (Aplikasi Web, Aplikasi Seluler, dll.)
                        - budget_range: Rentang anggaran yang ditentukan

                    2. TUNGGU hingga analisis selesai sebelum melanjutkan.
                    
                    3. Tinjau hasil analisis dan berikan rekomendasi strategis.
                    """,
                    tools=[AnalyzeProjectRequirements],
                    api_headers=api_headers,
                    temperature=0.7,
                    max_prompt_tokens=25000
                )

                cto = Agent(
                    name="Technical Architect",
                    description="Senior Technical Architect dengan keahlian mendalam dalam desain sistem.",
                    instructions="""
                    Kamu adalah seorang Technical Architect. Ikuti langkah-langkah berikut dengan ketat:

                    1. TUNGGU analisis proyek selesai oleh CEO.

                    2. Gunakan alat CreateTechnicalSpecification dengan:
                        - architecture_type: Pilih dari monolitik/layanan mikro/tanpa server/hibrida
                        - core_technologies: Cantumkan teknologi utama sebagai nilai yang dipisahkan koma
                        - scalability_requirements: Pilih tinggi/sedang/rendah berdasarkan kebutuhan proyek

                    3. Tinjau spesifikasi teknis dan berikan rekomendasi tambahan.
                    """,
                    tools=[CreateTechnicalSpecification],
                    api_headers=api_headers,
                    temperature=0.5,
                    max_prompt_tokens=25000
                )

                product_manager = Agent(
                    name="Product Manager",
                    description="Product Manager berpengalaman yang berfokus pada keunggulan pengiriman.",
                    instructions="""
                    - Mengelola cakupan dan jangka waktu proyek dengan memberikan peta jalan proyek
                    - Menentukan persyaratan produk dan Anda harus memberikan produk dan fitur potensial yang dapat dibangun untuk perusahaan rintisan
                    """,
                    api_headers=api_headers,
                    temperature=0.4,
                    max_prompt_tokens=25000
                )

                developer = Agent(
                    name="Lead Developer",
                    description="Senior developer dengan keahlian full-stack.",
                    instructions="""
                    - Merencanakan implementasi teknis
                    - Menyediakan estimasi upaya
                    - Meninjau kelayakan teknis
                    """,
                    api_headers=api_headers,
                    temperature=0.3,
                    max_prompt_tokens=25000
                )

                client_manager = Agent(
                    name="Client Success Manager",
                    description="Client Success Manager yang berfokus pada penyampaian proyek.",
                    instructions="""
                    - Memastikan kepuasan klien
                    - Kelola ekspektasi
                    - Menangani umpan balik
                    """,
                    api_headers=api_headers,
                    temperature=0.6,
                    max_prompt_tokens=25000
                )

                # Create agency
                agency = Agency(
                    [
                        ceo, cto, product_manager, developer, client_manager,
                        [ceo, cto],
                        [ceo, product_manager],
                        [ceo, developer],
                        [ceo, client_manager],
                        [cto, developer],
                        [product_manager, developer],
                        [product_manager, client_manager]
                    ],
                    async_mode='threading',
                    shared_files='shared_files'
                )
                
                # Prepare project info
                project_info = {
                    "name": project_name,
                    "description": project_description,
                    "type": project_type,
                    "timeline": timeline,
                    "budget": budget_range,
                    "priority": priority,
                    "technical_requirements": tech_requirements,
                    "special_considerations": special_considerations
                }

                st.session_state.messages.append({"role": "user", "content": str(project_info)})
                # Create tabs and run analysis
                with st.spinner("AI Services Agency sedang menganalisis proyek Anda......"):
                    try:
                        # Get analysis from each agent using agency.get_completion()
                        ceo_response = agency.get_completion(
                            message=f"""Analisis proyek ini menggunakan tool AnalyzeProjectRequirements:
                            Project Name: {project_name}
                            Project Description: {project_description}
                            Project Type: {project_type}
                            Budget Range: {budget_range}
                            
                            Use these exact values with the tool and wait for the analysis results.""",
                            recipient_agent=ceo
                        )
                        
                        cto_response = agency.get_completion(
                            message=f"""Tinjau analisis proyek dan buat spesifikasi teknis menggunakan alat CreateTechnicalSpecification.
                            Pilih yang paling sesuai:
                                - architecture_type (monolithic/microservices/serverless/hybrid)
                                - core_technologies (comma-separated list)
                                - scalability_requirements (tinggi/sedang/rendah)
                            
                            Dasarkan pilihan Anda pada persyaratan dan analisis proyek.""",
                            recipient_agent=cto
                        )
                        
                        pm_response = agency.get_completion(
                            message=f"Menganalisis aspek manajemen proyek: {str(project_info)}",
                            recipient_agent=product_manager,
                            additional_instructions="Berfokus pada kesesuaian produk-pasar dan pengembangan peta jalan, serta berkoordinasi dengan tim teknis dan pemasaran."
                        )

                        developer_response = agency.get_completion(
                            message=f"Menganalisis implementasi teknis berdasarkan spesifikasi CTO: {str(project_info)}",
                            recipient_agent=developer,
                            additional_instructions="Berikan rincian implementasi teknis, tumpukan teknologi optimal yang akan Anda gunakan termasuk biaya layanan cloud (jika ada) dan umpan balik kelayakan, dan berkoordinasilah dengan manajer produk dan CTO untuk membangun produk yang diperlukan untuk perusahaan rintisan."
                        )
                        
                        client_response = agency.get_completion(
                            message=f"Menganalisis aspek keberhasilan klien: {str(project_info)}",
                            recipient_agent=client_manager,
                            additional_instructions="Memberikan strategi masuk pasar dan rencana akuisisi pelanggan yang terperinci, dan berkoordinasi dengan manajer produk."
                        )
                        
                        # Create tabs for different analyses
                        tabs = st.tabs([
                            "CEO's Project Analysis",
                            "CTO's Technical Specification",
                            "Product Manager's Plan",
                            "Developer's Implementation",
                            "Client Success Strategy"
                        ])
                        
                        with tabs[0]:
                            st.markdown("## CEO's Strategic Analysis")
                            st.markdown(ceo_response)
                            st.session_state.messages.append({"role": "assistant", "content": ceo_response})
                        
                        with tabs[1]:
                            st.markdown("## CTO's Technical Specification")
                            st.markdown(cto_response)
                            st.session_state.messages.append({"role": "assistant", "content": cto_response})
                        
                        with tabs[2]:
                            st.markdown("## Product Manager's Plan")
                            st.markdown(pm_response)
                            st.session_state.messages.append({"role": "assistant", "content": pm_response})
                        
                        with tabs[3]:
                            st.markdown("## Lead Developer's Development Plan")
                            st.markdown(developer_response)
                            st.session_state.messages.append({"role": "assistant", "content": developer_response})
                        
                        with tabs[4]:
                            st.markdown("## Client Success Strategy")
                            st.markdown(client_response)
                            st.session_state.messages.append({"role": "assistant", "content": client_response})

                    except Exception as e:
                        st.error(f"Kesalahan saat analisis: {str(e)}")
                        st.error("Silakan periksa masukan dan API key Anda, lalu coba lagi.")

            except Exception as e:
                st.error(f"Kesalahan saat analisis: {str(e)}")
                st.error("Silakan periksa API key Anda dan coba lagi.")

    # Add history management in sidebar
    with st.sidebar:
        st.subheader("Options")
        if st.checkbox("Tampilkan Analisis Riwayat"):
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])
        
        if st.button("Hapus Riwayat"):
            st.session_state.messages = []
            st.rerun()

if __name__ == "__main__":
    main()
from typing import Literal, Tuple, Dict, Optional, List
import os
import time
import json
import requests
import PyPDF2
from datetime import datetime, timedelta
import pytz
import pandas as pd
import re

import streamlit as st
from phi.agent import Agent
from phi.model.openai import OpenAIChat
from phi.tools.email import EmailTools
from phi.tools.zoom import ZoomTool
from phi.utils.log import logger
from streamlit_pdf_viewer import pdf_viewer


class CustomZoomTool(ZoomTool):
    def __init__(self, *, account_id: Optional[str] = None, client_id: Optional[str] = None, client_secret: Optional[str] = None, name: str = "zoom_tool"):
        super().__init__(account_id=account_id, client_id=client_id, client_secret=client_secret, name=name)
        self.token_url = "https://zoom.us/oauth/token"
        self.access_token = None
        self.token_expires_at = 0

    def get_access_token(self) -> str:
        if self.access_token and time.time() < self.token_expires_at:
            return str(self.access_token)
            
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {"grant_type": "account_credentials", "account_id": self.account_id}

        try:
            response = requests.post(self.token_url, headers=headers, data=data, auth=(self.client_id, self.client_secret))
            response.raise_for_status()

            token_info = response.json()
            self.access_token = token_info["access_token"]
            expires_in = token_info["expires_in"]
            self.token_expires_at = time.time() + expires_in - 60

            self._set_parent_token(str(self.access_token))
            return str(self.access_token)

        except requests.RequestException as e:
            logger.error(f"Error fetching access token: {e}")
            return ""

    def _set_parent_token(self, token: str) -> None:
        if token:
            self._ZoomTool__access_token = token


def init_session_state() -> None:
    """Initialize session state variables."""
    defaults = {
        'openai_api_key': "", 'zoom_account_id': "", 'zoom_client_id': "", 
        'zoom_client_secret': "", 'email_sender': "", 'email_passkey': "", 
        'company_name': "", 'custom_role_name': "", 'custom_requirements': "",
        'batch_results': [], 'processing_complete': False
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def create_resume_analyzer(requirements: str) -> Agent:
    """Creates resume analysis agent with custom requirements."""
    if not st.session_state.openai_api_key:
        st.error("Please enter your OpenAI API key first.")
        return None

    return Agent(
        model=OpenAIChat(
            id="gpt-4o",
            api_key=st.session_state.openai_api_key
        ),
        description="You are an expert technical recruiter who analyzes resumes.",
        instructions=[
            "Analyze the resume against the provided job requirements",
            "Be lenient with candidates who show strong potential",
            "Consider project experience as valid experience",
            "Value hands-on experience with key technologies",
            "Return a JSON response with selection decision and feedback"
        ],
        markdown=True
    )


def create_email_agent(receiver_email: str) -> Agent:
    """Create email agent for specific receiver."""
    return Agent(
        model=OpenAIChat(
            id="gpt-4o",
            api_key=st.session_state.openai_api_key
        ),
        tools=[EmailTools(
            receiver_email=receiver_email,
            sender_email=st.session_state.email_sender,
            sender_name=st.session_state.company_name,
            sender_passkey=st.session_state.email_passkey
        )],
        description="You are a professional recruitment coordinator.",
        instructions=[
            "Draft and send professional recruitment emails",
            "Use all lowercase letters for casual, human tone",
            "Maintain friendly yet professional tone",
            "Always end emails with: 'best,\\nthe ai recruiting team'",
            f"Company name: '{st.session_state.company_name}'"
        ],
        markdown=True,
        show_tool_calls=True
    )


def create_scheduler_agent() -> Agent:
    """Create Zoom scheduler agent."""
    zoom_tools = CustomZoomTool(
        account_id=st.session_state.zoom_account_id,
        client_id=st.session_state.zoom_client_id,
        client_secret=st.session_state.zoom_client_secret
    )

    return Agent(
        name="Interview Scheduler",
        model=OpenAIChat(
            id="gpt-4o",
            api_key=st.session_state.openai_api_key
        ),
        tools=[zoom_tools],
        description="You are an interview scheduling coordinator.",
        instructions=[
            "Schedule interviews during business hours (9 AM - 5 PM Jakarta Time)",
            "Create meetings with proper titles and descriptions",
            "Use ISO 8601 format for dates"
        ],
        markdown=True,
        show_tool_calls=True
    )


def extract_text_from_pdf(pdf_file) -> str:
    """Extract text from PDF file."""
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text
    except Exception as e:
        logger.error(f"Error extracting PDF text: {str(e)}")
        return ""


def extract_email_from_text(text: str) -> Optional[str]:
    """Extract email address from resume text."""
    # Pattern email yang umum
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(email_pattern, text)
    
    if emails:
        # Prioritas: email personal (gmail, yahoo, outlook) daripada email universitas
        personal_domains = ['gmail.com', 'yahoo.com', 'outlook.com', 'hotmail.com', 'icloud.com']
        
        # Cari email dengan domain personal
        for email in emails:
            if any(domain in email.lower() for domain in personal_domains):
                return email
        
        # Jika tidak ada, ambil email pertama
        return emails[0]
    
    return None


def analyze_resume(resume_text: str, requirements: str, analyzer: Agent) -> Tuple[bool, str, dict]:
    """Analyze single resume against requirements."""
    try:
        response = analyzer.run(
            f"""Analyze this resume against the requirements and respond in valid JSON:
            
            Role Requirements:
            {requirements}
            
            Resume Text:
            {resume_text}
            
            Return JSON:
            {{
                "selected": true/false,
                "feedback": "Detailed feedback",
                "matching_skills": ["skill1", "skill2"],
                "missing_skills": ["skill3", "skill4"],
                "experience_level": "junior/mid/senior"
            }}
            
            Criteria:
            1. Match at least 70% of required skills
            2. Consider practical experience and projects
            3. Value transferable skills
            4. Look for continuous learning
            
            Return ONLY the JSON object without markdown.
            """
        )

        assistant_message = next((msg.content for msg in response.messages if msg.role == 'assistant'), None)
        if not assistant_message:
            raise ValueError("No assistant message found")

        result = json.loads(assistant_message.strip())
        if not isinstance(result, dict) or not all(k in result for k in ["selected", "feedback"]):
            raise ValueError("Invalid response format")

        return result["selected"], result["feedback"], result

    except Exception as e:
        logger.error(f"Error analyzing resume: {str(e)}")
        return False, f"Error: {str(e)}", {}


def send_selection_email(email_agent: Agent, role: str) -> None:
    """Send selection email to candidate."""
    email_agent.run(
        f"""Send selection email for {role} position.
        
        Include:
        1. Congratulate on selection
        2. Explain next steps
        3. Mention interview details coming soon
        4. End with: best,\\nthe ai recruiting team
        """
    )


def send_rejection_email(email_agent: Agent, role: str, feedback: str) -> None:
    """Send rejection email with feedback."""
    email_agent.run(
        f"""Send rejection email for {role} position.
        
        Style:
        1. All lowercase
        2. Empathetic and human
        3. Include feedback: {feedback}
        4. Encourage upskilling
        5. Suggest learning resources
        6. End with: best,\\nthe ai recruiting team
        """
    )


def schedule_interview(scheduler: Agent, candidate_email: str, email_agent: Agent, role: str) -> bool:
    """Schedule interview and send confirmation."""
    try:
        jakarta_tz = pytz.timezone('Asia/Jakarta')
        current_time_jkt = datetime.now(jakarta_tz)
        tomorrow_jkt = current_time_jkt + timedelta(days=1)
        interview_time = tomorrow_jkt.replace(hour=11, minute=0, second=0, microsecond=0)
        formatted_time_iso = interview_time.strftime('%Y-%m-%dT%H:%M:%S')

        meeting_response = scheduler.run(
            f"""Schedule 60-minute technical interview:
            - Title: '{role} Technical Interview'
            - Date: {formatted_time_iso}
            - Timezone: Asia/Jakarta
            - Attendee: {candidate_email}
            - Duration: 60 minutes
            """
        )

        meeting_link, meeting_id = "Zoom link not available", "N/A"
        try:
            raw_response = meeting_response.messages[-1].content.strip()
            if raw_response.startswith("{"):
                meeting_info = json.loads(raw_response)
                meeting_link = meeting_info.get("join_url", meeting_link)
                meeting_id = meeting_info.get("id", meeting_id)
            else:
                if "https://" in raw_response:
                    meeting_link = raw_response.split("https://")[1].split()[0]
                    meeting_link = "https://" + meeting_link
        except Exception as e:
            logger.warning(f"Could not parse meeting response: {e}")

        pretty_date = interview_time.strftime("%A, %d %B %Y")
        pretty_time = interview_time.strftime("%I:%M %p")

        email_agent.run(
            f"""Send interview confirmation to {candidate_email}:
            
            Subject: Interview Confirmation – {role} Position
            
            Dear Candidate,
            
            Technical interview details for {role}:
            
            📅 Date: {pretty_date}
            🕒 Time: {pretty_time} (Jakarta Time, UTC+7)
            ⏳ Duration: 60 minutes
            🔗 Zoom Link: {meeting_link}
            
            Notes:
            - Join 5 minutes early
            - Timezone converter: https://www.timeanddate.com/worldclock/converter.html
            - Be confident and prepare well!
            
            best,
            the ai recruiting team
            """
        )
        return True

    except Exception as e:
        logger.error(f"Error scheduling interview: {str(e)}")
        return False


def process_batch_applications(candidates_data: List[Dict], role_name: str, requirements: str) -> List[Dict]:
    """Process multiple applications at once."""
    results = []
    analyzer = create_resume_analyzer(requirements)
    
    if not analyzer:
        st.error("Failed to create analyzer")
        return results

    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for idx, candidate in enumerate(candidates_data):
        status_text.text(f"Processing {candidate['email']}...")
        
        # Analyze resume
        is_selected, feedback, analysis_details = analyze_resume(
            candidate['resume_text'],
            requirements,
            analyzer
        )
        
        result = {
            'email': candidate['email'],
            'filename': candidate['filename'],
            'selected': is_selected,
            'feedback': feedback,
            'analysis': analysis_details,
            'email_sent': False,
            'interview_scheduled': False
        }
        
        # Send appropriate email
        try:
            email_agent = create_email_agent(candidate['email'])
            
            if is_selected:
                send_selection_email(email_agent, role_name)
                result['email_sent'] = True
                
                # Schedule interview
                scheduler = create_scheduler_agent()
                success = schedule_interview(scheduler, candidate['email'], email_agent, role_name)
                result['interview_scheduled'] = success
            else:
                send_rejection_email(email_agent, role_name, feedback)
                result['email_sent'] = True
                
        except Exception as e:
            logger.error(f"Error processing {candidate['email']}: {str(e)}")
            result['error'] = str(e)
        
        results.append(result)
        progress_bar.progress((idx + 1) / len(candidates_data))
    
    status_text.text("✅ Processing complete!")
    return results


def main() -> None:
    st.set_page_config(
        page_title="AI Recruitment System - Batch Processing",
        page_icon="🤖",
        layout="wide"
    )
    
    st.title("🤖 AI Recruitment System - Batch Processing")
    st.markdown("Upload multiple CVs and process them all at once")

    init_session_state()

    # Sidebar Configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        st.subheader("OpenAI Settings")
        api_key = st.text_input("OpenAI API Key", type="password", 
                               value=st.session_state.openai_api_key)
        if api_key: 
            st.session_state.openai_api_key = api_key

        st.subheader("Zoom Settings")
        zoom_account_id = st.text_input("Zoom Account ID", type="password", 
                                       value=st.session_state.zoom_account_id)
        zoom_client_id = st.text_input("Zoom Client ID", type="password", 
                                      value=st.session_state.zoom_client_id)
        zoom_client_secret = st.text_input("Zoom Client Secret", type="password", 
                                          value=st.session_state.zoom_client_secret)
        
        st.subheader("Email Settings")
        email_sender = st.text_input("Sender Email", value=st.session_state.email_sender)
        email_passkey = st.text_input("Email App Password", type="password", 
                                     value=st.session_state.email_passkey)
        company_name = st.text_input("Company Name", value=st.session_state.company_name)

        if zoom_account_id: st.session_state.zoom_account_id = zoom_account_id
        if zoom_client_id: st.session_state.zoom_client_id = zoom_client_id
        if zoom_client_secret: st.session_state.zoom_client_secret = zoom_client_secret
        if email_sender: st.session_state.email_sender = email_sender
        if email_passkey: st.session_state.email_passkey = email_passkey
        if company_name: st.session_state.company_name = company_name

    # Check required configs
    required_configs = {
        'OpenAI API Key': st.session_state.openai_api_key,
        'Zoom Account ID': st.session_state.zoom_account_id,
        'Zoom Client ID': st.session_state.zoom_client_id,
        'Zoom Client Secret': st.session_state.zoom_client_secret,
        'Email Sender': st.session_state.email_sender,
        'Email Password': st.session_state.email_passkey,
        'Company Name': st.session_state.company_name
    }

    missing_configs = [k for k, v in required_configs.items() if not v]
    if missing_configs:
        st.warning(f"⚠️ Please configure: {', '.join(missing_configs)}")
        return

    # Main Interface
    st.markdown("---")
    
    # Step 1: Define Role
    st.header("📋 Step 1: Define Job Role")
    col1, col2 = st.columns(2)
    
    with col1:
        role_name = st.text_input("Role/Position Name", 
                                  value=st.session_state.custom_role_name,
                                  placeholder="e.g., Senior Backend Engineer")
        if role_name:
            st.session_state.custom_role_name = role_name
    
    with col2:
        st.info("💡 Tip: Be specific about the role title")
    
    requirements = st.text_area(
        "Job Requirements (Skills, Experience, etc.)",
        value=st.session_state.custom_requirements,
        height=200,
        placeholder="""Example:
Required Skills:
- Python, Django, FastAPI
- PostgreSQL, Redis
- Docker, Kubernetes
- REST API design
- 3+ years experience

Nice to have:
- AWS/GCP experience
- Microservices architecture
- TDD/BDD practices
        """
    )
    if requirements:
        st.session_state.custom_requirements = requirements

    if not role_name or not requirements:
        st.warning("⚠️ Please define role name and requirements to continue")
        return

    st.markdown("---")

    # Step 2: Upload CVs and Emails
    st.header("📂 Step 2: Upload CVs and Enter Emails")
    
    uploaded_files = st.file_uploader(
        "Upload Resume PDFs (multiple files allowed)",
        type=["pdf"],
        accept_multiple_files=True
    )

    if uploaded_files:
        st.success(f"✅ {len(uploaded_files)} CV(s) uploaded")
        
        # Show uploaded files
        with st.expander("📄 View Uploaded CVs", expanded=True):
            for file in uploaded_files:
                st.text(f"• {file.name}")
        
        # Auto-extract emails from CVs
        st.subheader("📧 Candidate Emails")
        st.info("💡 System will auto-detect emails from CVs. You can edit or add missing emails below.")
        
        # Extract text and emails from all CVs
        cv_data = []
        for file in uploaded_files:
            resume_text = extract_text_from_pdf(file)
            extracted_email = extract_email_from_text(resume_text) if resume_text else None
            cv_data.append({
                'filename': file.name,
                'resume_text': resume_text,
                'extracted_email': extracted_email
            })
        
        # Create editable email mapping table
        st.write("**Edit Email Addresses (one per line, matching CV order):**")
        
        # Show preview with extracted emails
        with st.expander("🔍 Auto-Detected Emails Preview", expanded=True):
            preview_data = []
            for i, data in enumerate(cv_data):
                status = "✅ Found" if data['extracted_email'] else "❌ Not found"
                preview_data.append({
                    'No': i + 1,
                    'CV File': data['filename'],
                    'Detected Email': data['extracted_email'] or '(not found)',
                    'Status': status
                })
            preview_df = pd.DataFrame(preview_data)
            st.dataframe(preview_df, use_container_width=True)
        
        # Pre-fill emails_input with detected emails
        default_emails = '\n'.join([
            data['extracted_email'] if data['extracted_email'] else ''
            for data in cv_data
        ])
        
        emails_input = st.text_area(
            "Candidate Emails (Edit if needed)",
            value=default_emails,
            height=150,
            placeholder="candidate1@email.com\ncandidate2@email.com\ncandidate3@email.com",
            help="Auto-detected emails are pre-filled. Edit or add missing emails."
        )
        
        if emails_input:
            emails = [e.strip() for e in emails_input.split('\n') if e.strip()]
            
            if len(emails) != len(uploaded_files):
                st.error(f"❌ Mismatch! You have {len(uploaded_files)} CVs but {len(emails)} emails")
            else:
                st.success(f"✅ {len(emails)} emails matched with CVs")
                
                # Show mapping
                with st.expander("🔗 CV-Email Mapping", expanded=True):
                    mapping_df = pd.DataFrame({
                        'CV File': [f.name for f in uploaded_files],
                        'Email': emails
                    })
                    st.dataframe(mapping_df, use_container_width=True)
                
                # Process button
                if st.button("🚀 Process All Applications", type="primary", use_container_width=True):
                    with st.spinner("🔄 Processing applications..."):
                        # Prepare candidates data
                        candidates_data = []
                        for file, email in zip(uploaded_files, emails):
                            resume_text = extract_text_from_pdf(file)
                            if resume_text:
                                candidates_data.append({
                                    'email': email,
                                    'filename': file.name,
                                    'resume_text': resume_text
                                })
                        
                        # Process all
                        results = process_batch_applications(
                            candidates_data,
                            st.session_state.custom_role_name,
                            st.session_state.custom_requirements
                        )
                        
                        st.session_state.batch_results = results
                        st.session_state.processing_complete = True
                        st.rerun()

    # Step 3: Show Results
    if st.session_state.processing_complete and st.session_state.batch_results:
        st.markdown("---")
        st.header("📊 Processing Results")
        
        results = st.session_state.batch_results
        selected_count = sum(1 for r in results if r['selected'])
        rejected_count = len(results) - selected_count
        
        # Summary metrics
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Processed", len(results))
        col2.metric("✅ Selected", selected_count)
        col3.metric("❌ Rejected", rejected_count)
        
        # Detailed results
        st.subheader("📋 Detailed Results")
        
        # Selected candidates
        if selected_count > 0:
            st.success(f"✅ Selected Candidates ({selected_count})")
            for result in results:
                if result['selected']:
                    with st.expander(f"✅ {result['email']} - {result['filename']}"):
                        st.write("**Feedback:**", result['feedback'])
                        st.write("**Email Sent:**", "✅ Yes" if result['email_sent'] else "❌ No")
                        st.write("**Interview Scheduled:**", "✅ Yes" if result['interview_scheduled'] else "❌ No")
                        if result.get('analysis'):
                            st.json(result['analysis'])
        
        # Rejected candidates
        if rejected_count > 0:
            st.error(f"❌ Rejected Candidates ({rejected_count})")
            for result in results:
                if not result['selected']:
                    with st.expander(f"❌ {result['email']} - {result['filename']}"):
                        st.write("**Feedback:**", result['feedback'])
                        st.write("**Email Sent:**", "✅ Yes" if result['email_sent'] else "❌ No")
                        if result.get('analysis'):
                            st.json(result['analysis'])
        
        # Export results
        if st.button("📥 Export Results to CSV"):
            df = pd.DataFrame(results)
            csv = df.to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name=f"recruitment_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )

    # Reset button
    if st.sidebar.button("🔄 Start New Batch"):
        st.session_state.batch_results = []
        st.session_state.processing_complete = False
        st.rerun()


if __name__ == "__main__":
    main()
import streamlit as st
import openai
import time
from pathlib import Path
import tempfile
import base64
import cv2
import os
import inspect

# Fix for getargspec deprecation warning
if not hasattr(inspect, 'getargspec'):
    inspect.getargspec = inspect.getfullargspec

try:
    from phi.agent import Agent
    from phi.model.openai import OpenAIChat
    from phi.tools.duckduckgo import DuckDuckGo
    PHI_AVAILABLE = True
except ImportError as e:
    PHI_AVAILABLE = False
    st.error(f"Error importing phi libraries: {str(e)}")
    st.info("Please install phidata with: pip install phidata==2.4.11")

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
    st.markdown("**Installation Requirements:**")
    st.code("""
pip install streamlit
pip install phidata==2.7.2
pip install openai==1.3.0
pip install opencv-python
pip install Pillow
pip install duckduckgo-search==3.9.6
    """, language="bash")
    
    st.markdown("**If you get 'getargspec' error, try:**")
    st.code("""
pip uninstall phidata
pip install phidata==2.7.2
    """, language="bash")

def extract_frames_from_video(video_path, num_frames=5):
    """Extract frames from video for analysis"""
    cap = cv2.VideoCapture(video_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    frames = []
    frame_indices = [int(i * total_frames / num_frames) for i in range(num_frames)]
    
    for idx in frame_indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ret, frame = cap.read()
        if ret:
            # Convert BGR to RGB
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frames.append(frame)
    
    cap.release()
    return frames

def encode_frame_to_base64(frame):
    """Convert frame to base64 for OpenAI API"""
    import io
    from PIL import Image
    
    # Convert numpy array to PIL Image
    pil_image = Image.fromarray(frame)
    
    # Save to bytes
    buffer = io.BytesIO()
    pil_image.save(buffer, format='JPEG')
    buffer.seek(0)
    
    # Encode to base64
    return base64.b64encode(buffer.getvalue()).decode('utf-8')

def analyze_video_with_openai(frames, user_prompt, api_key):
    """Analyze video frames using OpenAI Vision API"""
    try:
        # Prepare messages with frames
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"""Analyze these frames from a video and answer the following question: {user_prompt}
                        
                        Please provide detailed analysis based on what you can see in these video frames.
                        Focus on practical, actionable information."""
                    }
                ]
            }
        ]
        
        # Add frames to the message
        for i, frame in enumerate(frames):
            base64_frame = encode_frame_to_base64(frame)
            messages[0]["content"].append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{base64_frame}",
                    "detail": "high"
                }
            })
        
        # Make API call
        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o",  # Use GPT-4 Vision model
            messages=messages,
            max_tokens=1500
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        st.error(f"Error analyzing video: {str(e)}")
        return None

# Initialize agent for web research
@st.cache_resource
def initialize_agent(api_key):
    if not PHI_AVAILABLE:
        return None
    try:
        return Agent(
            name="Research Agent",
            model=OpenAIChat(
                id="gpt-4o",
                api_key=api_key
            ),
            tools=[DuckDuckGo()],
            markdown=True,
        )
    except Exception as e:
        st.error(f"Error initializing agent: {str(e)}")
        return None

# Main content area
st.header("Video Analysis & Research Tool")

# Check if API key is provided
if not openai_api_key:
    st.error("⚠️ Please enter your OpenAI API key in the sidebar to use this application.")
    st.stop()

# Check if PHI is available
if not PHI_AVAILABLE:
    st.error("⚠️ PHI libraries are not properly installed.")
    st.stop()

# Initialize agent with the provided API key
agent = initialize_agent(openai_api_key)
if agent is None:
    st.error("⚠️ Failed to initialize research agent.")
    st.stop()

# File uploader
uploaded_file = st.file_uploader("Upload a video file", type=['mp4', 'mov', 'avi'])

if uploaded_file:
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp_file:
        tmp_file.write(uploaded_file.read())
        video_path = tmp_file.name
    
    st.video(video_path)
    
    user_prompt = st.text_area(
        "What would you like to know?",
        placeholder="Ask any question related to the video - the AI Agent will analyze it and search the web if needed",
        help="You can ask questions about the video content and get relevant information from the web"
    )
    
    if st.button("Analyze & Research"):
        if not user_prompt:
            st.warning("Please enter your question.")
        else:
            try:
                with st.spinner("Processing video and researching..."):
                    # Extract frames from video
                    st.info("Extracting frames from video...")
                    frames = extract_frames_from_video(video_path, num_frames=5)
                    
                    if not frames:
                        st.error("Could not extract frames from the video.")
                    else:
                        # Analyze video with OpenAI Vision
                        st.info("Analyzing video content...")
                        video_analysis = analyze_video_with_openai(frames, user_prompt, openai_api_key)
                        
                        if video_analysis:
                            # Use the agent for web research based on video analysis
                            st.info("Conducting web research...")
                            try:
                                research_prompt = f"""
                                Based on this video analysis: {video_analysis}
                                
                                Now search the web for additional relevant information to answer: {user_prompt}
                                
                                Provide a comprehensive response that combines the video analysis with current web information.
                                Focus on practical, actionable information.
                                """
                                
                                result = agent.run(research_prompt)
                                
                                st.subheader("Analysis Results")
                                
                                # Display video analysis
                                with st.expander("Video Analysis", expanded=True):
                                    st.markdown(video_analysis)
                                
                                # Display web research results
                                with st.expander("Web Research & Final Response", expanded=True):
                                    st.markdown(result.content)
                            except Exception as research_error:
                                st.error(f"Web research failed: {str(research_error)}")
                                # Still show video analysis even if web research fails
                                st.subheader("Video Analysis Results")
                                st.markdown(video_analysis)
                        else:
                            st.error("Failed to analyze video content.")

            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
                st.info("Make sure you have installed all required packages: opencv-python, Pillow")
            finally:
                # Clean up temporary file
                if 'video_path' in locals():
                    Path(video_path).unlink(missing_ok=True)
else:
    st.info("Please upload a video to begin analysis.")

st.markdown("""
    <style>
    .stTextArea textarea {
        height: 100px;
    }
    </style>
    """, unsafe_allow_html=True)
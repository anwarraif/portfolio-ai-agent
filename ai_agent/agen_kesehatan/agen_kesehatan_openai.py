import openai
import streamlit as st
import json
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px
from typing import Dict, Any

st.set_page_config(
    page_title="AI Health & Fitness Planner",
    page_icon="🏋️‍♂️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Enhanced CSS styling
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    .main {
        padding: 1rem 2rem;
        font-family: 'Inter', sans-serif;
    }
    
    .stApp {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    
    .main-container {
        background: white;
        border-radius: 20px;
        padding: 2rem;
        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
        margin: 1rem 0;
    }
    
    .metric-card {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        padding: 1.5rem;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin: 0.5rem 0;
        box-shadow: 0 8px 16px rgba(79, 172, 254, 0.3);
    }
    
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }
    
    .metric-label {
        font-size: 0.9rem;
        opacity: 0.9;
    }
    
    .plan-card {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 15px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
    }
    
    .plan-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 1rem;
        text-align: center;
    }
    
    .feature-highlight {
        background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%);
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
        border-left: 4px solid #ff6b6b;
    }
    
    .progress-container {
        background: #f1f3f4;
        border-radius: 10px;
        padding: 1rem;
        margin: 1rem 0;
    }
    
    .stButton>button {
        width: 100%;
        border-radius: 10px;
        height: 3em;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border: none;
        color: white;
        font-weight: 600;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
        transition: all 0.3s ease;
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
    }
    
    .sidebar-content {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
    }
    
    div[data-testid="stExpander"] {
        background: white;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin: 1rem 0;
    }
    
    .success-animation {
        animation: pulse 2s infinite;
    }
    
    @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.05); }
        100% { transform: scale(1); }
    }
    </style>
""", unsafe_allow_html=True)

def calculate_bmi(weight: float, height: float) -> float:
    """Calculate BMI"""
    height_m = height / 100
    return weight / (height_m ** 2)

def get_bmi_category(bmi: float) -> str:
    """Get BMI category"""
    if bmi < 18.5:
        return "Underweight"
    elif bmi < 25:
        return "Normal"
    elif bmi < 30:
        return "Overweight"
    else:
        return "Obese"

def calculate_bmr(weight: float, height: float, age: int, sex: str) -> float:
    """Calculate Basal Metabolic Rate using Harris-Benedict equation"""
    if sex.lower() == "male":
        return 88.362 + (13.397 * weight) + (4.799 * height) - (5.677 * age)
    else:
        return 447.593 + (9.247 * weight) + (3.098 * height) - (4.330 * age)

def calculate_daily_calories(bmr: float, activity_level: str) -> float:
    """Calculate daily calorie needs"""
    multipliers = {
        "Sedentary": 1.2,
        "Lightly Active": 1.375,
        "Moderately Active": 1.55,
        "Very Active": 1.725,
        "Extremely Active": 1.9
    }
    return bmr * multipliers.get(activity_level, 1.2)

def generate_openai_response(prompt: str, api_key: str, model: str = "gpt-4") -> str:
    """Generate response using OpenAI Chat API with better error handling"""
    openai.api_key = api_key
    try:
        response = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a professional health and fitness expert with extensive knowledge in nutrition and exercise science. Provide detailed, safe, and personalized advice."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1500,
            temperature=0.7
        )
        return response["choices"][0]["message"]["content"]
    except openai.error.RateLimitError:
        return "❌ API rate limit reached. Please try again later."
    except openai.error.InvalidRequestError:
        return "❌ Invalid API request. Please check your API key."
    except openai.error.AuthenticationError:
        return "❌ Invalid API key. Please check your credentials."
    except Exception as e:
        return f"❌ Error: {str(e)}"

def display_health_metrics(weight: float, height: float, age: int, sex: str, activity_level: str):
    """Display health metrics in an attractive format"""
    bmi = calculate_bmi(weight, height)
    bmi_category = get_bmi_category(bmi)
    bmr = calculate_bmr(weight, height, age, sex)
    daily_calories = calculate_daily_calories(bmr, activity_level)
    
    st.markdown("### 📊 Your Health Metrics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{bmi:.1f}</div>
            <div class="metric-label">BMI ({bmi_category})</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{bmr:.0f}</div>
            <div class="metric-label">BMR (kcal/day)</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{daily_calories:.0f}</div>
            <div class="metric-label">Daily Calories</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        ideal_weight_min = 18.5 * (height/100)**2
        ideal_weight_max = 24.9 * (height/100)**2
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{ideal_weight_min:.0f}-{ideal_weight_max:.0f}</div>
            <div class="metric-label">Ideal Weight (kg)</div>
        </div>
        """, unsafe_allow_html=True)

def create_nutrition_chart(calories: float):
    """Create a nutrition breakdown chart"""
    # Sample macro distribution (can be customized based on goals)
    protein_cal = calories * 0.25
    carb_cal = calories * 0.45
    fat_cal = calories * 0.30
    
    fig = go.Figure(data=[go.Pie(
        labels=['Protein', 'Carbohydrates', 'Fats'],
        values=[protein_cal, carb_cal, fat_cal],
        hole=.3,
        marker_colors=['#ff6b6b', '#4ecdc4', '#45b7d1']
    )])
    
    fig.update_layout(
        title="Daily Macro Distribution",
        showlegend=True,
        height=300,
        margin=dict(t=50, b=0, l=0, r=0)
    )
    
    return fig

def display_dietary_plan(plan_content: Dict[str, Any], daily_calories: float):
    """Enhanced dietary plan display"""
    with st.expander("🍽️ Your Personalized Dietary Plan", expanded=True):
        
        # Nutrition chart
        col1, col2 = st.columns([1, 1])
        
        with col1:
            fig = create_nutrition_chart(daily_calories)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown("### 🎯 Plan Benefits")
            st.markdown(f"""
            <div class="feature-highlight">
                <strong>Why this works for you:</strong><br>
                {plan_content.get("why_this_plan_works", "Customized for your specific goals and metabolism.")}
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("### 📋 Daily Meal Plan")
        st.markdown(f"""
        <div class="plan-card">
            {plan_content.get("meal_plan", "Plan not available")}
        </div>
        """, unsafe_allow_html=True)
        
        # Tips and considerations
        col3, col4 = st.columns(2)
        
        with col3:
            st.markdown("### 💡 Nutrition Tips")
            tips = [
                "🥤 Drink 8-10 glasses of water daily",
                "🥗 Fill half your plate with vegetables",
                "🍽️ Eat slowly and mindfully",
                "⏰ Try to eat at regular intervals"
            ]
            for tip in tips:
                st.info(tip)
        
        with col4:
            st.markdown("### ⚠️ Important Notes")
            considerations = plan_content.get("important_considerations", "").split('\n')
            for consideration in considerations:
                if consideration.strip():
                    st.warning(consideration.strip())

def display_fitness_plan(plan_content: Dict[str, Any]):
    """Enhanced fitness plan display"""
    with st.expander("💪 Your Personalized Fitness Plan", expanded=True):
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("### 🎯 Your Fitness Goals")
            st.markdown(f"""
            <div class="plan-header">
                <h3>{plan_content.get("goals", "Build strength and improve overall fitness")}</h3>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("### 🏋️‍♂️ Weekly Exercise Routine")
            st.markdown(f"""
            <div class="plan-card">
                {plan_content.get("routine", "Routine not available")}
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("### 💡 Pro Tips")
            tips = plan_content.get("tips", "").split('\n')
            for tip in tips:
                if tip.strip():
                    st.success(tip.strip())
            
            # Progress tracking section
            st.markdown("### 📈 Track Progress")
            st.markdown("""
            <div class="progress-container">
                <p>🎯 <strong>Weekly Goals:</strong></p>
                <p>• Log workouts: 0/5</p>
                <p>• Active days: 0/4</p>
                <p>• Rest days: 0/2</p>
            </div>
            """, unsafe_allow_html=True)

def display_progress_dashboard():
    """Display a simple progress dashboard"""
    st.markdown("### 📊 Progress Dashboard")
    
    # Sample data - in real app, this would come from user tracking
    dates = [datetime.now() - timedelta(days=x) for x in range(30, 0, -1)]
    weights = [75 + (x/10) * (-0.5) for x in range(30)]  # Sample weight loss trend
    
    fig = px.line(
        x=dates, 
        y=weights,
        title="Weight Progress (Last 30 Days)",
        labels={"x": "Date", "y": "Weight (kg)"}
    )
    fig.update_traces(line_color="#667eea", line_width=3)
    fig.update_layout(height=300)
    
    st.plotly_chart(fig, use_container_width=True)

def main():
    # Initialize session state
    if 'dietary_plan' not in st.session_state:
        st.session_state.dietary_plan = {}
        st.session_state.fitness_plan = {}
        st.session_state.plans_generated = False
        st.session_state.user_profile = {}

    # Header
    st.markdown("""
    <div class="main-container">
        <div style="text-align: center; margin-bottom: 2rem;">
            <h1>🏋️‍♂️ AI Health & Fitness Planner</h1>
            <p style="font-size: 1.2rem; color: #666; margin-top: 1rem;">
                Your personal AI-powered health companion for nutrition and fitness planning
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Sidebar configuration
    with st.sidebar:
        st.markdown('<div class="sidebar-content">', unsafe_allow_html=True)
        st.markdown("## 🔑 API Configuration")
        
        openai_api_key = st.text_input(
            "OpenAI API Key",
            type="password",
            help="Enter your OpenAI API key to access AI features",
            placeholder="sk-..."
        )
        
        if not openai_api_key:
            st.markdown("""
            <div style="background: #fff3cd; padding: 1rem; border-radius: 8px; border-left: 4px solid #ffc107;">
                <strong>⚠️ API Key Required</strong><br>
                Please enter your OpenAI API key to use AI features.
                <br><br>
                <a href="https://platform.openai.com/signup/" target="_blank">🔗 Get your API key here</a>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="background: #d4edda; padding: 1rem; border-radius: 8px; border-left: 4px solid #28a745;">
                <strong>✅ API Key Connected</strong><br>
                Ready to generate your personalized plans!
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Quick stats if plans are generated
        if st.session_state.plans_generated:
            st.markdown("---")
            st.markdown("## 📈 Quick Stats")
            profile = st.session_state.user_profile
            if profile:
                st.metric("Current BMI", f"{calculate_bmi(profile['weight'], profile['height']):.1f}")
                st.metric("Daily Calories", f"{calculate_daily_calories(calculate_bmr(profile['weight'], profile['height'], profile['age'], profile['sex']), profile['activity_level']):.0f}")

    if openai_api_key:
        # User Profile Section
        st.markdown("## 👤 Your Health Profile")
        
        with st.container():
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### 📏 Basic Information")
                age = st.slider("Age", min_value=10, max_value=100, value=30, help="Your current age")
                height = st.number_input("Height (cm)", min_value=100.0, max_value=250.0, value=170.0, step=0.1)
                weight = st.number_input("Weight (kg)", min_value=20.0, max_value=300.0, value=70.0, step=0.1)
                sex = st.selectbox("Sex", options=["Male", "Female", "Other"], help="Biological sex for accurate calculations")

            with col2:
                st.markdown("### 🎯 Goals & Preferences")
                activity_level = st.selectbox(
                    "Activity Level",
                    options=["Sedentary", "Lightly Active", "Moderately Active", "Very Active", "Extremely Active"],
                    index=2,
                    help="Your typical weekly activity level"
                )
                
                fitness_goals = st.selectbox(
                    "Primary Fitness Goal",
                    options=["Lose Weight", "Gain Muscle", "Improve Endurance", "General Health", "Strength Training"],
                    help="What's your main fitness objective?"
                )
                
                dietary_preferences = st.multiselect(
                    "Dietary Preferences",
                    options=["Vegetarian", "Vegan", "Keto", "Gluten Free", "Low Carb", "Dairy Free", "Paleo"],
                    help="Select all that apply to you"
                )
                
                experience_level = st.selectbox(
                    "Fitness Experience",
                    options=["Beginner", "Intermediate", "Advanced"],
                    help="Your current fitness experience level"
                )

        # Display health metrics
        if age and height and weight:
            display_health_metrics(weight, height, age, sex, activity_level)

        # Generate plans button
        st.markdown("---")
        if st.button("🚀 Generate My Personalized Health Plan", use_container_width=True):
            with st.spinner("🤖 AI is analyzing your profile and creating your personalized plans..."):
                try:
                    # Store user profile
                    user_profile = {
                        "age": age, "weight": weight, "height": height, "sex": sex,
                        "activity_level": activity_level, "fitness_goals": fitness_goals,
                        "dietary_preferences": dietary_preferences, "experience_level": experience_level
                    }
                    st.session_state.user_profile = user_profile
                    
                    # Calculate metrics
                    bmi = calculate_bmi(weight, height)
                    bmr = calculate_bmr(weight, height, age, sex)
                    daily_calories = calculate_daily_calories(bmr, activity_level)
                    
                    profile_text = f"""
                    User Profile:
                    - Age: {age} years
                    - Weight: {weight}kg, Height: {height}cm
                    - Sex: {sex}
                    - BMI: {bmi:.1f} ({get_bmi_category(bmi)})
                    - Activity Level: {activity_level}
                    - Fitness Goals: {fitness_goals}
                    - Dietary Preferences: {', '.join(dietary_preferences) if dietary_preferences else 'None specified'}
                    - Experience Level: {experience_level}
                    - Daily Calorie Needs: {daily_calories:.0f} kcal
                    """

                    # Generate dietary plan
                    dietary_prompt = f"""
                    As a certified nutritionist, create a comprehensive daily meal plan based on this profile:
                    
                    {profile_text}
                    
                    Please provide:
                    1. A detailed daily meal plan with specific foods and portions
                    2. Explanation of why this plan works for their goals
                    3. Important nutritional considerations
                    4. Meal timing recommendations
                    
                    Focus on practical, sustainable nutrition that fits their preferences and goals.
                    """
                    
                    # Generate fitness plan
                    fitness_prompt = f"""
                    As a certified fitness trainer, create a comprehensive weekly workout plan based on this profile:
                    
                    {profile_text}
                    
                    Please provide:
                    1. A detailed weekly workout schedule with specific exercises
                    2. Sets, reps, and intensity guidelines
                    3. Progression recommendations
                    4. Recovery and rest day guidelines
                    5. Safety considerations for their experience level
                    
                    Make it practical and progressive for their fitness level and goals.
                    """

                    # Get AI responses
                    dietary_response = generate_openai_response(dietary_prompt, openai_api_key)
                    fitness_response = generate_openai_response(fitness_prompt, openai_api_key)

                    # Prepare plan data
                    dietary_plan = {
                        "why_this_plan_works": f"This plan is tailored for {fitness_goals.lower()} with {daily_calories:.0f} daily calories, considering your {activity_level.lower()} lifestyle and {', '.join(dietary_preferences) if dietary_preferences else 'no specific dietary restrictions'}.",
                        "meal_plan": dietary_response,
                        "important_considerations": """
                        • Stay hydrated with 8-10 glasses of water daily
                        • Monitor your energy levels and adjust portions as needed
                        • Include a variety of colors in your fruits and vegetables
                        • Consider meal prep to stay consistent with your plan
                        • Listen to your body's hunger and fullness cues
                        """
                    }

                    fitness_plan = {
                        "goals": f"Achieve {fitness_goals.lower()} through structured {experience_level.lower()}-level training",
                        "routine": fitness_response,
                        "tips": """
                        • Start with proper warm-up every session
                        • Focus on form over speed or weight
                        • Track your workouts to monitor progress
                        • Allow 48 hours rest between training same muscle groups
                        • Stay consistent - results come with time
                        • Adjust intensity based on how you feel
                        """
                    }

                    # Store in session state
                    st.session_state.dietary_plan = dietary_plan
                    st.session_state.fitness_plan = fitness_plan
                    st.session_state.plans_generated = True

                    # Success message
                    st.success("✅ Your personalized health plan has been generated!")
                    st.balloons()

                except Exception as e:
                    st.error(f"❌ An error occurred while generating your plan: {str(e)}")

        # Display generated plans
        if st.session_state.plans_generated:
            st.markdown("---")
            profile = st.session_state.user_profile
            daily_calories = calculate_daily_calories(
                calculate_bmr(profile['weight'], profile['height'], profile['age'], profile['sex']),
                profile['activity_level']
            )
            
            display_dietary_plan(st.session_state.dietary_plan, daily_calories)
            display_fitness_plan(st.session_state.fitness_plan)
            
            # Progress dashboard
            st.markdown("---")
            display_progress_dashboard()
            
            # Action buttons
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("📧 Email Plans", use_container_width=True):
                    st.info("📧 Feature coming soon! You'll be able to email your plans.")
            
            with col2:
                if st.button("📱 Export to App", use_container_width=True):
                    st.info("📱 Mobile app integration coming soon!")
            
            with col3:
                if st.button("🔄 Regenerate Plans", use_container_width=True):
                    st.session_state.plans_generated = False
                    st.experimental_rerun()

if __name__ == "__main__":
    main()
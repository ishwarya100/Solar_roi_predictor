import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import requests
import json

# Helper function for ROI calculation - MOVED TO TOP
def calculate_solar_roi(inputs):
    """
    Enhanced ROI calculation with weather integration
    """
    # Basic assumptions (adjusted based on weather conditions)
    base_solar_irradiance = 5.5  # kWh/m²/day (average for India)
    system_efficiency = 0.85
    panel_cost_per_kw = 45000  # ₹45,000 per kW
    installation_cost_ratio = 0.3  # 30% of panel cost
    
    # Weather adjustment factors
    weather_factors = {
        'Sunny': 1.0,
        'Mostly Sunny': 0.95,
        'Partly Cloudy': 0.85,
        'Cloudy': 0.70,
        'Rainy': 0.60,
        'Very Cloudy': 0.50
    }
    
    # Season adjustment factors
    season_factors = {
        'Summer': 1.15,
        'Winter': 0.80,
        'Monsoon': 0.65,
        'Post-Monsoon': 0.90
    }
    
    # Apply weather adjustments
    weather_factor = weather_factors.get(inputs.get('weather_condition', 'Sunny'), 1.0)
    season_factor = season_factors.get(inputs.get('dominant_season', 'Summer'), 1.0)
    
    # Adjust solar irradiance based on weather
    adjusted_irradiance = base_solar_irradiance * weather_factor * season_factor
    
    # Additional weather-based adjustments
    dust_factor = 1.0
    if inputs.get('dust_pollution', 'Low') == 'High':
        dust_factor = 0.85
    elif inputs.get('dust_pollution', 'Low') == 'Medium':
        dust_factor = 0.92
    
    # Final irradiance calculation
    solar_irradiance = adjusted_irradiance * dust_factor
    
    # Calculate system size needed
    monthly_consumption = inputs['monthly_units']
    system_size = (monthly_consumption * 12) / (solar_irradiance * 365 * system_efficiency)
    
    # Adjust for roof area constraint
    max_system_size = (inputs['rooftop_area'] * 0.7) / 100  # 70% of roof area, 100 sq ft per kW
    system_size = min(system_size, max_system_size)
    
    # Calculate costs
    panel_cost = system_size * panel_cost_per_kw
    installation_cost = panel_cost * installation_cost_ratio
    total_investment = panel_cost + installation_cost
    
    # Calculate generation with weather considerations
    annual_generation = system_size * solar_irradiance * 365 * system_efficiency
    daily_average = annual_generation / 365
    
    # Monthly generation with weather-adjusted seasonal variation
    base_monthly_factors = [0.85, 0.9, 1.0, 1.1, 1.15, 1.1, 1.05, 1.0, 0.95, 0.9, 0.85, 0.8]
    
    # Adjust monthly factors based on weather patterns
    if inputs.get('dominant_season') == 'Monsoon':
        # Reduce generation during monsoon months (Jun-Sep)
        monsoon_adjustment = [1.0, 1.0, 1.0, 1.0, 1.0, 0.7, 0.6, 0.6, 0.8, 1.0, 1.0, 1.0]
        monthly_gen_factors = [base_monthly_factors[i] * monsoon_adjustment[i] for i in range(12)]
    else:
        monthly_gen_factors = base_monthly_factors
    
    monthly_generation = [annual_generation * factor / 12 for factor in monthly_gen_factors]
    
    # Calculate savings
    monthly_savings = min(monthly_consumption, annual_generation/12) * (inputs['monthly_bill']/monthly_consumption)
    annual_savings = monthly_savings * 12
    
    # Calculate payback
    payback_years = total_investment / annual_savings if annual_savings > 0 else 999
    
    # 20-year projections
    years = list(range(1, 21))
    cumulative_savings = [annual_savings * year for year in years]
    total_20_year_savings = annual_savings * 20
    net_profit = total_20_year_savings - total_investment
    
    # Determine suitability with weather considerations
    weather_score_adjustment = weather_factor * 10  # Scale weather impact
    base_score = 60
    
    if payback_years < 5 and annual_generation > monthly_consumption * 10:
        suitability = "Excellent"
        solar_score = min(90, base_score + 30 + weather_score_adjustment)
    elif payback_years < 7 and annual_generation > monthly_consumption * 8:
        suitability = "Good"
        solar_score = min(85, base_score + 15 + weather_score_adjustment)
    else:
        suitability = "Average"
        solar_score = min(75, base_score + weather_score_adjustment)
    
    return {
        'suitability': suitability,
        'solar_score': solar_score,
        'system_size': system_size,
        'total_investment': total_investment,
        'annual_generation': annual_generation,
        'daily_average': daily_average,
        'peak_sun_hours': solar_irradiance,
        'monthly_generation': monthly_generation,
        'monthly_savings': monthly_savings,
        'annual_savings': annual_savings,
        'payback_years': payback_years,
        'annual_roi': (annual_savings / total_investment) * 100 if total_investment > 0 else 0,
        'cumulative_savings': cumulative_savings,
        'total_20_year_savings': total_20_year_savings,
        'net_profit': net_profit,
        'weather_impact': weather_factor,
        'effective_irradiance': solar_irradiance
    }

# Page configuration
st.set_page_config(
    page_title="Smart Solar ROI Predictor for MSMEs",
    page_icon="☀️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #ff6b35, #f7931e);
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        text-align: center;
        color: white;
    }
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #ff6b35;
        margin: 0.5rem 0;
    }
    .result-container {
        background: #f8f9fa;
        padding: 1.5rem;
        border-radius: 10px;
        margin-top: 1rem;
    }
    .weather-info {
        background: #e3f2fd;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #2196f3;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div class="main-header">
    <h1>🌞 Smart Solar ROI Predictor for MSMEs</h1>
    <p>Discover if solar energy is right for your business - Get instant ROI analysis with weather intelligence!</p>
</div>
""", unsafe_allow_html=True)

# Sidebar for navigation
with st.sidebar:
    st.header("📋 Navigation")
    page = st.selectbox("Choose Section", 
                       ["📝 Input Details", "📊 Results & Analysis", "💡 Recommendations"])
    
    st.markdown("---")
    st.markdown("### How It Works")
    st.markdown("""
    1. **Enter Business Details**
    2. **Provide Weather Information**
    3. **AI Analyzes Solar Potential**
    4. **Get Weather-Adjusted ROI**
    5. **View Smart Recommendations**
    """)

# Initialize session state
if 'calculated' not in st.session_state:
    st.session_state.calculated = False
if 'results' not in st.session_state:
    st.session_state.results = {}

# Page 1: Input Details
if page == "📝 Input Details":
    st.header("🏢 Enter Your Business Details")
    
    # Create two columns for better layout
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📍 Location & Property Details")
        
        indian_cities = [
    "Agartala", "Agra", "Ahmedabad", "Ahmednagar", "Aizawl", "Ajmer", "Akola", "Alappuzha", "Aligarh",
    "Allahabad", "Alwar", "Ambala", "Amravati", "Amritsar", "Anantapur", "Anand", "Asansol", "Aurangabad",
    "Azamgarh", "Bangalore", "Baran", "Bareilly", "Bathinda", "Begusarai", "Belagavi", "Bellary", "Berhampur",
    "Bhagalpur", "Bharatpur", "Bharuch", "Bhavnagar", "Bhilai", "Bhilwara", "Bhopal", "Bhubaneswar", "Bhuj",
    "Bidar", "Bikaner", "Bilaspur", "Bokaro", "Chandigarh", "Chandrapur", "Chennai", "Chhindwara", "Chittoor",
    "Coimbatore", "Cuttack", "Daman", "Darbhanga", "Darjeeling", "Davanagere", "Dehradun", "Delhi", "Dewas",
    "Dhanbad", "Dhar", "Dhule", "Dibrugarh", "Dindigul", "Dispur", "Durg", "Durgapur", "Erode", "Etawah",
    "Faizabad", "Faridabad", "Farrukhabad", "Fatehpur", "Firozabad", "Gandhinagar", "Gaya", "Ghaziabad",
    "Ghazipur", "Gorakhpur", "Greater Noida", "Gulbarga", "Guna", "Guntur", "Gurgaon", "Guwahati", "Gwalior",
    "Hajipur", "Haldia", "Haldwani", "Haridwar", "Hassan", "Hisar", "Hosur", "Hubli", "Hyderabad", "Ichalkaranji",
    "Imphal", "Indore", "Itanagar", "Jabalpur", "Jagdalpur", "Jagraon", "Jaipur", "Jalandhar", "Jalgaon", "Jammu",
    "Jamnagar", "Jamshedpur", "Jhansi", "Jhunjhunu", "Jodhpur", "Junagadh", "Kadapa", "Kaithal", "Kakinada",
    "Kalaburagi", "Kalyan", "Kanchipuram", "Kannur", "Kanpur", "Kapurthala", "Karimnagar", "Karnal", "Karur",
    "Katni", "Kharagpur", "Kochi", "Kolhapur", "Kolkata", "Kollam", "Korba", "Kota", "Kottayam", "Kozhikode",
    "Krishnanagar", "Kurnool", "Latur", "Loni", "Lucknow", "Ludhiana", "Madurai", "Maheshtala", "Malda",
    "Malegaon", "Mangalore", "Mathura", "Meerut", "Mirzapur", "Moradabad", "Morena", "Mumbai", "Muzaffarnagar",
    "Muzaffarpur", "Mysore", "Nadiad", "Nagapattinam", "Nagercoil", "Nagpur", "Nanded", "Nashik", "Navi Mumbai",
    "Neemuch", "Nellore", "Nizamabad", "Noida", "Ongole", "Orai", "Ooty", "Palakkad", "Palanpur", "Pali",
    "Panaji", "Panchkula", "Panipat", "Parbhani", "Pathankot", "Patiala", "Patna", "Pimpri-Chinchwad", "Porbandar",
    "Prayagraj", "Puducherry", "Pune", "Puri", "Raebareli", "Raichur", "Raigarh", "Raipur", "Rajahmundry",
    "Rajkot", "Ranchi", "Ratlam", "Rewa", "Rewari", "Rohtak", "Roorkee", "Rourkela", "Sagar", "Saharanpur",
    "Salem", "Sambalpur", "Sangli", "Sangrur", "Satara", "Satna", "Secunderabad", "Serampore", "Shillong",
    "Shimla", "Shivpuri", "Sikar", "Silchar", "Siliguri", "Solapur", "Sonipat", "Srinagar", "Surat", "Tenali",
    "Tezpur", "Thane", "Thanjavur", "Thiruvananthapuram", "Thoothukudi", "Thrissur", "Tinsukia", "Tiruchirappalli",
    "Tirunelveli", "Tirupati", "Tiruppur", "Tiruvannamalai", "Udaipur", "Udupi", "Ujjain", "Ulhasnagar",
    "Una", "Unnao", "Vadodara", "Valsad", "Varanasi", "Vasai-Virar", "Vellore", "Vidisha", "Vijayawada",
    "Viluppuram", "Virar", "Visakhapatnam", "Warangal", "Wardha", "Yamunanagar",      "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh", "Goa",
    "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka", "Kerala",
    "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram", "Nagaland",
    "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana",
    "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal",
    "Andaman and Nicobar Islands", "Chandigarh", "Dadra and Nagar Haveli and Daman and Diu",
    "Delhi", "Jammu and Kashmir", "Ladakh", "Lakshadweep", "Puducherry"
]
        location = st.selectbox(
                    "Select Your Business Location", 
                    [""] + sorted(indian_cities),
                    index=0
        )

        # Rooftop area
        area_method = st.radio("How do you want to provide rooftop area?", 
                              ["Manual Input", "Estimate from Building Size"])
        
        if area_method == "Manual Input":
            rooftop_area = st.number_input("Available Rooftop Area (sq ft)", 
                                          min_value=100, max_value=10000, value=1000)
        else:
            building_length = st.number_input("Building Length (ft)", min_value=10, value=50)
            building_width = st.number_input("Building Width (ft)", min_value=10, value=40)
            rooftop_area = building_length * building_width
            st.info(f"Estimated rooftop area: {rooftop_area} sq ft")
        
        # Roof details
        roof_type = st.selectbox("🏠 Roof Type", 
                                ["Flat Roof", "Sloped Roof", "Mixed"])
        
        roof_condition = st.selectbox("Roof Condition", 
                                     ["Excellent", "Good", "Average", "Needs Repair"])
    
    with col2:
        st.subheader("⚡ Electricity Usage Details")
        
        # Business type
        business_type = st.selectbox("🏢 Type of Business", [
            "Manufacturing", "Retail Store", "Office", "Restaurant", 
            "Hospital/Clinic", "School", "Warehouse", "Hotel", "Other"
        ])
        
        # Electricity bill method
        bill_method = st.radio("How do you want to provide electricity data?", 
                              ["Monthly Bill Amount", "Monthly Units (kWh)"])
        
        if bill_method == "Monthly Bill Amount":
            monthly_bill = st.number_input("Average Monthly Electricity Bill (₹)", 
                                          min_value=1000, max_value=100000, value=15000)
            # Estimate units based on average tariff
            avg_tariff = st.slider("Average Electricity Rate (₹/kWh)", 
                                  min_value=3.0, max_value=12.0, value=6.5)
            monthly_units = monthly_bill / avg_tariff
            st.info(f"Estimated monthly consumption: {monthly_units:.0f} kWh")
        else:
            monthly_units = st.number_input("Monthly Electricity Consumption (kWh)", 
                                           min_value=500, max_value=20000, value=2000)
            avg_tariff = st.slider("Average Electricity Rate (₹/kWh)", 
                                  min_value=3.0, max_value=12.0, value=6.5)
            monthly_bill = monthly_units * avg_tariff
            st.info(f"Estimated monthly bill: ₹{monthly_bill:.0f}")
        
        # Operating hours
        operating_hours = st.slider("🕐 Daily Operating Hours", 
                                   min_value=6, max_value=24, value=10)
        
        # Budget
        budget_range = st.selectbox("💰 Budget Range for Solar Installation", [
            "₹1-3 Lakhs", "₹3-5 Lakhs", "₹5-10 Lakhs", "₹10-20 Lakhs", "₹20+ Lakhs"
        ])

    # NEW WEATHER SECTION
    st.subheader("🌤️ Weather & Environmental Conditions")
    
    col5, col6 = st.columns(2)
    
    with col5:
        st.markdown("##### Current Weather Patterns")
        
        # Current weather condition
        weather_condition = st.selectbox("☀️ Typical Weather Condition", [
            "Sunny", "Mostly Sunny", "Partly Cloudy", "Cloudy", "Rainy", "Very Cloudy"
        ])
        
        # Dominant season
        dominant_season = st.selectbox("🌿 Dominant Season (Most of the Year)", [
            "Summer", "Winter", "Monsoon", "Post-Monsoon"
        ])
        
        # Average sunny days
        sunny_days = st.slider("☀️ Average Sunny Days per Month", 
                              min_value=5, max_value=30, value=20)
        
        # Temperature range
        temp_range = st.selectbox("🌡️ Average Temperature Range", [
            "Very Hot (>40°C)", "Hot (30-40°C)", "Moderate (20-30°C)", 
            "Cool (10-20°C)", "Cold (<10°C)"
        ])
    
    with col6:
        st.markdown("##### Environmental Factors")
        
        # Dust and pollution
        dust_pollution = st.selectbox("🌫️ Dust/Air Pollution Level", [
            "Low", "Medium", "High"
        ])
        
        # Shading issues
        shading_issues = st.selectbox("🌳 Roof Shading Issues", [
            "No Shading", "Partial Shading (Morning)", "Partial Shading (Afternoon)", 
            "Heavy Shading", "Seasonal Shading"
        ])
        
        # Monsoon intensity
        monsoon_intensity = st.selectbox("🌧️ Monsoon Intensity", [
            "Light", "Moderate", "Heavy", "Very Heavy"
        ])
        
        # Wind conditions
        wind_conditions = st.selectbox("💨 Wind Conditions", [
            "Calm", "Light Breeze", "Moderate Wind", "Strong Wind", "Very Windy"
        ])
    
    # Weather impact info
    st.markdown("""
    <div class="weather-info">
        <h4>🌦️ Weather Impact on Solar Performance</h4>
        <p><strong>Why weather matters:</strong> Solar panel efficiency depends heavily on sunlight exposure, 
        temperature, and environmental conditions. Our AI considers these factors to give you accurate ROI predictions.</p>
        <ul>
            <li><strong>Sunny conditions:</strong> Maximum solar generation</li>
            <li><strong>Cloudy/Rainy days:</strong> Reduced but still significant generation</li>
            <li><strong>Dust/Pollution:</strong> Can reduce efficiency by 10-20%</li>
            <li><strong>Temperature:</strong> Extreme heat can slightly reduce efficiency</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
    
    # Additional details
    st.subheader("📋 Additional Information")
    col3, col4 = st.columns(2)
    
    with col3:
        priority = st.selectbox("🎯 Primary Goal", [
            "Reduce Electricity Bills", "Environmental Impact", "Energy Independence", 
            "Government Incentives", "Increase Property Value"
        ])
        
        timeline = st.selectbox("⏱️ Expected Installation Timeline", [
            "Within 3 months", "3-6 months", "6-12 months", "Just exploring"
        ])
    
    with col4:
        previous_solar = st.radio("🔄 Previous Solar Experience?", ["No", "Yes"])
        
        if previous_solar == "Yes":
            solar_experience = st.text_area("Tell us about your previous solar experience")
        
        # Contact for follow-up
        contact_consent = st.checkbox("📞 I consent to be contacted for solar installation quotes")
    
    # Calculate button
    st.markdown("---")
    if st.button("🚀 Calculate Weather-Adjusted Solar ROI", type="primary", use_container_width=True):
        if location and rooftop_area > 0 and monthly_units > 0:
            # Store inputs in session state
            st.session_state.inputs = {
                'location': location,
                'rooftop_area': rooftop_area,
                'monthly_units': monthly_units,
                'monthly_bill': monthly_bill,
                'business_type': business_type,
                'operating_hours': operating_hours,
                'budget_range': budget_range,
                'roof_type': roof_type,
                'roof_condition': roof_condition,
                'priority': priority,
                'timeline': timeline,
                'contact_consent': contact_consent,
                # Weather parameters
                'weather_condition': weather_condition,
                'dominant_season': dominant_season,
                'sunny_days': sunny_days,
                'temp_range': temp_range,
                'dust_pollution': dust_pollution,
                'shading_issues': shading_issues,
                'monsoon_intensity': monsoon_intensity,
                'wind_conditions': wind_conditions
            }
            
            # Perform calculations
            st.session_state.results = calculate_solar_roi(st.session_state.inputs)
            st.session_state.calculated = True
            
            st.success("✅ Weather-adjusted calculation completed! Go to 'Results & Analysis' to view your detailed report.")
        else:
            st.error("⚠️ Please fill in all required fields: Location, Rooftop Area, and Electricity Consumption")

# Page 2: Results & Analysis
elif page == "📊 Results & Analysis":
    if st.session_state.calculated:
        st.header("📈 Your Weather-Adjusted Solar ROI Analysis Report")
        
        results = st.session_state.results
        inputs = st.session_state.inputs
        
        # Weather impact summary
        st.markdown("""
        <div class="weather-info">
            <h4>🌤️ Weather Impact Analysis</h4>
        </div>
        """, unsafe_allow_html=True)
        
        col_weather1, col_weather2, col_weather3 = st.columns(3)
        
        with col_weather1:
            st.metric("🌤️ Weather Impact Factor", f"{results['weather_impact']:.2f}", 
                     delta="1.0 = Ideal" if results['weather_impact'] >= 1.0 else "Below Ideal")
        
        with col_weather2:
            st.metric("☀️ Effective Solar Irradiance", f"{results['effective_irradiance']:.1f} kWh/m²/day")
        
        with col_weather3:
            weather_status = "Excellent" if results['weather_impact'] >= 0.95 else "Good" if results['weather_impact'] >= 0.85 else "Fair"
            st.metric("🌈 Weather Suitability", weather_status)
        
        # Summary metrics
        st.markdown("---")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("🌟 Solar Suitability", results['suitability'], 
                     delta=f"{results['solar_score']}/100")
        
        with col2:
            st.metric("💰 Total Investment", f"₹{results['total_investment']:,.0f}")
        
        with col3:
            st.metric("⏱️ Payback Period", f"{results['payback_years']:.1f} years")
        
        with col4:
            st.metric("📊 Annual ROI", f"{results['annual_roi']:.1f}%")
        
        # Detailed results
        st.markdown("---")
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("☀️ Weather-Adjusted Solar Generation")
            
            # Solar generation chart
            months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                     'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            generation = results['monthly_generation']
            
            fig = go.Figure()
            fig.add_trace(go.Bar(x=months, y=generation, 
                               name='Solar Generation (kWh)',
                               marker_color='orange'))
            fig.update_layout(title="Monthly Solar Generation Forecast (Weather-Adjusted)",
                            xaxis_title="Month",
                            yaxis_title="Generation (kWh)")
            st.plotly_chart(fig, use_container_width=True)
            
            # Key metrics
            st.markdown(f"""
            **Solar System Details:**
            - **System Size**: {results['system_size']:.1f} kW
            - **Annual Generation**: {results['annual_generation']:,.0f} kWh
            - **Daily Average**: {results['daily_average']:.1f} kWh
            - **Weather-Adjusted Irradiance**: {results['effective_irradiance']:.1f} kWh/m²/day
            """)
            
            # Weather conditions summary
            st.markdown(f"""
            **Weather Conditions:**
            - **Typical Weather**: {inputs['weather_condition']}
            - **Dominant Season**: {inputs['dominant_season']}
            - **Sunny Days/Month**: {inputs['sunny_days']} days
            - **Dust/Pollution**: {inputs['dust_pollution']}
            """)
        
        with col2:
            st.subheader("💵 Financial Projections")
            
            # ROI over time
            years = list(range(1, 21))
            cumulative_savings = results['cumulative_savings']
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=years, y=cumulative_savings, 
                                   mode='lines+markers',
                                   name='Cumulative Savings',
                                   line=dict(color='green', width=3)))
            fig.add_hline(y=results['total_investment'], 
                         line_dash="dash", line_color="red",
                         annotation_text="Break-even Point")
            fig.update_layout(title="20-Year Savings Projection (Weather-Adjusted)",
                            xaxis_title="Year",
                            yaxis_title="Cumulative Savings (₹)")
            st.plotly_chart(fig, use_container_width=True)
            
            # Financial summary
            st.markdown(f"""
            **Financial Summary:**
            - **Monthly Savings**: ₹{results['monthly_savings']:,.0f}
            - **Annual Savings**: ₹{results['annual_savings']:,.0f}
            - **20-Year Savings**: ₹{results['total_20_year_savings']:,.0f}
            - **Net Profit (20 years)**: ₹{results['net_profit']:,.0f}
            """)
        
        # Weather-specific recommendations
        st.markdown("---")
        st.subheader("🌤️ Weather-Specific Insights")
        
        # Generate weather-specific recommendations
        weather_recommendations = []
        
        if inputs['weather_condition'] in ['Cloudy', 'Very Cloudy']:
            weather_recommendations.append("⚠️ Consider high-efficiency panels for cloudy conditions")
        
        if inputs['dust_pollution'] == 'High':
            weather_recommendations.append("🧹 Plan for regular panel cleaning (monthly)")
        
        if inputs['dominant_season'] == 'Monsoon':
            weather_recommendations.append("☔ Consider waterproof mounting and drainage systems")
        
        if inputs['monsoon_intensity'] in ['Heavy', 'Very Heavy']:
            weather_recommendations.append("🌧️ Ensure robust structural support for heavy rains")
        
            if inputs['wind_conditions'] in ['Strong Wind', 'Very Windy']:
                weather_recommendations.append("💨 Install wind-resistant mounting systems")

        # Display recommendations
        if weather_recommendations:
            for rec in weather_recommendations:
                st.markdown(f"- {rec}")
        else:
            st.success("✅ No major weather-related issues detected. Standard installation should suffice.")

# Page 3: Recommendations
elif page == "💡 Recommendations":
    if st.session_state.calculated:
        st.header("💡 Smart Solar Recommendations")
        
        inputs = st.session_state.inputs
        results = st.session_state.results
        
        st.subheader("📌 Summary")
        st.markdown(f"""
        Based on your business details and environmental conditions in **{inputs['location']}**, here are our top insights:
        - **Solar Suitability:** {results['suitability']}
        - **Payback Period:** {results['payback_years']:.1f} years
        - **Net Profit over 20 Years:** ₹{results['net_profit']:,.0f}
        """)
        
        st.markdown("---")
        st.subheader("✅ Recommended Next Steps")
        
        st.markdown("""
        1. **Contact local solar vendors** for quotes within your budget range.
        2. **Request site inspection** to confirm roof conditions and shading analysis.
        3. **Evaluate subsidy opportunities** available in your state or through central government schemes.
        4. **Plan maintenance** – especially if pollution or heavy monsoon is present.
        5. **Track generation** using a smart solar monitoring app post-installation.
        """)
        
        if inputs['contact_consent']:
            st.success("📞 Thanks! A solar expert may reach out with relevant offers.")
        else:
            st.info("📩 You can also share this report with your local installer.")

    else:
        st.warning("🚧 Please complete the input section and calculation first.")

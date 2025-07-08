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
    Simplified ROI calculation - in a real app, this would use actual APIs
    """
    # Basic assumptions (would be API-driven in production)
    solar_irradiance = 5.5  # kWh/m²/day (average for India)
    system_efficiency = 0.85
    panel_cost_per_kw = 45000  # ₹45,000 per kW
    installation_cost_ratio = 0.3  # 30% of panel cost
    
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
    
    # Calculate generation
    annual_generation = system_size * solar_irradiance * 365 * system_efficiency
    daily_average = annual_generation / 365
    
    # Monthly generation (simplified seasonal variation)
    monthly_gen_factors = [0.85, 0.9, 1.0, 1.1, 1.15, 1.1, 1.05, 1.0, 0.95, 0.9, 0.85, 0.8]
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
    
    # Determine suitability
    if payback_years < 5 and annual_generation > monthly_consumption * 10:
        suitability = "Excellent"
        solar_score = 90
    elif payback_years < 7 and annual_generation > monthly_consumption * 8:
        suitability = "Good"
        solar_score = 75
    else:
        suitability = "Average"
        solar_score = 60
    
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
        'net_profit': net_profit
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
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div class="main-header">
    <h1>🌞 Smart Solar ROI Predictor for MSMEs</h1>
    <p>Discover if solar energy is right for your business - Get instant ROI analysis!</p>
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
    2. **AI Analyzes Solar Potential**
    3. **Get ROI Predictions**
    4. **View Recommendations**
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
    if st.button("🚀 Calculate Solar ROI", type="primary", use_container_width=True):
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
                'timeline': timeline
            }
            
            # Perform calculations
            st.session_state.results = calculate_solar_roi(st.session_state.inputs)
            st.session_state.calculated = True
            
            st.success("✅ Calculation completed! Go to 'Results & Analysis' to view your report.")
        else:
            st.error("⚠️ Please fill in all required fields: Location, Rooftop Area, and Electricity Consumption")

# Page 2: Results & Analysis
elif page == "📊 Results & Analysis":
    if st.session_state.calculated:
        st.header("📈 Your Solar ROI Analysis Report")
        
        results = st.session_state.results
        
        # Summary metrics
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
            st.subheader("☀️ Solar Generation Analysis")
            
            # Solar generation chart
            months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                     'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            generation = results['monthly_generation']
            
            fig = go.Figure()
            fig.add_trace(go.Bar(x=months, y=generation, 
                               name='Solar Generation (kWh)',
                               marker_color='orange'))
            fig.update_layout(title="Monthly Solar Generation Forecast",
                            xaxis_title="Month",
                            yaxis_title="Generation (kWh)")
            st.plotly_chart(fig, use_container_width=True)
            
            # Key metrics
            st.markdown(f"""
            **Solar System Details:**
            - **System Size**: {results['system_size']:.1f} kW
            - **Annual Generation**: {results['annual_generation']:,.0f} kWh
            - **Daily Average**: {results['daily_average']:.1f} kWh
            - **Peak Sun Hours**: {results['peak_sun_hours']:.1f} hours
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
            fig.update_layout(title="20-Year Savings Projection",
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
        
        # Recommendations
        st.markdown("---")
        st.subheader("🎯 Recommendations")
        
        if results['suitability'] == "Excellent":
            st.success("""
            ✅ **Highly Recommended**: Your location has excellent solar potential! 
            This is a great investment opportunity with strong returns.
            """)
        elif results['suitability'] == "Good":
            st.info("""
            ✅ **Recommended**: Good solar potential with decent returns. 
            Consider proceeding with the installation.
            """)
        else:
            st.warning("""
            ⚠️ **Consider Carefully**: Moderate solar potential. 
            You might want to explore additional energy efficiency measures first.
            """)
        
        # Action items
        st.markdown("### 🚀 Next Steps")
        st.markdown("""
        1. **Get Multiple Quotes**: Contact 3-4 local solar installers
        2. **Check Subsidies**: Explore available government incentives
        3. **Financing Options**: Consider solar loans or leasing
        4. **Site Survey**: Schedule a detailed technical assessment
        """)
        
    else:
        st.warning("⚠️ Please complete the input form first to see your results.")
        st.markdown("👈 Go to 'Input Details' to enter your business information.")

# Page 3: Recommendations
elif page == "💡 Recommendations":
    st.header("🔗 Resources & Recommendations")
    
    if st.session_state.calculated:
        st.success("Based on your analysis, here are personalized recommendations:")
        
        # Tabs for different recommendations
        tab1, tab2, tab3, tab4 = st.tabs(["🏭 Installers", "💰 Financing", "🎁 Subsidies", "📚 Resources"])
        
        with tab1:
            st.subheader("Recommended Solar Installers")
            # This would integrate with a database of local installers
            st.markdown("""
            **Top Rated Installers in Your Area:**
            1. **SolarMax Solutions** - ⭐⭐⭐⭐⭐ (4.8/5) - Contact: +91-9876543210
            2. **GreenTech Energy** - ⭐⭐⭐⭐ (4.5/5) - Contact: +91-9876543211
            3. **EcoSolar Systems** - ⭐⭐⭐⭐ (4.3/5) - Contact: +91-9876543212
            
            💡 **Tip**: Get quotes from at least 3 installers to compare prices and services.
            """)
        
        with tab2:
            st.subheader("Financing Options")
            st.markdown("""
            **Available Financing:**
            1. **Solar Loans** - 8-12% interest, 5-10 year terms
            2. **MSME Loans** - Special rates for small businesses
            3. **Leasing Options** - No upfront cost, monthly payments
            4. **Government Schemes** - Subsidized financing available
            """)
        
        with tab3:
            st.subheader("Government Subsidies & Incentives")
            st.markdown("""
            **Available Incentives:**
            1. **Central Government**: 20% subsidy on solar installations
            2. **State Incentives**: Additional 10-15% subsidy (varies by state)
            3. **Tax Benefits**: Accelerated depreciation, tax deductions
            4. **Net Metering**: Sell excess power back to grid
            """)
        
        with tab4:
            st.subheader("Additional Resources")
            st.markdown("""
            **Useful Links:**
            - [Solar Rooftop Portal](https://solarrooftop.gov.in/)
            - [MNRE Guidelines](https://mnre.gov.in/)
            - [State Solar Policies](https://www.solar-energy.org/)
            - [Solar Calculator Tools](https://www.solar-calculator.com/)
            """)
    
    else:
        st.info("Complete your solar analysis first to get personalized recommendations!")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; padding: 1rem;'>
    <p>🌱 <strong>Smart Solar ROI Predictor</strong> | Empowering MSMEs with Solar Intelligence</p>
    <p>Made with ❤️ for a sustainable future | © 2024</p>
</div>
""", unsafe_allow_html=True)
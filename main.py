import streamlit as st
import requests
import plotly.express as px
import pandas as pd
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

st.set_page_config(
    page_title="Student Budget Calc",
    page_icon="💰",
    layout="wide"
)

# Initialize session state - had issues with widgets resetting
if 'rent' not in st.session_state:
    st.session_state.rent = 0
if 'food' not in st.session_state:
    st.session_state.food = 0  
if 'utilities' not in st.session_state:
    st.session_state.utilities = 0
if 'transportation' not in st.session_state:
    st.session_state.transportation = 0
if 'misc' not in st.session_state:
    st.session_state.misc = 0

# Custom CSS because default streamlit looks terrible
st.markdown("""
<style>
.stApp {
    background-color: #0e1117;
    color: #ffffff;
}
.title-section {
    text-align: center;
    padding: 20px 0;
    margin-bottom: 30px;
    border-bottom: 1px solid #333;
}
.expense-card {
    background: #1a1a1a;
    border-radius: 8px;
    padding: 15px;
    margin: 8px 0;
    border-left: 3px solid #ff6b6b;
}
.high-cost { color: #ff6b6b; }
.low-cost { color: #51cf66; }
.avg-cost { color: #ffd43b; }
</style>
""", unsafe_allow_html=True)

# Rough cost estimates from when I was researching this stuff
# Numbers are approximate based on student forums and cost of living sites
LIVING_COSTS = {
    'California': {'rent': 1800, 'food': 450, 'utilities': 150, 'transportation': 120, 'misc': 350},
    'New York': {'rent': 1700, 'food': 420, 'utilities': 140, 'transportation': 110, 'misc': 330},
    'Massachusetts': {'rent': 1600, 'food': 400, 'utilities': 135, 'transportation': 105, 'misc': 310},
    'Hawaii': {'rent': 2100, 'food': 550, 'utilities': 180, 'transportation': 140, 'misc': 400},
    'Washington': {'rent': 1450, 'food': 380, 'utilities': 130, 'transportation': 100, 'misc': 290},
    'Oregon': {'rent': 1350, 'food': 370, 'utilities': 125, 'transportation': 95, 'misc': 270},
    'Colorado': {'rent': 1300, 'food': 360, 'utilities': 120, 'transportation': 90, 'misc': 250},
    'Florida': {'rent': 1200, 'food': 340, 'utilities': 145, 'transportation': 85, 'misc': 230},
    'Texas': {'rent': 1100, 'food': 320, 'utilities': 125, 'transportation': 80, 'misc': 220},
    'Illinois': {'rent': 1150, 'food': 330, 'utilities': 115, 'transportation': 85, 'misc': 230},
    'North Carolina': {'rent': 950, 'food': 300, 'utilities': 110, 'transportation': 75, 'misc': 190},
    'Georgia': {'rent': 1000, 'food': 310, 'utilities': 115, 'transportation': 75, 'misc': 200},
    'Arizona': {'rent': 1050, 'food': 320, 'utilities': 125, 'transportation': 80, 'misc': 210},
    'Tennessee': {'rent': 900, 'food': 280, 'utilities': 105, 'transportation': 70, 'misc': 170},
    'Ohio': {'rent': 850, 'food': 290, 'utilities': 100, 'transportation': 70, 'misc': 180},
    'Pennsylvania': {'rent': 950, 'food': 310, 'utilities': 110, 'transportation': 75, 'misc': 190},
    'Michigan': {'rent': 850, 'food': 300, 'utilities': 105, 'transportation': 70, 'misc': 180},
    'Virginia': {'rent': 1150, 'food': 330, 'utilities': 120, 'transportation': 85, 'misc': 230},
    'Indiana': {'rent': 800, 'food': 280, 'utilities': 95, 'transportation': 65, 'misc': 160},
    'Oklahoma': {'rent': 750, 'food': 270, 'utilities': 90, 'transportation': 60, 'misc': 150},
    'West Virginia': {'rent': 700, 'food': 260, 'utilities': 85, 'transportation': 55, 'misc': 140}
}

# Exchange rate stuff - using free APIs
EXCHANGE_RATES = {
    'USD': {'name': 'US Dollar', 'symbol': '$'}, 
    'EUR': {'name': 'Euro', 'symbol': '€'}, 
    'GBP': {'name': 'British Pound', 'symbol': '£'}, 
    'JPY': {'name': 'Japanese Yen', 'symbol': '¥'},
    'CAD': {'name': 'Canadian Dollar', 'symbol': 'C$'}, 
    'AUD': {'name': 'Australian Dollar', 'symbol': 'A$'}, 
    'CHF': {'name': 'Swiss Franc', 'symbol': 'CHF'},
    'CNY': {'name': 'Chinese Yuan', 'symbol': '¥'}, 
    'INR': {'name': 'Indian Rupee', 'symbol': '₹'}, 
    'KRW': {'name': 'South Korean Won', 'symbol': '₩'}
}

def fetch_exchange_rate(from_currency, to_currency):
    """Get exchange rate between two currencies"""
    if from_currency == to_currency:
        return 1.0
    
    try:
        # Using exchangerate-api.com - free tier should be enough
        url = f"https://api.exchangerate-api.com/v4/latest/{from_currency}"
        response = requests.get(url, timeout=5)
        data = response.json()
        
        if to_currency in data.get('rates', {}):
            return data['rates'][to_currency]
        else:
            # Fallback to hardcoded rates if API fails
            return get_fallback_rate(from_currency, to_currency)
    except:
        return get_fallback_rate(from_currency, to_currency)

def get_fallback_rate(from_curr, to_curr):
    """Backup exchange rates in case API is down"""
    # These are rough estimates, not exact
    rates = {
        ('USD', 'EUR'): 0.85,
        ('USD', 'GBP'): 0.75,
        ('USD', 'JPY'): 150,
        ('USD', 'CAD'): 1.35,
        ('USD', 'AUD'): 1.50,
        ('USD', 'CHF'): 0.90,
        ('USD', 'CNY'): 7.20,
        ('USD', 'INR'): 83.0,
        ('USD', 'KRW'): 1300,
        ('EUR', 'USD'): 1.18,
        ('GBP', 'USD'): 1.25,
        ('JPY', 'USD'): 0.0067,
        ('CAD', 'USD'): 0.74,
        ('AUD', 'USD'): 0.67,
        ('CHF', 'USD'): 1.11,
        ('CNY', 'USD'): 0.14,
        ('INR', 'USD'): 0.012,
        ('KRW', 'USD'): 0.00077
    }
    return rates.get((from_curr, to_curr), 1.0)

# Cache exchange rates for 30 minutes
@st.cache_data(ttl=1800)
def get_cached_rate(from_curr, to_curr):
    return fetch_exchange_rate(from_curr, to_curr)

# Main app
st.markdown('<div class="title-section"><h1>💰 Student Budget Calculator</h1><p>Calculate living costs for studying in the US</p></div>', unsafe_allow_html=True)

# Sidebar for currency selection
with st.sidebar:
    st.header("💱 Currency Settings")
    
    home_currency = st.selectbox(
        "Your home currency:",
        options=list(EXCHANGE_RATES.keys()),
        format_func=lambda x: f"{x} - {EXCHANGE_RATES[x]['name']}",
        index=0
    )
    
    study_currency = st.selectbox(
        "Study destination currency:",
        options=list(EXCHANGE_RATES.keys()),
        format_func=lambda x: f"{x} - {EXCHANGE_RATES[x]['name']}",
        index=0
    )
    
    # Get exchange rate
    if home_currency != study_currency:
        exchange_rate = get_cached_rate(study_currency, home_currency)
        st.info(f"1 {study_currency} = {exchange_rate:.4f} {home_currency}")
    else:
        exchange_rate = 1.0
        st.info("Same currency")
    
    # Quick converter - I keep needing this
    st.markdown("---")
    st.subheader("🔄 Convert")
    convert_amount = st.number_input(
        f"{study_currency}:",
        min_value=0.0,
        step=100.0,
        value=1000.0,
        key="converter"
    )
    
    if convert_amount > 0:
        converted = convert_amount * exchange_rate
        st.success(f"{convert_amount:,.0f} {study_currency} = {converted:,.2f} {home_currency}")

# Main content area
col1, col2 = st.columns([1.5, 1])

with col1:
    st.subheader("📍 Study Location & Duration")
    
    location_col, duration_col = st.columns(2)
    
    with location_col:
        selected_state = st.selectbox(
            "State:", 
            options=list(LIVING_COSTS.keys()),
            index=0
        )
    
    with duration_col:
        study_months = st.slider(
            "Duration (months):", 
            min_value=3, max_value=60, value=12, step=3
        )
    
    st.subheader("💸 Monthly Expenses (USD)")
    
    # Get reference costs for the selected state
    reference_costs = LIVING_COSTS[selected_state]
    
    # Input fields
    expense_col1, expense_col2, reference_col = st.columns([2, 2, 1])
    
    with expense_col1:
        rent = st.number_input(
            "🏠 Housing/Rent:", 
            min_value=0, max_value=5000, step=50, 
            value=st.session_state.rent,
            key="rent_input"
        )
        
        utilities = st.number_input(
            "⚡ Utilities:", 
            min_value=0, max_value=500, step=25, 
            value=st.session_state.utilities,
            key="utilities_input"
        )
        
        misc = st.number_input(
            "🛍️ Miscellaneous:", 
            min_value=0, max_value=1000, step=25, 
            value=st.session_state.misc,
            key="misc_input"
        )
    
    with expense_col2:
        food = st.number_input(
            "🍕 Food & Groceries:", 
            min_value=0, max_value=1000, step=25, 
            value=st.session_state.food,
            key="food_input"
        )
        
        transportation = st.number_input(
            "🚗 Transportation:", 
            min_value=0, max_value=500, step=25, 
            value=st.session_state.transportation,
            key="transport_input"
        )
    
    with reference_col:
        st.write(f"**{selected_state} avg:**")
        st.write(f"${reference_costs['rent']}")
        st.write(f"${reference_costs['utilities']}")
        st.write(f"${reference_costs['misc']}")
        st.write(f"${reference_costs['food']}")
        st.write(f"${reference_costs['transportation']}")
    
    # Quick action buttons
    button_col1, button_col2 = st.columns(2)
    
    with button_col1:
        if st.button("📋 Use Average Values", use_container_width=True):
            st.session_state.rent = reference_costs['rent']
            st.session_state.food = reference_costs['food']
            st.session_state.utilities = reference_costs['utilities']
            st.session_state.transportation = reference_costs['transportation']
            st.session_state.misc = reference_costs['misc']
            st.rerun()
    
    with button_col2:
        if st.button("🔄 Clear All", use_container_width=True):
            for key in ['rent', 'food', 'utilities', 'transportation', 'misc']:
                st.session_state[key] = 0
            st.rerun()

# Results section
with col2:
    st.subheader("💰 Cost Summary")
    
    # Calculate totals
    monthly_total_usd = rent + food + utilities + transportation + misc
    monthly_total_home = monthly_total_usd * exchange_rate
    total_cost_period = monthly_total_home * study_months
    
    # Monthly cost display
    st.markdown(f"""
    <div class="expense-card">
        <h3>Monthly Total</h3>
        <h2>${monthly_total_usd:,.0f} USD</h2>
        <p>{EXCHANGE_RATES[home_currency]['symbol']}{monthly_total_home:,.0f} {home_currency}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Total cost for study period
    st.markdown(f"""
    <div class="expense-card">
        <h3>Total Cost ({study_months} months)</h3>
        <h2>${monthly_total_usd * study_months:,.0f} USD</h2>
        <p>{EXCHANGE_RATES[home_currency]['symbol']}{total_cost_period:,.0f} {home_currency}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Comparison with state average
    if monthly_total_usd > 0:
        state_avg_total = sum(reference_costs.values())
        difference = monthly_total_usd - state_avg_total
        percentage_diff = (difference / state_avg_total) * 100
        
        if abs(percentage_diff) < 10:
            status_class = "avg-cost"
            status_text = f"Close to average ({percentage_diff:+.0f}%)"
        elif difference > 0:
            status_class = "high-cost"
            status_text = f"${difference:,.0f} above average ({percentage_diff:+.0f}%)"
        else:
            status_class = "low-cost"
            status_text = f"${abs(difference):,.0f} below average ({percentage_diff:+.0f}%)"
        
        st.markdown(f"""
        <div class="expense-card">
            <h4>vs {selected_state} Average</h4>
            <p class="{status_class}">{status_text}</p>
        </div>
        """, unsafe_allow_html=True)

# Charts and detailed breakdown
if monthly_total_usd > 0:
    st.markdown("---")
    
    chart_col, breakdown_col = st.columns([1.8, 1.2])
    
    with chart_col:
        st.subheader("📊 Expense Breakdown")
        
        # Prepare data for pie chart
        expense_categories = {
            '🏠 Housing': rent,
            '🍕 Food': food,
            '⚡ Utilities': utilities,
            '🚗 Transportation': transportation,
            '🛍️ Miscellaneous': misc
        }
        
        # Filter out zero expenses
        non_zero_expenses = {k: v for k, v in expense_categories.items() if v > 0}
        
        if non_zero_expenses:
            df_chart = pd.DataFrame(
                list(non_zero_expenses.items()), 
                columns=['Category', 'Amount']
            )
            
            fig = px.pie(
                df_chart, 
                values='Amount', 
                names='Category',
                hole=0.3,
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            
            fig.update_traces(
                textposition='inside', 
                textinfo='percent+label',
                hovertemplate='<b>%{label}</b><br>$%{value:,.0f}<br>%{percent}<extra></extra>'
            )
            
            fig.update_layout(
                template="plotly_dark",
                height=350,
                showlegend=False,
                font=dict(color='white', size=12),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
            )
            
            st.plotly_chart(fig, use_container_width=True)
    
    with breakdown_col:
        st.subheader("📋 Details")
        
        # Create breakdown table
        breakdown_data = []
        for category, amount in expense_categories.items():
            if amount > 0:
                home_amount = amount * exchange_rate
                percentage = (amount / monthly_total_usd) * 100
                breakdown_data.append({
                    'Category': category,
                    'USD': f"${amount:,.0f}",
                    home_currency: f"{EXCHANGE_RATES[home_currency]['symbol']}{home_amount:,.0f}",
                    'Share': f"{percentage:.1f}%"
                })
        
        if breakdown_data:
            df_breakdown = pd.DataFrame(breakdown_data)
            st.dataframe(df_breakdown, hide_index=True, use_container_width=True)
        
        # Timeline summary
        st.subheader("⏰ Timeline")
        timeline_data = {
            'Period': ['Per Month', f'Total ({study_months}m)'],
            'USD': [f"${monthly_total_usd:,.0f}", f"${monthly_total_usd * study_months:,.0f}"],
            home_currency: [f"{EXCHANGE_RATES[home_currency]['symbol']}{monthly_total_home:,.0f}", 
                           f"{EXCHANGE_RATES[home_currency]['symbol']}{total_cost_period:,.0f}"]
        }
        
        df_timeline = pd.DataFrame(timeline_data)
        st.dataframe(df_timeline, hide_index=True, use_container_width=True)

else:
    st.info("💡 Enter your expected expenses above to see a detailed breakdown!")

# Footer
st.markdown("---")
st.caption("Exchange rates update every 30min. Numbers are estimates and vary by location.")
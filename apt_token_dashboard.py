import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px

# Page configuration
st.set_page_config(page_title="APT Token Economy Dashboard", layout="wide")

st.title("🪙 APT Token Economy Simulation Dashboard")
st.markdown("Interactive simulation of the APT token economy with solar infrastructure revenue model")

# Sidebar controls
st.sidebar.header("📊 Economic Parameters")

# Mode toggle for staking calculation
mode = st.sidebar.radio(
    "Staking Calculation Mode",
    ["Manual Control", "Yield-Based Auto Staking"],
    help="Manual: Use slider to set staking %. Yield-Based: Staking % = f(2x) of annual yield %"
)

# Core parameters
investor_allocation = st.sidebar.slider(
    "Investor Allocation %", 
    min_value=0.0, max_value=80.0, value=40.0, step=1.0,
    help="Percentage of total supply allocated to investors"
) / 100

investor_stake_duration = st.sidebar.slider(
    "Investor Stake Duration (years)", 
    min_value=0.5, max_value=5.0, value=2.0, step=0.5,
    help="How long investor tokens are locked in staking"
)

if mode == "Manual Control":
    liquid_stake_pct = st.sidebar.slider(
        "Liquid Token Stake %", 
        min_value=0.0, max_value=100.0, value=50.0, step=5.0,
        help="Percentage of liquid tokens that are staked"
    ) / 100
else:
    st.sidebar.markdown("*Liquid Token Stake % calculated automatically based on yield*")

# Constants
TOTAL_SUPPLY = 100_000_000  # 100M tokens
FUNDING_AMOUNT = 10_000_000  # $10M
MARKET_MAKER_ALLOCATION = 0.10  # 10%
DEV_ALLOCATION = 0.10  # 10%
SOLAR_COST_PER_MW = 700_000  # $700k per MW
KWH_PRICE = 0.17  # $0.17 per kWh
HOURS_PER_DAY = 4  # 4 hours of generation per day
DAYS_PER_YEAR = 365
DEPLOYMENT_MONTHS = 10

def calculate_token_economics(investor_alloc, stake_duration, liquid_stake_pct=None, mode="Manual Control"):
    """Calculate token economics over time"""
    
    # Token allocations
    investor_tokens = TOTAL_SUPPLY * investor_alloc
    deflator_tokens = TOTAL_SUPPLY * (0.8 - investor_alloc)  # Remaining up to 80%
    mm_tokens = TOTAL_SUPPLY * MARKET_MAKER_ALLOCATION
    dev_tokens = TOTAL_SUPPLY * DEV_ALLOCATION
    
    # Initial pricing
    initial_price = FUNDING_AMOUNT / investor_tokens
    
    # Solar capacity calculation
    solar_capacity_mw = FUNDING_AMOUNT / SOLAR_COST_PER_MW
    annual_kwh = solar_capacity_mw * 1000 * HOURS_PER_DAY * DAYS_PER_YEAR  # Convert MW to kW
    annual_revenue_usd = annual_kwh * KWH_PRICE
    
    # Time series simulation (48 months = 4 years)
    months = 48
    results = []
    
    # Initial state
    circulating_supply = mm_tokens  # Only MM tokens are liquid initially
    deflator_balance = deflator_tokens
    liquid_investor_tokens = investor_tokens * 1/3  # 1/3 initially liquid
    investor_staked_tokens = investor_tokens * 2/3  # 2/3 initially staked
    staked_tokens = investor_staked_tokens
    
    for month in range(months):
        # Deployment phase (first 10 months)
        if month < DEPLOYMENT_MONTHS:
            deployment_progress = (month + 1) / DEPLOYMENT_MONTHS
            current_capacity = solar_capacity_mw * deployment_progress
            current_annual_revenue = annual_revenue_usd * deployment_progress
        else:
            current_capacity = solar_capacity_mw
            current_annual_revenue = annual_revenue_usd
        
        # Monthly revenue
        monthly_revenue_usd = current_annual_revenue / 12
        
        # Token unlock schedule
        if month >= stake_duration * 12:  # Investor tokens unlock
            if staked_tokens > 0:
                liquid_investor_tokens += investor_staked_tokens
                circulating_supply += investor_staked_tokens
                staked_tokens -= investor_staked_tokens
                investor_staked_tokens = 0
        
        if month >= 36:  # Dev tokens unlock after 3 years
            if month == 36:
                circulating_supply += dev_tokens
                dev_tokens = 0
        
        # Market Maker Pool (Constant Product AMM)
        # Initial setup: 10M APT tokens valued at $2.5M + 2.5M USDC
        mm_usdc_balance = 2_500_000  # 2.5M USDC
        k_constant = circulating_supply * mm_usdc_balance  # Constant product
        
        # Current price calculation using AMM
        if circulating_supply > 0:
            # Price = USDC reserve / APT reserve (price of 1 APT in USDC)
            current_price = mm_usdc_balance / circulating_supply
        else:
            current_price = initial_price  # Fallback to initial price
        
        # Revenue in APT tokens (buying APT with USD revenue)
        if monthly_revenue_usd > 0 and mm_tokens > 0:
            # Calculate how much APT we can buy with monthly_revenue_usd
            # Using AMM formula: new_usdc = old_usdc + revenue_usd
            # new_apt = k / new_usdc
            # apt_received = old_apt - new_apt
            
            new_usdc_balance = mm_usdc_balance + monthly_revenue_usd
            new_apt_balance = k_constant / new_usdc_balance
            monthly_revenue_apt = circulating_supply - new_apt_balance
            
            # Update pool balances after the swap
            mm_usdc_balance = new_usdc_balance
            circulating_supply = new_apt_balance
            
            # Update price after the swap
            current_price = mm_usdc_balance / mm_tokens if mm_tokens > 0 else current_price
        else:
            monthly_revenue_apt = 0
                
        # Staking mechanics and token burning
        total_liquid_tokens = circulating_supply - staked_tokens
        stake_weight = staked_tokens / TOTAL_SUPPLY if TOTAL_SUPPLY > 0 else 0
        
        # Calculate staker allocation based on stake weight
        staker_alloc = monthly_revenue_apt * stake_weight
        
        # Determine tokens to burn based on staking scenarios
        if staked_tokens == 0:
            # No tokens staked: burn all revenue APT + matching amount from deflator
            revenue_apt_to_burn = monthly_revenue_apt
            deflator_matching_burn = min(monthly_revenue_apt, deflator_balance)
            total_tokens_burned = revenue_apt_to_burn + deflator_matching_burn
            
        elif stake_weight >= 1.0:  # All tokens are staked
            # All tokens staked: no revenue APT burned, only deflator tokens if available
            revenue_apt_to_burn = 0
            deflator_matching_burn = min(monthly_revenue_apt, deflator_balance) if deflator_balance > 0 else 0
            total_tokens_burned = deflator_matching_burn
            
        else:
            # Partial staking: burn (revenue_apt - staker_alloc) + deflator matching
            revenue_apt_to_burn = monthly_revenue_apt - staker_alloc
            deflator_matching_burn = min(monthly_revenue_apt, deflator_balance)
            total_tokens_burned = revenue_apt_to_burn + deflator_matching_burn
        
        # Update deflator balance
        deflator_balance -= deflator_matching_burn
        tokens_to_burn = deflator_matching_burn + revenue_apt_to_burn
        circulating_supply - tokens_to_burn
        
        # Calculate annual yield for stakers
        if staked_tokens > 0:
            annual_yield_pct = (staker_alloc * 12) / staked_tokens
        else:
            annual_yield_pct = 0

        if mode == "Yield-Based Auto Staking" and total_liquid_tokens > 0:
            # # Calculate annual yield
            # annual_revenue_apt = monthly_revenue_apt * 12
            # if staked_tokens > 0:
            #     annual_yield = (annual_revenue_apt * 0.7) / staked_tokens
            # else:
            #     annual_yield = 0
            
            # Staking percentage based on yield: f(2x) function
            target_stake_pct = min(annual_yield_pct * 2, 1.0)  # Cap at 100%
            
            # Adjust staking if yield < 8% (unstaking threshold)
            if annual_yield_pct < 0.08:
                target_stake_pct = 0  # Reduce staking when yield is low
        else:
            target_stake_pct = liquid_stake_pct if liquid_stake_pct else 0
        
        # Apply staking changes gradually
        staked_tokens = (circulating_supply * target_stake_pct) + investor_staked_tokens
                
        # Calculate metrics
        fdv = current_price * TOTAL_SUPPLY
        market_cap = current_price * circulating_supply
                
        results.append({
            'Month': month + 1,
            'Price': current_price,
            'Circulating_Supply': circulating_supply,
            'Staked_Tokens': staked_tokens,
            'FDV': fdv,
            'Market_Cap': market_cap,
            'Monthly_Revenue_USD': monthly_revenue_usd,
            'Monthly_Revenue_APT': monthly_revenue_apt,
            'Tokens_Burned': tokens_to_burn,
            'Deflator_Balance': deflator_balance,
            'Annual_Yield_Pct': annual_yield_pct,
            'Stake_Percentage': (staked_tokens / TOTAL_SUPPLY * 100),
            'Solar_Capacity_MW': current_capacity
        })
    
    return pd.DataFrame(results)

# Calculate results
if mode == "Manual Control":
    df = calculate_token_economics(investor_allocation, investor_stake_duration, liquid_stake_pct, mode)
else:
    df = calculate_token_economics(investor_allocation, investor_stake_duration, None, mode)

# Main dashboard
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("📈 Price and Supply Trends")
    
    # Create subplot with secondary y-axis
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=('Token Price & Valuation', 'Circulating Supply & Staking'),
        vertical_spacing=0.12,
        specs=[[{"secondary_y": True}], [{"secondary_y": True}]]
    )
    
    # Price and valuation
    fig.add_trace(
        go.Scatter(x=df['Month'], y=df['Price'], name='Token Price ($)', 
                  line=dict(color='#00CC96', width=3)),
        row=1, col=1
    )
    
    fig.add_trace(
        go.Scatter(x=df['Month'], y=df['FDV']/1e6, name='FDV ($M)', 
                  line=dict(color='#AB63FA', width=2, dash='dash')),
        row=1, col=1, secondary_y=True
    )
    
    # Supply and staking
    fig.add_trace(
        go.Scatter(x=df['Month'], y=df['Circulating_Supply']/1e6, name='Circulating Supply (M)', 
                  line=dict(color='#FF6692', width=3)),
        row=2, col=1
    )
    
    fig.add_trace(
        go.Scatter(x=df['Month'], y=df['Staked_Tokens']/1e6, name='Staked Tokens (M)', 
                  line=dict(color='#19D3F3', width=2)),
        row=2, col=1
    )
    
    fig.add_trace(
        go.Scatter(x=df['Month'], y=df['Annual_Yield_Pct'], name='Annual Yield (%)', 
                  line=dict(color='#FFA15A', width=2, dash='dot')),
        row=2, col=1, secondary_y=True
    )
    
    # Update layout
    fig.update_layout(height=700, showlegend=True, hovermode='x unified')
    fig.update_xaxes(title_text="Month", row=2, col=1)
    fig.update_yaxes(title_text="Price ($)", row=1, col=1)
    fig.update_yaxes(title_text="FDV ($M)", secondary_y=True, row=1, col=1)
    fig.update_yaxes(title_text="Tokens (Millions)", row=2, col=1)
    fig.update_yaxes(title_text="Annual Yield (%)", secondary_y=True, row=2, col=1)
    
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("📊 Current Metrics")
    
    # Latest values
    latest = df.iloc[-1]
    
    # Key metrics
    st.metric("Current Price", f"${latest['Price']:.3f}")
    st.metric("FDV", f"${latest['FDV']/1e6:.1f}M")
    st.metric("Market Cap", f"${latest['Market_Cap']/1e6:.1f}M")
    st.metric("Circulating Supply", f"{latest['Circulating_Supply']/1e6:.1f}M")
    st.metric("Staked Tokens", f"{latest['Staked_Tokens']/1e6:.1f}M")
    st.metric("Annual Yield", f"{latest['Annual_Yield_Pct']:.1f}%")
    st.metric("Stake %", f"{latest['Stake_Percentage']:.1f}%")
    
    st.subheader("🏭 Solar Infrastructure")
    st.metric("Capacity", f"{latest['Solar_Capacity_MW']:.1f} MW")
    st.metric("Monthly Revenue", f"${latest['Monthly_Revenue_USD']:,.0f}")
    st.metric("Deflator Balance", f"{latest['Deflator_Balance']/1e6:.1f}M APT")

# Additional analysis
st.subheader("🔥 Token Burn Analysis")

col3, col4 = st.columns(2)

with col3:
    # Cumulative burn chart
    df['Cumulative_Burned'] = df['Tokens_Burned'].cumsum()
    
    fig_burn = go.Figure()
    fig_burn.add_trace(go.Scatter(
        x=df['Month'], y=df['Cumulative_Burned']/1e6,
        name='Cumulative Burned (M)',
        fill='tonexty',
        line=dict(color='#FF4B4B', width=2)
    ))
    
    fig_burn.update_layout(
        title="Cumulative Token Burns",
        xaxis_title="Month",
        yaxis_title="Tokens Burned (Millions)",
        height=400
    )
    
    st.plotly_chart(fig_burn, use_container_width=True)

with col4:
    # Revenue breakdown
    fig_revenue = go.Figure()
    fig_revenue.add_trace(go.Scatter(
        x=df['Month'], y=df['Monthly_Revenue_USD']/1000,
        name='Monthly Revenue ($K)',
        line=dict(color='#00CC96', width=3)
    ))
    
    fig_revenue.update_layout(
        title="Monthly Revenue Growth",
        xaxis_title="Month",
        yaxis_title="Revenue ($K)",
        height=400
    )
    
    st.plotly_chart(fig_revenue, use_container_width=True)

# Summary statistics
st.subheader("📋 Simulation Summary")

summary_col1, summary_col2, summary_col3 = st.columns(3)

with summary_col1:
    st.markdown("**Token Allocation:**")
    st.write(f"• Investors: {investor_allocation*100:.0f}% ({investor_allocation*TOTAL_SUPPLY/1e6:.1f}M)")
    st.write(f"• Deflator: {(0.8-investor_allocation)*100:.0f}% ({(0.8-investor_allocation)*TOTAL_SUPPLY/1e6:.1f}M)")
    st.write(f"• Market Maker: 10% (10.0M)")
    st.write(f"• Dev Team: 10% (10.0M)")

with summary_col2:
    st.markdown("**Financial Metrics:**")
    st.write(f"• Initial Price: ${FUNDING_AMOUNT/(investor_allocation*TOTAL_SUPPLY):.3f}")
    st.write(f"• Final Price: ${latest['Price']:.3f}")
    st.write(f"• Price Appreciation: {((latest['Price']/(FUNDING_AMOUNT/(investor_allocation*TOTAL_SUPPLY)))-1)*100:.1f}%")
    st.write(f"• Total Revenue (4Y): ${df['Monthly_Revenue_USD'].sum()/1e6:.1f}M")

with summary_col3:
    st.markdown("**Solar Infrastructure:**")
    solar_capacity = FUNDING_AMOUNT / SOLAR_COST_PER_MW
    annual_kwh = solar_capacity * 1000 * HOURS_PER_DAY * DAYS_PER_YEAR
    st.write(f"• Capacity: {solar_capacity:.1f} MW")
    st.write(f"• Annual Generation: {annual_kwh/1e6:.1f} GWh")
    st.write(f"• Annual Revenue: ${annual_kwh * KWH_PRICE/1e6:.1f}M")
    st.write(f"• Total Burned: {df['Cumulative_Burned'].iloc[-1]/1e6:.1f}M APT")

# Footer
st.markdown("---")
st.markdown("*This dashboard simulates the APT token economy based on the specified parameters. Actual performance may vary significantly.*")

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
    dev_locked = TOTAL_SUPPLY * DEV_ALLOCATION
    
    # Initial pricing
    initial_price = FUNDING_AMOUNT / investor_tokens if investor_tokens > 0 else 0
    
    # Solar capacity calculation
    solar_capacity_mw = FUNDING_AMOUNT / SOLAR_COST_PER_MW
    annual_kwh = solar_capacity_mw * 1000 * HOURS_PER_DAY * DAYS_PER_YEAR  # Convert MW to kW
    annual_revenue_usd = annual_kwh * KWH_PRICE
    
    # Time series simulation (48 months = 4 years)
    months = 48
    results = []
    
    # Initial state
    pool_apt = mm_tokens
    pool_usdc = pool_apt * initial_price
    k_constant = pool_apt * pool_usdc if pool_apt > 0 else 0

    holder_liquid = investor_tokens * (1/3)  # 1/3 initially liquid
    investor_staked_tokens = investor_tokens * (2/3)  # 2/3 initially staked
    staked_tokens = investor_staked_tokens
    circulating_supply = pool_apt + holder_liquid  # Liquid (circulating) supply
    deflator_balance = deflator_tokens
    total_supply = TOTAL_SUPPLY

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
        if month >= stake_duration * 12:
            if investor_staked_tokens > 0:
                holder_liquid += investor_staked_tokens
                circulating_supply += investor_staked_tokens
                staked_tokens -= investor_staked_tokens
                investor_staked_tokens = 0
        
        if month >= 36:
            if month == 36:
                holder_liquid += dev_locked
                circulating_supply += dev_locked
                dev_locked = 0
                
        # Current price
        current_price = pool_usdc / pool_apt if pool_apt > 0 else initial_price
        
        # Revenue in APT tokens (buying APT with USD revenue via AMM)
        monthly_revenue_apt = 0
        if monthly_revenue_usd > 0 and pool_apt > 0:
            new_usdc = pool_usdc + monthly_revenue_usd
            new_apt = k_constant / new_usdc
            monthly_revenue_apt = pool_apt - new_apt
            
            # Update pool balances after the swap
            pool_usdc = new_usdc
            pool_apt = new_apt
            
            # Update circulating supply (APT removed from pool)
            circulating_supply -= monthly_revenue_apt
            
            # Update price after the swap
            current_price = pool_usdc / pool_apt if pool_apt > 0 else current_price
                
        # Staking mechanics and token burning
        stake_weight = staked_tokens / total_supply if total_supply > 0 else 0
        
        # Deflator matching burn
        deflator_matching_burn = min(monthly_revenue_apt, deflator_balance)
        deflator_balance -= deflator_matching_burn
        total_supply -= deflator_matching_burn
        
        # Revenue split
        staker_alloc = monthly_revenue_apt * stake_weight
        
        # Burn the rest of revenue APT
        revenue_apt_to_burn = monthly_revenue_apt - staker_alloc
        total_supply -= revenue_apt_to_burn
        
        # Distribute to stakers (compounding)
        staked_tokens += staker_alloc
        
        # Calculate annual yield for stakers
        annual_yield_pct = ((staker_alloc * 12) / staked_tokens) if staked_tokens > 0 else 0

        # Determine target stake percentage
        if mode == "Yield-Based Auto Staking":
            if annual_yield_pct < 0.08:
                target_stake_pct = 0
            else:
                target_stake_pct = min(annual_yield_pct * 2, 1.0)
        else:
            target_stake_pct = liquid_stake_pct if liquid_stake_pct is not None else 0
        
        # Adjust voluntary staking
        total_stakable = holder_liquid + (staked_tokens - investor_staked_tokens)
        voluntary_staked = target_stake_pct * total_stakable
        staked_tokens = investor_staked_tokens + voluntary_staked
        holder_liquid = total_stakable - voluntary_staked
        circulating_supply = pool_apt + holder_liquid
                
        # Calculate metrics
        fdv = current_price * total_supply
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
            'Tokens_Burned': revenue_apt_to_burn + deflator_matching_burn,
            'Deflator_Balance': deflator_balance,
            'Annual_Yield_Pct': annual_yield_pct * 100,  # As percentage for display
            'Stake_Percentage': (staked_tokens / total_supply * 100) if total_supply > 0 else 0,
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
    initial_price_calc = FUNDING_AMOUNT / (investor_allocation * TOTAL_SUPPLY) if investor_allocation > 0 else 0
    st.write(f"• Initial Price: ${initial_price_calc:.3f}")
    st.write(f"• Final Price: ${latest['Price']:.3f}")
    price_app = ((latest['Price'] / initial_price_calc) - 1) * 100 if initial_price_calc > 0 else 0
    st.write(f"• Price Appreciation: {price_app:.1f}%")
    st.write(f"• Total Revenue (4Y): ${df['Monthly_Revenue_USD'].sum():,.0f}")

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

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px

# Page configuration
st.set_page_config(page_title="APT Token Economy Dashboard (Alliance)", layout="wide")

st.title("🪙 APT (Alliance Power Token) Economy Simulation Dashboard")
st.markdown("Interactive simulation of the APT token economy with solar infrastructure revenue model")

# Sidebar controls
st.sidebar.header("📊 Economic Parameters")

# Core parameters
with st.sidebar.expander("Simulation Setup"):
    months = st.slider(
        "Simulation Duration (months)", 
        min_value=18, max_value=96, value=48, step=1,
        help="Simulation Duration"
    )
    
with st.sidebar.expander("Token Setup"):
    investor_allocation = st.slider(
        "Investor Allocation (%)", 
        min_value=0.0, max_value=80.0, value=40.0, step=1.0,
        help="Percentage of total supply allocated to investors"
    ) / 100
    
    investor_stake_duration = st.slider(
        "Investor Stake Duration (months)", 
        min_value=0, max_value=60, value=24, step=1,
        help="How long investor tokens are locked in staking"
    )
    
    TOTAL_SUPPLY = st.slider(
        "Total Supply", 
        min_value=500_000, max_value=1_000_000_000, value=100_000_000, step=1_000_000,
        help="Total token supply"
    )
    
with st.sidebar.expander("Cashflow Setup"):
    FUNDING_AMOUNT = st.slider(
        "Funding Amount ($)", 
        min_value=1_000_000, max_value=50_000_000, value=10_000_000, step=1_000_000,
        help="Funding amount"
    )
    
    SOLAR_COST_PER_MW = st.slider(
        "Solar Cost per Megawatt Capacity ($)", 
        min_value=500_000, max_value=1_000_000, value=700_000, step=100_000,
        help="Solar Cost per Mega Watt Capacity"
    )
    
    KWH_PRICE = st.slider(
        "Price for KiloWatt Hour ($)", 
        min_value=0.06, max_value=0.20, value=0.17, step=0.01,
        help="Kilowatt Price"
    )
    
    DEPLOYMENT_MONTHS = st.slider(
        "Deployment Months", 
        min_value=1, max_value=24, value=10, step=1,
        help="Time to deploy Projects"
    )
    
    OPEX_ALLOCATION = st.slider(
        "OPEX Allocation (%)", 
        min_value=0.0, max_value=20.0, value=10.0, step=0.5,
        help="Percentage of revenue allocated to operational expenses"
    ) / 100
    
    REINVESTMENT_ALLOCATION = st.slider(
        "Reinvestment Allocation (%)", 
        min_value=0.0, max_value=20.0, value=10.0, step=0.5,
        help="Percentage of revenue allocated to reinvestments"
    ) / 100

with st.sidebar.expander("Market Setup"):
    st.markdown("⚠️ Caution!!")
    
    stake_yield_factor = st.slider(
        "Staked Percentage Yield Factor", 
        min_value=0.1, max_value=3.0, value=2.0, step=0.1,
        help="Market Yield Offering to benchmark against"
    )

    competitive_yield = st.slider(
        "Competitive Market Yield (%)", 
        min_value=4, max_value=20, value=8, step=1,
        help="Market Yield Offering to benchmark against"
    )

st.sidebar.markdown("*Liquid Token Stake % calculated automatically based on yield*")

# Constants
MARKET_MAKER_ALLOCATION = 0.10  # 10%
DEV_ALLOCATION = 0.10  # 10%
HOURS_PER_DAY = 4  # 4 hours of generation per day
DAYS_PER_YEAR = 365

def calculate_token_economics(investor_alloc, stake_duration):
    """Calculate token economics over time"""
    
    # Token allocations
    investor_tokens = TOTAL_SUPPLY * investor_alloc
    deflator_balance = TOTAL_SUPPLY * (0.8 - investor_alloc)  # Remaining up to 80%
    mm_tokens = TOTAL_SUPPLY * MARKET_MAKER_ALLOCATION
    dev_locked = TOTAL_SUPPLY * DEV_ALLOCATION
    
    # Initial pricing
    initial_price = FUNDING_AMOUNT / investor_tokens
    current_price = initial_price
    
    # Solar capacity calculation
    solar_capacity_mw = FUNDING_AMOUNT / SOLAR_COST_PER_MW
    annual_kwh = solar_capacity_mw * 1000 * HOURS_PER_DAY * DAYS_PER_YEAR  # Convert MW to kW
    annual_revenue_usd = annual_kwh * KWH_PRICE
    
    results = []
    
    # Initial state
    total_supply = TOTAL_SUPPLY
    investor_staked_tokens = investor_tokens * (2/3)  # 2/3 initially staked
    circulating_supply = mm_tokens + (investor_tokens * (1/3))  # 1/3 initially liquid (circulating) supply
    staked_tokens = investor_staked_tokens  # + dev_locked

    for month in range(months):
        # Deployment phase (first 10 months)
        if month < DEPLOYMENT_MONTHS:
            deployment_progress = (month + 1) / DEPLOYMENT_MONTHS
            current_annual_revenue = annual_revenue_usd * deployment_progress
        else:
            current_annual_revenue = annual_revenue_usd

        # Revenue in APT tokens (buying APT with USD revenue via AMM)
        monthly_revenue_usd = current_annual_revenue / 12
        # Allocate revenue to OPEX and reinvestment
        opex_allocation_usd = monthly_revenue_usd * OPEX_ALLOCATION
        reinvestment_allocation_usd = monthly_revenue_usd * REINVESTMENT_ALLOCATION
        net_revenue_usd = monthly_revenue_usd - (opex_allocation_usd + reinvestment_allocation_usd)
        # Use a fixed price or gradually appreciating price
        monthly_revenue_apt = net_revenue_usd / current_price
        
        # Staking mechanics and token burning
        total_stakable = circulating_supply + staked_tokens
        stake_weight = staked_tokens / total_stakable
        staker_alloc = monthly_revenue_apt * stake_weight

        supply_ratio =  (circulating_supply + deflator_balance) / TOTAL_SUPPLY
        current_price = initial_price / supply_ratio  # Price inversely related to supply

        # Calculate annual yield for stakers
        annual_yield_pct = (staker_alloc * 12) / staked_tokens if staked_tokens > 0 else 0
        # Determine target stake percentage
        if annual_yield_pct < (competitive_yield / 100):
            target_stake_pct = 0
        else:
            target_stake_pct = min(annual_yield_pct * stake_yield_factor, 1)

        # Token unlock schedule
        if month >= stake_duration and investor_staked_tokens > 0:
            investor_staked_tokens = 0

        if month >= 36 and dev_locked > 0:
            dev_locked = 0

        # Adjust voluntary staking
        target_stake_total = target_stake_pct * total_stakable
        staked_tokens = max(target_stake_total, investor_staked_tokens)
        circulating_supply = total_stakable - staked_tokens

        # Deflator matching burn
        deflator_matching_burn = min(monthly_revenue_apt, deflator_balance)
        deflator_balance -= deflator_matching_burn

        # Burn the rest of revenue APT
        revenue_apt_to_burn = monthly_revenue_apt - staker_alloc
        circulating_supply -= revenue_apt_to_burn
        total_supply -= (revenue_apt_to_burn + deflator_matching_burn)

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
            'OPEX_Allocation_USD': opex_allocation_usd,
            'Reinvestment_Allocation_USD': reinvestment_allocation_usd,
            'Net_Revenue_USD': net_revenue_usd,
            'Monthly_Revenue_APT': monthly_revenue_apt,
            'Tokens_Burned': revenue_apt_to_burn + deflator_matching_burn,
            'Deflator_Balance': deflator_balance,
            'Annual_Yield_Pct': annual_yield_pct * 100,  # As percentage for display
            'Stake_Target': target_stake_total,
            'Stake_Tokens': staked_tokens,
            'Stake_Percentage': stake_weight * 100,
            'Staker_Allocation': staker_alloc
        })

    return pd.DataFrame(results)

# Calculate results
df = calculate_token_economics(investor_allocation, investor_stake_duration)

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
        go.Scatter(x=df['Month'], y=round(df['Price'], 6), name='Token Price ($)', 
                  line=dict(color='#00CC96', width=3)),
        row=1, col=1
    )
    
    fig.add_trace(
        go.Scatter(x=df['Month'], y=round(df['FDV']/1e6, 2), name='FDV ($M)', 
                  line=dict(color='#AB63FA', width=2, dash='dash')),
        row=1, col=1, secondary_y=True
    )
    
    # Supply and staking
    fig.add_trace(
        go.Scatter(x=df['Month'], y=round(df['Circulating_Supply']/1e6, 2), name='Circulating Supply (M)', 
                  line=dict(color='#FF6692', width=3)),
        row=2, col=1
    )
    
    fig.add_trace(
        go.Scatter(x=df['Month'], y=round(df['Staked_Tokens']/1e6, 2), name='Staked Tokens (M)', 
                  line=dict(color='#19D3F3', width=2)),
        row=2, col=1
    )
    
    fig.add_trace(
        go.Scatter(x=df['Month'], y=round(df['Annual_Yield_Pct'], 2), name='Annual Yield (%)', 
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
    st.metric("Monthly Revenue", f"${latest['Monthly_Revenue_USD']:,.0f}")
    st.metric("OPEX Allocation", f"${latest['OPEX_Allocation_USD']:,.0f}")
    st.metric("Reinvestment Allocation", f"${latest['Reinvestment_Allocation_USD']:,.0f}")
    st.metric("Net Revenue", f"${latest['Net_Revenue_USD']:,.0f}")
    st.metric("Deflator Balance", f"{latest['Deflator_Balance']/1e6:.1f}M APT")

# Additional analysis
st.subheader("🔥 Token Burn Analysis")

col3, col4 = st.columns(2)

with col3:
    # Cumulative burn chart
    df['Cumulative_Burned'] = df['Tokens_Burned'].cumsum()
    
    fig_burn = go.Figure()
    fig_burn.add_trace(go.Scatter(
        x=df['Month'], y=round(df['Cumulative_Burned']/1e6, 2),
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
    fig_deflation = make_subplots(specs=[[{"secondary_y": True}]])
    fig_deflation.add_trace(go.Scatter(
        x=df['Month'], y=round(df['Deflator_Balance']/1000, 2),
        name='Deflator Balance (K)',
        line=dict(color='#00CC96', width=3)
    ))

    fig_deflation.add_trace(
        go.Scatter(x=df['Month'], y=round(df['Stake_Target']/1000, 2), name='Target Percentage APT Staked (k)', 
                  line=dict(color='#FFA15A', width=2, dash='dot')), secondary_y=True
    )

    fig_deflation.add_trace(
        go.Scatter(x=df['Month'], y=round(df['Stake_Tokens']/1000, 2), name='Actual APT Staked (k)', 
                  line=dict(width=2, dash='dot')), secondary_y=True
    )
    
    fig_deflation.update_layout(
        title="Supply Crunch",
        height=400, showlegend=True, hovermode='x unified'
    )

    fig_deflation.update_xaxes(title_text="Month")
    fig_deflation.update_yaxes(title_text="Balance (K)")
    fig_deflation.update_yaxes(title_text="Staked (%)", secondary_y=True)

    st.plotly_chart(fig_deflation, use_container_width=True)

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
    st.write(f"• Total OPEX (4Y): ${df['OPEX_Allocation_USD'].sum():,.0f}")
    st.write(f"• Total Reinvestment (4Y): ${df['Reinvestment_Allocation_USD'].sum():,.0f}")

with summary_col3:
    st.markdown("**Solar Infrastructure:**")
    solar_capacity = FUNDING_AMOUNT / SOLAR_COST_PER_MW
    annual_kwh = solar_capacity * 1000 * HOURS_PER_DAY * DAYS_PER_YEAR
    st.write(f"• Capacity: {solar_capacity:.1f} MW")
    st.write(f"• Annual Generation: {annual_kwh/1e6:.1f} GWh")
    st.write(f"• Annual Revenue: ${annual_kwh * KWH_PRICE/1e6:.1f}M")
    st.write(f"• Total Burned: {df['Cumulative_Burned'].iloc[-1]/1e6:.1f}M APT")

st.dataframe(df, use_container_width=True) # Displays an interactive table filling the container width

# Footer
st.markdown("---")
st.markdown("*This dashboard simulates the APT token economy based on the specified parameters. Actual performance may vary significantly.*")

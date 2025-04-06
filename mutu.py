import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from mftool import Mftool



# Custom badge panel
def layman_panel(icon, text, color="#4CAF50"):
    return st.markdown(f"""
    <div class="custom-badge" style="border-left-color:{color};">
        <span>{icon}</span><span><b>{text}</b></span>
    </div>
    """, unsafe_allow_html=True)

# Risk label rendering
def assign_risk_level(volatility):
    thresholds = {
        'Little or No Risk': 0.01,
        'Low Risk': 0.03,
        'Moderate Risk': 0.07,
        'High Risk': 0.15,
        'Ultra High Risk': 0.25
    }

    if volatility <= thresholds['Little or No Risk']:
        return 'Little or No Risk', '#4CAF50', '🛡️'
    elif volatility <= thresholds['Low Risk']:
        return 'Low Risk', '#2196F3', '🌊'
    elif volatility <= thresholds['Moderate Risk']:
        return 'Moderate Risk', '#FFC107', '⚖️'
    elif volatility <= thresholds['High Risk']:
        return 'High Risk', '#FF9800', '🔥'
    else:
        return 'Ultra High Risk', '#F44336', '💥'

# Initialization

mf = Mftool()
st.title("Mutual Fund Financial Dashboard")

option = st.sidebar.selectbox(
    "Choose an action",
    ["View Available Schemes", "Scheme Details", "Historical NAV", 
     "Compare NAVs", "Average AUM", "Risk and Volatility Analysis",  # ← Add these
     "Performance Heatmap"]  # ← Add this
)


# Fetch all scheme codes for dropdowns
scheme_names = {v: k for k, v in mf.get_scheme_codes().items()}

if option == "View Available Schemes":
    st.header("View Available Schemes")
    amc = st.sidebar.text_input("Enter AMC Name", "ICICI")
    schemes = mf.get_available_schemes(amc)
    if schemes:
        df = pd.DataFrame(schemes.items(), columns=["Scheme Code", "Scheme Name"])
        st.write(df)
        layman_panel("🏦", f"{len(df)} schemes available in {amc}", "#2196F3")
    else:
        st.write("No schemes found.")
if option == "Scheme Details":
    st.header("Scheme Details")
    scheme_code = scheme_names[st.sidebar.selectbox("Select a Scheme", scheme_names.keys())]
    details = pd.DataFrame(mf.get_scheme_details(scheme_code)).iloc[0]
    st.write(details)


if option == "Historical NAV":
    st.header("Historical NAV")
    scheme_name = st.sidebar.selectbox("Select a Scheme", scheme_names.keys())
    scheme_code = scheme_names[scheme_name]
    nav_data = mf.get_scheme_historical_nav(scheme_code, as_Dataframe=True)
    st.write(nav_data)
    
    if not nav_data.empty:
        avg_growth = nav_data['nav'].pct_change().mean() * 30  # Monthly avg
        layman_panel("📅", f"Average monthly growth: {avg_growth:.2%}", "#FF9800")
if option == "Compare NAVs":
    st.header("Compare NAVs")
    selected_schemes = st.sidebar.multiselect("Select Schemes to Compare", options=list(scheme_names.keys()))
    if selected_schemes:
        comparison_df = pd.DataFrame()
        for scheme in selected_schemes:
            code = scheme_names[scheme]
            data = mf.get_scheme_historical_nav(code, as_Dataframe=True)
            data = data.reset_index().rename(columns={"index": "date"})
            data["date"] = pd.to_datetime(data["date"], dayfirst=True).sort_values()
            data["nav"] = data["nav"].replace(0, None).interpolate()
            comparison_df[scheme] = data.set_index("date")["nav"]
        fig = px.line(comparison_df, title="Comparison of NAVs")
        st.plotly_chart(fig)
    else:
        st.info("Select at least one scheme.")

if option == "Average AUM":
    st.header("Average AUM")
    aum_data = mf.get_average_aum('July - September 2024', False)
    
    if aum_data:
        aum_df = pd.DataFrame(aum_data)
        aum_df["Total AUM"] = aum_df[["AAUM Overseas", "AAUM Domestic"]].astype(float).sum(axis=1)
        st.write(aum_df[["Fund Name", "Total AUM"]])
        
        # AUM ranking insight
        aum_rank = aum_df["Total AUM"].rank(pct=True).iloc[0]
        layman_panel("📊", f"Ranked in top {int(100*(1 - aum_rank))}% by AUM size", "#9C27B0")
    else:
        st.write("No AUM data available.")


if option == "Performance Heatmap":
    st.header("Performance Heatmap")
    scheme_code = scheme_names[st.sidebar.selectbox("Select a Scheme", scheme_names.keys())]
    nav_data = mf.get_scheme_historical_nav(scheme_code, as_Dataframe=True)
    scheme_name = list(scheme_names.keys())[list(scheme_names.values()).index(scheme_code)]

    if not nav_data.empty:
        # Prepare NAV data
        nav_data = nav_data.reset_index().rename(columns={"index": "date"})
        nav_data["month"] = pd.DatetimeIndex(nav_data["date"]).month
        nav_data["nav"] = nav_data["nav"].astype(float)

        # Performance Heatmap
        heatmap_data = nav_data.groupby(["month"])["dayChange"].mean().reset_index()
        heatmap_data["month"] = heatmap_data["month"].astype(str)

        fig_heatmap = px.density_heatmap(
            heatmap_data,
            x="month",
            y="dayChange",
            title="NAV Performance Heatmap",
            color_continuous_scale="Viridis"
        )
        st.plotly_chart(fig_heatmap)

        # Monte Carlo Simulation
        st.write("### Monte Carlo Simulation for Future NAV Projection")
        num_simulations = st.slider("Number of Simulations", min_value=100, max_value=5000, value=1000)
        num_days = st.slider("Projection Period (Days)", min_value=30, max_value=365, value=252)

        # Ensure returns column exists
        if "returns" not in nav_data.columns:
            nav_data["returns"] = nav_data["nav"].pct_change()

        last_nav = nav_data["nav"].iloc[-1]
        daily_volatility = nav_data["returns"].std()
        daily_mean_return = nav_data["returns"].mean()

        simulation_results = []
        for _ in range(num_simulations):
            prices = [last_nav]
            for __ in range(num_days):
                simulated_return = np.random.normal(daily_mean_return, daily_volatility)
                prices.append(prices[-1] * (1 + simulated_return))
            simulation_results.append(prices)

        # Create DataFrame for visualization
        simulation_df = pd.DataFrame(simulation_results).T
        simulation_df.index.name = "Day"
        simulation_df.columns = [f"Simulation {i+1}" for i in range(num_simulations)]

        # Plot simulations
        fig_simulation = px.line(
            simulation_df,
            title=f"Monte Carlo Simulation for {scheme_name} NAV Projection",
            labels={"value": "Projected NAV", "index": "Day"},
            template="plotly_dark"
        )
        st.plotly_chart(fig_simulation)

        # Show Summary Statistics
        final_prices = simulation_df.iloc[-1]
        st.write(f"### Simulation Summary for {scheme_name}")
        st.metric("Expected Final NAV", f"{final_prices.mean():.2f}")
        st.metric("Minimum Final NAV", f"{final_prices.min():.2f}")
        st.metric("Maximum Final NAV", f"{final_prices.max():.2f}")
    else:
        st.write("No historical NAV data available.")



    
if option == "Risk and Volatility Analysis":
    st.header("Risk and Volatility Analysis")
    scheme_name = st.sidebar.selectbox("Select a Scheme", scheme_names.keys())
    scheme_code = scheme_names[scheme_name]
    nav_data = mf.get_scheme_historical_nav(scheme_code, as_Dataframe=True)
    
    if not nav_data.empty:
        # Process NAV data
        nav_data = nav_data.reset_index().rename(columns={"index": "date"})
        nav_data["date"] = pd.to_datetime(nav_data["date"], dayfirst=True)
        nav_data["nav"] = pd.to_numeric(nav_data["nav"], errors="coerce")
        nav_data = nav_data.dropna(subset=["nav"])
        
        # Calculate daily returns
        nav_data["returns"] = nav_data["nav"].pct_change()
        nav_data = nav_data.dropna(subset=["returns"])
        
        # Calculate annualized return
        annualized_return = (1 + nav_data["returns"].mean()) ** 252 - 1
        
        # Calculate annualized volatility
        annualized_volatility = nav_data["returns"].std() * np.sqrt(252)
        
        # Define risk-free rate
        risk_free_rate = 0.06
        
        # Calculate Sharpe Ratio
        sharpe_ratio = (annualized_return - risk_free_rate) / annualized_volatility
        
        # Display metrics
        st.write(f"### Metrics for {scheme_name}")
        st.metric("Annualized Volatility", f"{annualized_volatility:.2%}")
        st.metric("Annualized Return", f"{annualized_return:.2%}")
        st.metric("Sharpe Ratio", f"{sharpe_ratio:.2f}")
        
        # Risk assessment logic
        risk_thresholds = {
            'Little or No Risk': 0.01,
            'Low Risk': 0.03,
            'Moderate Risk': 0.07,
            'High Risk': 0.15,
            'Ultra High Risk': 0.25
        }

        def assign_risk_level(volatility):
            """Assign risk level based on annualized volatility."""
            if volatility <= risk_thresholds['Little or No Risk']:
                return ('Little or No Risk', '#4CAF50', '🛡️')
            elif volatility <= risk_thresholds['Low Risk']:
                return ('Low Risk', '#2196F3', '🌊')
            elif volatility <= risk_thresholds['Moderate Risk']:
                return ('Moderate Risk', '#FFC107', '⚖️')
            elif volatility <= risk_thresholds['High Risk']:
                return ('High Risk', '#FF9800', '🔥')
            else:
                return ('Ultra High Risk', '#F44336', '💥')

        # Assign risk level based on volatility
        risk_level, color, icon = assign_risk_level(annualized_volatility)

        # Display Risk Badge
        st.write(f"### Risk Assessment")
        st.markdown(
            f"<div style='padding: 1rem; border-radius: 0.5rem; background-color: {color}; "
            f"color: white; width: fit-content; font-size: 1.2rem; margin: 1rem 0;'>"
            f"{icon} {risk_level}"
            "</div>", 
            unsafe_allow_html=True
        )



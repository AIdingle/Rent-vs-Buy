import streamlit as st
import pandas as pd
import numpy_financial as npf

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Rent vs. Own Calculator", layout="wide")

st.title("🏡 Rent vs. Own Analysis")
st.markdown("Adjust the assumptions in the sidebar (the 'Blue Cells') to see the financial outcome.")

# --- SIDEBAR: "THE BLUE CELLS" ---
st.sidebar.header("📝 Assumptions (Blue Cells)")

# 1. PURCHASE ASSUMPTIONS
with st.sidebar.expander("Purchase & Loan Details", expanded=True):
    purchase_price = st.number_input("Purchase Price ($)", value=550000)
    down_payment_percent = st.slider("Down Payment %", 0.0, 1.0, 0.20, help="Typical is 20%")
    mortgage_rate = st.number_input("Mortgage Rate (%)", value=6.25) / 100
    mortgage_term = st.selectbox("Mortgage Term", [15, 30], index=0)
    renovation_cost = st.number_input("Renovation Cost ($)", value=50000)
    reno_recapture = st.slider("Renovation Value Recapture %", 0.0, 1.0, 0.80, help="How much value the reno adds immediately")

# 2. ONGOING COST ASSUMPTIONS
with st.sidebar.expander("Ongoing Costs & Taxes", expanded=False):
    hoa_monthly = st.number_input("HOA Monthly ($)", value=700)
    insurance_rate = st.number_input("Insurance Rate (% of Value)", value=1.0) / 100
    maintenance_rate = st.number_input("Maintenance Rate (% of Value)", value=1.0) / 100
    
    st.markdown("---")
    st.markdown("**Tax Assumptions (Florida Logic)**")
    tax_rate = st.number_input("Property Tax Rate (%)", value=2.5) / 100
    assessed_value_pct = st.number_input("Assessed Value (% of Price)", value=86.0) / 100
    homestead_exemption = st.number_input("Homestead Exemption ($)", value=75000)
    tax_cap_rate = st.number_input("Annual Tax Cap (%)", value=3.0) / 100

# 3. MARKET & INFLATION ASSUMPTIONS
with st.sidebar.expander("Market & Inflation", expanded=False):
    appreciation_rate = st.number_input("Home Appreciation (%)", value=3.0) / 100
    inflation_rate = st.number_input("General Inflation (%)", value=3.0) / 100
    rent_appreciation = st.number_input("Rent Appreciation (%)", value=3.0) / 100
    cost_of_capital = st.number_input("Investment Return / Cost of Capital (%)", value=5.0) / 100

# 4. EXIT & RENT ASSUMPTIONS
with st.sidebar.expander("Rent & Sale Details", expanded=True):
    monthly_rent = st.number_input("Equivalent Monthly Rent ($)", value=3500)
    selling_costs_pct = st.number_input("Total Selling Costs (% of Sale Price)", value=7.0) / 100

# --- THE "LOCKED" LOGIC ---
# Users cannot see or edit anything below this line.

# Initial Calc
down_payment_dollars = purchase_price * down_payment_percent
loan_amount = purchase_price - down_payment_dollars
initial_market_value = purchase_price + (renovation_cost * reno_recapture)
initial_cash_invested = down_payment_dollars + renovation_cost

# Mortgage P&I
monthly_rate = mortgage_rate / 12
n_periods = mortgage_term * 12
monthly_pi = -npf.pmt(monthly_rate, n_periods, loan_amount)

# Year 1 Tax Base Calculation (Matches your Sheet Logic: (Price - Homestead) * Assessed%)
taxable_value_base = (purchase_price - homestead_exemption) * assessed_value_pct
initial_tax_bill = taxable_value_base * tax_rate

# Simulation Loop
years = []
owner_net_outcome = []
renter_net_outcome = []
gap_data = []

# State Variables
curr_home_value = initial_market_value
curr_rent_monthly = monthly_rent
curr_tax_bill = initial_tax_bill
curr_hoa = hoa_monthly
curr_maint = initial_market_value * maintenance_rate
curr_insurance = initial_market_value * insurance_rate
curr_loan_balance = loan_amount

# Renter Portfolio tracks the "opportunity cost"
# Renter starts with the cash the owner spent (Down Payment + Reno)
renter_portfolio = initial_cash_invested 

for year in range(1, 16):
    # 1. Update Market Values (Appreciation)
    if year > 1:
        curr_home_value *= (1 + appreciation_rate)
        curr_rent_monthly *= (1 + rent_appreciation)
        curr_hoa *= (1 + inflation_rate)
        curr_maint *= (1 + inflation_rate)
        curr_insurance *= (1 + inflation_rate)
        
        # Tax Cap Logic (Save Our Homes)
        # Tax bill grows by lesser of Inflation or Cap (3%)
        tax_growth = min(inflation_rate, tax_cap_rate)
        curr_tax_bill *= (1 + tax_growth)
    else:
        # Year 1 adjustments (End of Year)
        curr_home_value *= (1 + appreciation_rate)
        # Rent/Expenses usually fixed for year 1, but we apply appreciation for End-of-Year value

    # 2. Calculate Annual Cash Flows
    owner_annual_spend = (monthly_pi * 12) + (curr_hoa * 12) + curr_tax_bill + curr_maint + curr_insurance
    renter_annual_spend = (curr_rent_monthly * 12)
    
    # 3. The Savings Difference
    # If Owner spends more, Renter adds difference to savings.
    # If Renter spends more, Renter withdraws difference from portfolio.
    cash_flow_diff = owner_annual_spend - renter_annual_spend
    
    # 4. Grow Renter Portfolio
    # (Portfolio Balance + Savings Contribution) * Growth
    # We assume savings are contributed throughout year, simpler to add at end for annual model
    renter_portfolio = (renter_portfolio * (1 + cost_of_capital)) + cash_flow_diff

    # 5. Pay Down Loan
    # Simple amortization check
    interest_paid = 0
    principal_paid = 0
    for _ in range(12):
        if curr_loan_balance > 0:
            interest = curr_loan_balance * monthly_rate
            principal = monthly_pi - interest
            curr_loan_balance -= principal
            interest_paid += interest
            principal_paid += principal
        else:
            curr_loan_balance = 0

    # 6. Calculate Net Worth Positions
    
    # Owner Net Worth = (Home Value - Selling Costs - Loan Balance)
    owner_equity = curr_home_value - (curr_home_value * selling_costs_pct) - curr_loan_balance
    
    # Renter Net Worth = Investment Portfolio Balance
    renter_equity = renter_portfolio
    
    # 7. The Gap
    # If Owner Equity > Renter Equity, Owner Wins.
    benefit = owner_equity - renter_equity
    
    years.append(year)
    owner_net_outcome.append(owner_equity)
    renter_net_outcome.append(renter_equity)
    gap_data.append(benefit)

# --- RESULTS DISPLAY ---
st.subheader(f"Financial Comparison (Year 1 - 15)")

# Create DataFrame
df_res = pd.DataFrame({
    'Year': years,
    'Owner Wealth': owner_net_outcome,
    'Renter Wealth': renter_net_outcome,
    'Net Benefit of Owning': gap_data
})

# --- SUMMARY METRICS ---
col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        label="Year 5 Benefit",
        value=f"${gap_data[4]:,.0f}",
        delta="Owner Wins" if gap_data[4] > 0 else "Renter Wins",
        delta_color="normal" if gap_data[4] > 0 else "inverse"
    )

with col2:
    st.metric(
        label="Year 10 Benefit",
        value=f"${gap_data[9]:,.0f}",
        delta="Owner Wins" if gap_data[9] > 0 else "Renter Wins",
        delta_color="normal" if gap_data[9] > 0 else "inverse"
    )

with col3:
    st.metric(
        label="Year 15 Benefit",
        value=f"${gap_data[14]:,.0f}",
        delta="Owner Wins" if gap_data[14] > 0 else "Renter Wins",
        delta_color="normal" if gap_data[14] > 0 else "inverse"
    )

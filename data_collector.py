import yfinance as yf
import pandas as pd

TICKER = 'REPYY'  # Repsol, S.A. ADR

repsol = yf.Ticker(TICKER)

# Retrieve Annual Financial Statements (Income Statement, Balance Sheet, Cash Flow)
try:
    income_statement = repsol.financials.T
    balance_sheet = repsol.balance_sheet.T
    cash_flow = repsol.cashflow.T
except Exception as e:
    print(f"Error fetching financial statements: {e}")
    # Create empty DataFrames to avoid script failure
    income_statement = pd.DataFrame()
    balance_sheet = pd.DataFrame()
    cash_flow = pd.DataFrame()

# Retrieve Key Market and Common Stock Data
info = repsol.info
history = repsol.history(period="1y")

# Get latest market cap, shares outstanding, debt, and cash
try:
    market_cap = info.get('marketCap')
    shares_outstanding = info.get('sharesOutstanding')
    beta = info.get('beta')
    # Find the row names that correspond to these metrics
    total_debt = balance_sheet['Total Debt'].iloc[0] if 'Total Debt' in balance_sheet.columns else None
    cash = balance_sheet['Cash And Cash Equivalents'].iloc[0] if 'Cash And Cash Equivalents' in balance_sheet.columns else None

    # Get the latest closing price for market-dependent metrics
    latest_price = history['Close'].iloc[-1] if not history.empty else None

except Exception as e:
    print(f"Error fetching key market data: {e}")
    market_cap, shares_outstanding, beta, total_debt, cash, latest_price = [None] * 6


# Extract DCF Input Metrics from the Statements
# Define the required DCF metrics and their corresponding statement rows (keys)
dcf_metrics_map = {
    'Revenue': 'Total Revenue',
    'EBIT': 'EBIT',
    'Depreciation': 'Reconciled Depreciation', 
    'CapEx': 'Capital Expenditure', 
    'Taxes': 'Tax Provision'
}

# Consolidate the data into a single DataFrame
dcf_data = {}
for date in income_statement.index:
    data_point = {}

    # Get metrics from the map
    for metric, key in dcf_metrics_map.items():
        if metric in ['Revenue', 'EBIT', 'Taxes'] and key in income_statement.columns:
            data_point[metric] = income_statement.loc[date, key]
        elif metric == 'Depreciation' and key in income_statement.columns: # D&A is often on the income statement in yfinance
            # Use negative value for cash flow calculation
            data_point[metric] = income_statement.loc[date, key]
        elif metric == 'CapEx' and key in cash_flow.columns:
            # CapEx is usually a negative number (cash outflow), use its absolute value or leave as is
            # For DCF, we often use the absolute value of the outflow for the model input
            data_point[metric] = abs(cash_flow.loc[date, key])
        else:
            data_point[metric] = None
    
    # Calculate Net Working Capital (NWC) = Current Assets - Current Liabilities
    # Note: NWC calculation requires 'Current Assets' and 'Current Liabilities' from the Balance Sheet
    current_assets = balance_sheet.loc[date, 'Current Assets'] if 'Current Assets' in balance_sheet.columns else None
    current_liabilities = balance_sheet.loc[date, 'Current Liabilities'] if 'Current Liabilities' in balance_sheet.columns else None
    
    if current_assets is not None and current_liabilities is not None:
        data_point['Net Working Capital'] = current_assets - current_liabilities
    else:
        data_point['Net Working Capital'] = None

    dcf_data[date.strftime('%Y-%m-%d')] = data_point

dcf_df = pd.DataFrame(dcf_data).T

# Add Market and Shares Data

summary_data = {
    'Shares Outstanding': shares_outstanding,
    'Market Cap': market_cap,
    'Total Debt (Latest)': total_debt,
    'Cash & Equivalents (Latest)': cash,
    'Beta (Latest)': beta
}

# Convert summary data to a DataFrame row
summary_df = pd.DataFrame(summary_data, index=['Latest Market Data'])

# Combine financial and market data
final_df = pd.concat([dcf_df, summary_df])

# Save to CSV
FILE_NAME = 'repsol_financials.csv'
final_df.to_csv(FILE_NAME)

print(f"✅ Data collection complete. Results saved to {FILE_NAME}")
print("\nFirst few rows of the data:")

print(final_df.head())

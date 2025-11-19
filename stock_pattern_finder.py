import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# --- Configuration Parameters ---
# Define the list of stock tickers you want to analyze
TICKERS = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'SMCI', 'AMD', 'INTC', 'KO']
# Adjust START_DATE and END_DATE for the historical data range
# Changed dates back to a historical range for valid data fetching
START_DATE = '2023-01-01'
END_DATE = '2024-06-25' # Using current date as example

# --- Pattern Detection Parameters ---
# Period (in days) to look back for identifying a local low (support candidate)
LOOKBACK_PERIOD = 30
# Minimum percentage increase from the low for a valid "bounce"
BOUNCE_MIN_PCT = 0.05  # 5% bounce
# How close (in percentage) the retest low must be to the initial support low
RETEST_TOLERANCE_PCT = 0.01 # Within 1% of the original low
# Maximum number of days between the initial low, the bounce peak, and the retest low
MAX_DAYS_BETWEEN_EVENTS = 60
# Volume confirmation: Retest volume should be at most this ratio of the average volume
# during the initial drop-bounce phase. Lower volume on retest is often a bullish sign.
RETEST_VOLUME_RATIO = 0.8 # Retest volume <= 80% of initial phase average volume

# --- Main Analysis Function ---
def find_support_retest_pattern(
    ticker: str,
    start_date: str,
    end_date: str,
    lookback_period: int,
    bounce_min_pct: float,
    retest_tolerance_pct: float,
    max_days_between_events: int,
    retest_volume_ratio: float
) -> list:
    """
    Identifies if a stock exhibits a "support retest" pattern with volume consideration.

    Args:
        ticker (str): The stock ticker symbol (e.g., 'AAPL').
        start_date (str): Start date for data fetching (YYYY-MM-DD).
        end_date (str): End date for data fetching (YYYY-MM-DD).
        lookback_period (int): Number of days to look back for the initial support low.
        bounce_min_pct (float): Minimum percentage increase from the initial low for a valid bounce.
        retest_tolerance_pct (float): Max percentage difference from the initial low for the retest.
        max_days_between_events (int): Max days allowed for the entire pattern (low -> bounce -> retest).
        retest_volume_ratio (float): Max ratio of retest volume to initial phase average volume.

    Returns:
        list: A list of dictionaries, each indicating a date when the pattern was found,
              along with key price and volume data for that pattern.
    """
    print(f"Fetching data for {ticker}...")
    try:
        data = yf.download(ticker, start=start_date, end=end_date, progress=False, auto_adjust=True)
        if data.empty:
            print(f"No data found for {ticker} in the specified range. Skipping.")
            return []
    except Exception as e:
        print(f"Error fetching data for {ticker}: {e}. Skipping.")
        return []

    # Ensure data is sorted by date
    data = data.sort_index()

    # Drop any rows with NaN values that might prevent calculations
    data.dropna(inplace=True)
    if data.empty:
        print(f"No clean data after dropping NaNs for {ticker}. Skipping.")
        return []

    identified_patterns = []

    # Iterate through the data to find patterns
    # We need enough data points for lookback_period and subsequent events
    for i in range(lookback_period, len(data) - 1): # -1 to ensure there's at least one day after
        # Define the window for finding the initial low (support candidate)
        initial_low_window = data.iloc[i - lookback_period : i + 1]
        
        # --- Step 1: Find Initial Low (Support Candidate) ---
        # Find the true low within this window
        # Use .item() to ensure initial_low_price is a scalar float
        initial_low_price = initial_low_window['Low'].min().item()
        
        # Get the date of the initial low
        # If there are multiple occurrences of the min low, take the first one
        initial_low_date = initial_low_window[initial_low_window['Low'] == initial_low_price].index[0]
        
        # Get the index of the initial low date in the full data
        initial_low_idx = data.index.get_loc(initial_low_date)

        # Ensure we have enough data *after* the initial low for a bounce and retest
        if initial_low_idx + 1 >= len(data):
            continue # Not enough data after this low point

        # --- Step 2: Find a Bounce ---
        # Look for a bounce after the initial low
        # The bounce must occur within MAX_DAYS_BETWEEN_EVENTS after the initial low
        bounce_search_start_idx = initial_low_idx + 1
        bounce_search_end_idx = min(len(data), initial_low_idx + max_days_between_events + 1)
        
        bounce_data = data.iloc[bounce_search_start_idx:bounce_search_end_idx]
        if bounce_data.empty:
            continue

        bounce_found = False
        bounce_peak_price = -1
        bounce_peak_date = None
        
        for j in range(len(bounce_data)):
            # Use .item() to ensure current_high is a scalar float
            current_high = bounce_data.iloc[j]['High'].item()
            if (current_high - initial_low_price) / initial_low_price >= bounce_min_pct:
                bounce_peak_price = current_high # Using high of the day as peak
                bounce_peak_date = bounce_data.iloc[j].name
                bounce_found = True
                break # Found a valid bounce, proceed

        if not bounce_found:
            continue # No sufficient bounce found

        # --- Step 3: Find a Retest ---
        # Look for a retest after the bounce peak
        # The retest must occur within MAX_DAYS_BETWEEN_EVENTS from the initial low date
        retest_search_start_idx = data.index.get_loc(bounce_peak_date) + 1
        retest_search_end_idx = min(len(data), initial_low_idx + max_days_between_events + 1)

        retest_data = data.iloc[retest_search_start_idx:retest_search_end_idx]
        if retest_data.empty:
            continue

        retest_found = False
        retest_low_price = -1
        retest_date = None
        
        # Define the retest support range
        retest_upper_bound = initial_low_price * (1 + retest_tolerance_pct)
        retest_lower_bound = initial_low_price * (1 - retest_tolerance_pct)

        for k in range(len(retest_data)):
            # Use .item() to ensure current_low is a scalar float
            current_low = retest_data.iloc[k]['Low'].item()
            
            # Check if the current low falls within the retest tolerance
            if retest_lower_bound <= current_low <= retest_upper_bound:
                retest_low_price = current_low
                retest_date = retest_data.iloc[k].name
                retest_found = True
                break # Found a valid retest

        if not retest_found:
            continue # No retest found within tolerance

        # Ensure the retest date is after the initial low date and bounce date
        if not (initial_low_date < bounce_peak_date < retest_date):
            continue

        # --- Step 4: Volume Confirmation ---
        # Calculate average volume during the initial drop to bounce phase
        initial_phase_volume_data = data.loc[initial_low_date:bounce_peak_date]['Volume']
        # Use .item() to explicitly extract the scalar value from the mean result
        initial_phase_avg_volume = initial_phase_volume_data.mean().item()
        
        # Check retest volume against the ratio
        # Get the integer location of the retest_date in the full data DataFrame
        retest_date_idx_in_data = data.index.get_loc(retest_date)
        # Access the 'Volume' column using integer position for the row and column, then .item()
        retest_day_volume = data.iloc[retest_date_idx_in_data]['Volume'].item()

        if retest_day_volume <= initial_phase_avg_volume * retest_volume_ratio:
            # Pattern detected! Store the details.
            identified_patterns.append({
                'ticker': ticker,
                'pattern_end_date': retest_date.strftime('%Y-%m-%d'),
                'initial_low_date': initial_low_date.strftime('%Y-%m-%d'),
                'initial_low_price': round(initial_low_price, 2),
                'bounce_peak_date': bounce_peak_date.strftime('%Y-%m-%d'),
                'bounce_peak_price': round(bounce_peak_price, 2),
                'retest_date': retest_date.strftime('%Y-%m-%d'),
                'retest_low_price': round(retest_low_price, 2),
                'initial_avg_volume': int(initial_phase_avg_volume),
                'retest_volume': int(retest_day_volume),
                'volume_ratio': round(retest_day_volume / initial_phase_avg_volume, 2)
            })

    return identified_patterns

# --- Execution Block ---
if __name__ == "__main__":
    print("Starting stock pattern analysis...\n")
    all_found_patterns = []

    for ticker_symbol in TICKERS:
        patterns = find_support_retest_pattern(
            ticker=ticker_symbol,
            start_date=START_DATE,
            end_date=END_DATE,
            lookback_period=LOOKBACK_PERIOD,
            bounce_min_pct=BOUNCE_MIN_PCT,
            retest_tolerance_pct=RETEST_TOLERANCE_PCT,
            max_days_between_events=MAX_DAYS_BETWEEN_EVENTS,
            retest_volume_ratio=RETEST_VOLUME_RATIO
        )
        if patterns:
            all_found_patterns.extend(patterns)
            print(f"Found {len(patterns)} patterns for {ticker_symbol}.")
        else:
            print(f"No patterns found for {ticker_symbol}.")
        print("-" * 40) # Separator for readability

    print("\n--- Summary of All Found Patterns ---")
    if all_found_patterns:
        for pattern in all_found_patterns:
            print(f"Ticker: {pattern['ticker']} - Pattern End Date: {pattern['pattern_end_date']}")
            print(f"  Initial Low: {pattern['initial_low_price']} on {pattern['initial_low_date']}")
            print(f"  Bounce Peak: {pattern['bounce_peak_price']} on {pattern['bounce_peak_date']}")
            print(f"  Retest Low: {pattern['retest_low_price']} on {pattern['retest_date']}")
            print(f"  Volume (Initial Avg): {pattern['initial_avg_volume']}, Retest Volume: {pattern['retest_volume']} (Ratio: {pattern['volume_ratio']})")
            print("-" * 20)
    else:
        print("No support retest patterns identified across all analyzed stocks.")

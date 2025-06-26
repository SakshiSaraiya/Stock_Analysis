import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import ta

# --- PAGE SETUP ---
st.set_page_config(page_title="Stock Market Analysis", layout="wide")
st.title("📈 Stock Market Analysis Dashboard")

# --- SIDEBAR INPUTS ---
st.sidebar.header("User Input")

popular = st.sidebar.selectbox(
    "Or choose a popular stock:",
    ["None", "AAPL", "MSFT", "GOOGL", "TSLA", "INFY.NS", "TCS.NS"]
)

ticker = st.sidebar.text_input("Enter Stock Ticker Symbol", value="", placeholder="Type a ticker symbol...")

if popular != "None":
    ticker = popular

if not ticker:
    st.warning("Please enter a stock ticker.")
    st.stop()

start_date = st.sidebar.date_input("Start Date", pd.to_datetime("2022-01-01"))
end_date = st.sidebar.date_input("End Date", pd.to_datetime("2024-12-31"))

indicators = st.sidebar.multiselect(
    "Select Technical Indicators",
    ['SMA (20)', 'EMA (20)', 'RSI', 'MACD'],
    default=['SMA (20)', 'RSI']
)

# Glossary
with st.sidebar.expander("📘 Indicator Glossary"):
    st.markdown("""
- **SMA (Simple Moving Average)**: Unweighted average of closing prices.
- **EMA (Exponential Moving Average)**: More weight on recent prices.
- **RSI (Relative Strength Index)**: Oscillator from 0–100 showing momentum. Overbought > 70, Oversold < 30.
- **MACD**: Uses EMAs to show trend direction and momentum crossover.
""")

# --- DATA LOADING ---
@st.cache_data
def load_data(ticker, start, end):
    df = yf.download(ticker, start=start, end=end)
    df.reset_index(inplace=True)
    return df

data = load_data(ticker, start_date, end_date)

if 'Close' not in data.columns:
    st.error("❌ 'Close' column missing.")
    st.stop()

close_col = pd.to_numeric(data['Close'].squeeze(), errors='coerce')
if close_col.isnull().all():
    st.error("❌ 'Close' column contains only NaNs.")
    st.stop()

# --- INDICATORS ---
if 'SMA (20)' in indicators:
    data['SMA20'] = ta.trend.sma_indicator(close=close_col, window=20)

if 'EMA (20)' in indicators:
    data['EMA20'] = ta.trend.ema_indicator(close=close_col, window=20)

if 'RSI' in indicators:
    data['RSI'] = ta.momentum.rsi(close=close_col, window=14)

macd_curr = signal_curr = None
if 'MACD' in indicators:
    try:
        macd_obj = ta.trend.macd(close=close_col)
        data['MACD'] = macd_obj.macd()
        data['Signal_Line'] = macd_obj.macd_signal()
        if not data['MACD'].isnull().all():
            macd_curr = data['MACD'].iloc[-1]
            signal_curr = data['Signal_Line'].iloc[-1]
    except Exception as e:
        st.warning(f"⚠️ MACD error: {e}")
        data['MACD'] = data['Signal_Line'] = None

# --- PRICE CHART ---
st.subheader(f"Price Chart for {ticker.upper()}")

if 'SMA (20)' in indicators or 'EMA (20)' in indicators:
    st.caption("SMA and EMA are averages of past prices. SMA is simple average, EMA gives more weight to recent prices.")

required_cols = ['Open', 'High', 'Low', 'Close']
if set(required_cols).issubset(data.columns):
    try:
        ohlc = data[required_cols + ['Date']].copy().dropna()
        for col in required_cols:
            ohlc[col] = pd.to_numeric(ohlc[col], errors='coerce')
        ohlc = ohlc.dropna()

        if ohlc.empty:
            st.warning("⚠️ No valid OHLC data.")
        else:
            fig = go.Figure()
            fig.add_trace(go.Candlestick(
                x=ohlc['Date'],
                open=ohlc['Open'],
                high=ohlc['High'],
                low=ohlc['Low'],
                close=ohlc['Close'],
                name='Candlestick'
            ))
            if 'SMA (20)' in indicators:
                fig.add_trace(go.Scatter(x=data['Date'], y=data['SMA20'], name='SMA (20)', line=dict(color='blue')))
            if 'EMA (20)' in indicators:
                fig.add_trace(go.Scatter(x=data['Date'], y=data['EMA20'], name='EMA (20)', line=dict(color='orange')))
            fig.update_layout(xaxis_rangeslider_visible=False, height=600)
            st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.warning(f"Error rendering chart: {e}")
else:
    st.warning("Missing OHLC columns.")

# --- RSI CHART ---
if 'RSI' in indicators and 'RSI' in data:
    st.subheader("RSI (Relative Strength Index)")
    st.caption("RSI shows momentum of price movements. >70 = overbought, <30 = oversold.")
    fig_rsi = go.Figure()
    fig_rsi.add_trace(go.Scatter(x=data['Date'], y=data['RSI'], name='RSI', line=dict(color='purple')))
    fig_rsi.add_hline(y=70, line_dash="dash", line_color="red")
    fig_rsi.add_hline(y=30, line_dash="dash", line_color="green")
    fig_rsi.update_layout(height=300)
    st.plotly_chart(fig_rsi, use_container_width=True)

# --- MACD CHART ---
if 'MACD' in indicators and 'MACD' in data and data['MACD'] is not None:
    st.subheader("MACD (Moving Average Convergence Divergence)")
    st.caption("MACD shows trend direction and strength. Crossovers may signal buy/sell.")
    fig_macd = go.Figure()
    fig_macd.add_trace(go.Scatter(x=data['Date'], y=data['MACD'], name='MACD', line=dict(color='blue')))
    fig_macd.add_trace(go.Scatter(x=data['Date'], y=data['Signal_Line'], name='Signal Line', line=dict(color='red')))
    fig_macd.update_layout(height=300)
    st.plotly_chart(fig_macd, use_container_width=True)

# --- KEY METRICS ---
st.subheader("📊 Key Metrics")
col1, col2, col3 = st.columns(3)
col1.metric("Latest Close", f"${float(data['Close'].iloc[-1]):.2f}")
col2.metric("52W High", f"${float(data['High'].max()):.2f}")
col3.metric("52W Low", f"${float(data['Low'].min()):.2f}")

# --- FUNDAMENTALS ---
st.subheader("📘 Fundamental Ratio Analysis")
ticker_obj = yf.Ticker(ticker)
info = ticker_obj.info

col4, col5, col6 = st.columns(3)
col4.metric("P/E Ratio", f"{info.get('trailingPE', 'N/A')}")
col5.metric("EPS (TTM)", f"{info.get('trailingEps', 'N/A')}")
col6.metric("ROE", f"{info.get('returnOnEquity', 0) * 100:.2f}%" if info.get('returnOnEquity') else "N/A")

col7, col8, col9 = st.columns(3)
col7.metric("Debt/Equity", f"{info.get('debtToEquity', 'N/A')}")
col8.metric("P/B Ratio", f"{info.get('priceToBook', 'N/A')}")
col9.metric("Market Cap", f"${info.get('marketCap', 0):,.0f}")

# --- INVESTMENT INSIGHTS ---
st.subheader("💡 Investment Insights")

# RSI Trend
if 'RSI' in indicators and 'RSI' in data:
    latest_rsi = data['RSI'].iloc[-1]
    prev_rsi = data['RSI'].iloc[-2] if len(data) > 1 else latest_rsi
    if latest_rsi > 70 and prev_rsi <= 70:
        st.warning("📈 RSI just entered overbought zone — caution advised.")
    elif latest_rsi < 30 and prev_rsi >= 30:
        st.success("📉 RSI just entered oversold zone — potential buying opportunity.")
    else:
        st.info("RSI indicates neutral market condition.")

# MACD Crossovers
if macd_curr is not None and signal_curr is not None:
    prev_macd = data['MACD'].iloc[-2] if len(data) > 1 else macd_curr
    prev_signal = data['Signal_Line'].iloc[-2] if len(data) > 1 else signal_curr
    if prev_macd < prev_signal and macd_curr > signal_curr:
        st.success("📈 Bullish MACD crossover detected — trend reversal likely upward.")
    elif prev_macd > prev_signal and macd_curr < signal_curr:
        st.warning("📉 Bearish MACD crossover detected — possible downward trend.")
    else:
        st.info("MACD trend stable — no crossover change detected.")

# --- RAW DATA VIEW ---
with st.expander("📋 View Raw Data"):
    st.dataframe(data.tail(100))

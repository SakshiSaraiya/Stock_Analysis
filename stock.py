import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import ta
from textblob import TextBlob

# Page config
st.set_page_config(page_title="Stock Market Analysis", layout="wide")
st.title("📈 Stock Market Analysis Dashboard")

# Sidebar inputs
st.sidebar.header("User Input")

# Popular stock dropdown
popular = st.sidebar.selectbox(
    "Or choose a popular stock:",
    ["None", "AAPL", "MSFT", "GOOGL", "TSLA", "INFY.NS", "TCS.NS"]
)

# Manual input
ticker = st.sidebar.text_input(
    "Enter Stock Ticker Symbol (e.g., AAPL, MSFT, INFY.NS)", 
    value="", 
    placeholder="Type a ticker symbol..."
)

# Use dropdown if selected
if popular != "None":
    ticker = popular

# Stop if no ticker
if not ticker:
    st.warning("Please enter a stock ticker in the sidebar to view the analysis.")
    st.stop()

# Date range
start_date = st.sidebar.date_input("Start Date", pd.to_datetime("2022-01-01"))
end_date = st.sidebar.date_input("End Date", pd.to_datetime("2024-12-31"))

# Indicators
indicators = st.sidebar.multiselect(
    "Select Technical Indicators",
    ['SMA (20)', 'EMA (20)', 'RSI', 'MACD'],
    default=['SMA (20)', 'RSI']
)

# Load stock data
@st.cache_data
def load_data(ticker, start, end):
    df = yf.download(ticker, start=start, end=end)
    df.reset_index(inplace=True)
    return df

data = load_data(ticker, start_date, end_date)

# Defensive check
if 'Close' not in data.columns:
    st.error("❌ 'Close' column not found in data.")
    st.stop()

close_col = pd.to_numeric(data['Close'].squeeze(), errors='coerce')
if close_col.isnull().all():
    st.error("❌ 'Close' price data is invalid or missing for this stock.")
    st.stop()

# Apply technical indicators
if 'SMA (20)' in indicators:
    data['SMA20'] = ta.trend.sma_indicator(close=close_col, window=20)

if 'EMA (20)' in indicators:
    data['EMA20'] = ta.trend.ema_indicator(close=close_col, window=20)

if 'RSI' in indicators:
    data['RSI'] = ta.momentum.rsi(close=close_col, window=14)

# MACD Handling
macd_curr = signal_curr = None
if 'MACD' in indicators:
    try:
        macd_obj = ta.trend.macd(close=close_col)
        data['MACD'] = macd_obj.macd()
        data['Signal_Line'] = macd_obj.macd_signal()
        if data['MACD'].isnull().all() or data['Signal_Line'].isnull().all():
            st.warning("⚠️ MACD could not be computed due to insufficient data.")
            data['MACD'] = data['Signal_Line'] = None
        else:
            macd_curr = data['MACD'].iloc[-1]
            signal_curr = data['Signal_Line'].iloc[-1]
    except Exception as e:
        st.warning(f"⚠️ MACD calculation error: {e}")
        data['MACD'] = data['Signal_Line'] = None

# Price chart
st.subheader(f"Price Chart for {ticker.upper()}")
fig = go.Figure()
fig.add_trace(go.Candlestick(
    x=data['Date'],
    open=data['Open'],
    high=data['High'],
    low=data['Low'],
    close=data['Close'],
    name='Candlestick'
))
if 'SMA (20)' in indicators and 'SMA20' in data:
    fig.add_trace(go.Scatter(x=data['Date'], y=data['SMA20'], name='SMA (20)', line=dict(color='blue')))
if 'EMA (20)' in indicators and 'EMA20' in data:
    fig.add_trace(go.Scatter(x=data['Date'], y=data['EMA20'], name='EMA (20)', line=dict(color='orange')))
fig.update_layout(xaxis_rangeslider_visible=False, height=600)
st.plotly_chart(fig, use_container_width=True)

# RSI chart
if 'RSI' in indicators and 'RSI' in data:
    st.subheader("RSI (Relative Strength Index)")
    fig_rsi = go.Figure()
    fig_rsi.add_trace(go.Scatter(x=data['Date'], y=data['RSI'], line=dict(color='purple'), name='RSI'))
    fig_rsi.add_hline(y=70, line_dash="dash", line_color="red")
    fig_rsi.add_hline(y=30, line_dash="dash", line_color="green")
    fig_rsi.update_layout(height=300)
    st.plotly_chart(fig_rsi, use_container_width=True)

# MACD chart
if 'MACD' in indicators and 'MACD' in data and data['MACD'] is not None:
    st.subheader("MACD")
    fig_macd = go.Figure()
    fig_macd.add_trace(go.Scatter(x=data['Date'], y=data['MACD'], name='MACD', line=dict(color='blue')))
    fig_macd.add_trace(go.Scatter(x=data['Date'], y=data['Signal_Line'], name='Signal Line', line=dict(color='red')))
    fig_macd.update_layout(height=300)
    st.plotly_chart(fig_macd, use_container_width=True)

# Key metrics
st.subheader("📊 Key Metrics")
col1, col2, col3 = st.columns(3)
col1.metric("Latest Close", f"${float(data['Close'].iloc[-1]):.2f}")
col2.metric("52W High", f"${float(data['High'].max()):.2f}")
col3.metric("52W Low", f"${float(data['Low'].min()):.2f}")

# Fundamental ratios
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

# Investment strategy insights
st.subheader("💡 Investment Insights")
if 'RSI' in indicators and 'RSI' in data:
    latest_rsi = data['RSI'].iloc[-1]
    if latest_rsi > 70:
        st.warning("RSI indicates the stock is overbought – Consider waiting for a dip.")
    elif latest_rsi < 30:
        st.success("RSI indicates the stock is oversold – Potential buying opportunity.")
    else:
        st.info("RSI indicates neutral condition.")

if macd_curr is not None and signal_curr is not None:
    if pd.notnull(macd_curr) and pd.notnull(signal_curr):
        if macd_curr > signal_curr:
            st.success("MACD crossover suggests a bullish signal.")
        elif macd_curr < signal_curr:
            st.warning("MACD crossover suggests a bearish signal.")
        else:
            st.info("MACD is flat – No clear trend.")
    else:
        st.info("MACD signal not available due to null values.")

# Raw data
with st.expander("📋 View Raw Data"):
    st.dataframe(data.tail(100))

# Sentiment analysis
st.subheader("🗞️ News Sentiment Analysis")
try:
    news = ticker_obj.news
    if news:
        for i in range(min(5, len(news))):
            headline = news[i]['title']
            sentiment = TextBlob(headline).sentiment.polarity
            if sentiment > 0.1:
                st.success(f"🔼 {headline}")
            elif sentiment < -0.1:
                st.error(f"🔻 {headline}")
            else:
                st.info(f"➖ {headline}")
    else:
        st.write("No recent news available.")
except:
    st.warning("Sentiment analysis not available for this ticker.")

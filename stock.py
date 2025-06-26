import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import ta
from textblob import TextBlob

st.set_page_config(page_title="Stock Market Analysis", layout="wide")
st.title("📈 Stock Market Analysis Dashboard")

# Sidebar inputs
st.sidebar.header("User Input")
popular = st.sidebar.selectbox("Or choose a popular stock:", ["None", "AAPL", "MSFT", "GOOGL", "TSLA", "INFY.NS", "TCS.NS"])
ticker = st.sidebar.text_input("Enter Stock Ticker Symbol", value="", placeholder="e.g. AAPL, MSFT")

if popular != "None":
    ticker = popular

if not ticker:
    st.warning("Please enter a stock ticker.")
    st.stop()

start_date = st.sidebar.date_input("Start Date", pd.to_datetime("2022-01-01"))
end_date = st.sidebar.date_input("End Date", pd.to_datetime("2024-12-31"))

indicators = st.sidebar.multiselect("Select Technical Indicators", ['SMA (20)', 'EMA (20)', 'RSI', 'MACD'], default=['SMA (20)', 'RSI'])

@st.cache_data
def load_data(ticker, start, end):
    df = yf.download(ticker, start=start, end=end)
    df.reset_index(inplace=True)
    return df

data = load_data(ticker, start_date, end_date)

if 'Close' not in data.columns or data['Close'].isnull().all():
    st.error("❌ No valid 'Close' data found.")
    st.stop()

close_col = pd.to_numeric(data['Close'], errors='coerce')

if 'SMA (20)' in indicators:
    data['SMA20'] = ta.trend.sma_indicator(close=close_col, window=20)
if 'EMA (20)' in indicators:
    data['EMA20'] = ta.trend.ema_indicator(close=close_col, window=20)
if 'RSI' in indicators:
    data['RSI'] = ta.momentum.rsi(close=close_col, window=14)
if 'MACD' in indicators:
    try:
        macd_obj = ta.trend.macd(close=close_col)
        data['MACD'] = macd_obj.macd()
        data['Signal_Line'] = macd_obj.macd_signal()
        if data['MACD'].isnull().all():
            data['MACD'] = data['Signal_Line'] = None
    except:
        data['MACD'] = data['Signal_Line'] = None

# Price Chart
st.subheader(f"Price Chart for {ticker.upper()}")
fig = go.Figure()
fig.add_trace(go.Candlestick(x=data['Date'], open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'], name='Candlestick'))

if 'SMA (20)' in indicators and 'SMA20' in data:
    fig.add_trace(go.Scatter(x=data['Date'], y=data['SMA20'], name='SMA (20)', line=dict(color='blue')))
if 'EMA (20)' in indicators and 'EMA20' in data:
    fig.add_trace(go.Scatter(x=data['Date'], y=data['EMA20'], name='EMA (20)', line=dict(color='orange')))

fig.update_layout(xaxis_rangeslider_visible=False, height=600)
st.plotly_chart(fig, use_container_width=True)

if 'SMA (20)' in indicators or 'EMA (20)' in indicators:
    with st.expander("ℹ️ SMA & EMA Definitions"):
        st.markdown("""
        - **SMA (Simple Moving Average):** Average of closing prices over a specific period.
        - **EMA (Exponential Moving Average):** Like SMA but gives more weight to recent prices.
        """)

# RSI Chart
if 'RSI' in indicators and 'RSI' in data:
    st.subheader("RSI (Relative Strength Index)")
    fig_rsi = go.Figure()
    fig_rsi.add_trace(go.Scatter(x=data['Date'], y=data['RSI'], name='RSI', line=dict(color='purple')))
    fig_rsi.add_hline(y=70, line_dash="dash", line_color="red")
    fig_rsi.add_hline(y=30, line_dash="dash", line_color="green")
    fig_rsi.update_layout(height=300)
    st.plotly_chart(fig_rsi, use_container_width=True)

    with st.expander("ℹ️ RSI Definition"):
        st.markdown("""
        - **RSI:** A momentum indicator showing whether a stock is overbought (>70) or oversold (<30).
        """)

# MACD Chart
if 'MACD' in indicators and data['MACD'] is not None:
    st.subheader("MACD")
    fig_macd = go.Figure()
    fig_macd.add_trace(go.Scatter(x=data['Date'], y=data['MACD'], name='MACD', line=dict(color='blue')))
    fig_macd.add_trace(go.Scatter(x=data['Date'], y=data['Signal_Line'], name='Signal Line', line=dict(color='red')))
    fig_macd.update_layout(height=300)
    st.plotly_chart(fig_macd, use_container_width=True)

    with st.expander("ℹ️ MACD Definition"):
        st.markdown("""
        - **MACD:** Trend-following momentum indicator using difference of EMAs.
        - Crossovers suggest trend changes.
        """)

# Key Metrics
st.subheader("📊 Key Metrics")
col1, col2, col3 = st.columns(3)
col1.metric("Latest Close", f"${float(data['Close'].iloc[-1]):.2f}")
col2.metric("52W High", f"${float(data['High'].max()):.2f}")
col3.metric("52W Low", f"${float(data['Low'].min()):.2f}")

# Fundamentals
st.subheader("📘 Fundamental Ratios")
info = yf.Ticker(ticker).info
col4, col5, col6 = st.columns(3)
col4.metric("P/E Ratio", f"{info.get('trailingPE', 'N/A')}")
col5.metric("EPS (TTM)", f"{info.get('trailingEps', 'N/A')}")
col6.metric("ROE", f"{info.get('returnOnEquity', 0) * 100:.2f}%" if info.get('returnOnEquity') else "N/A")

col7, col8, col9 = st.columns(3)
col7.metric("Debt/Equity", f"{info.get('debtToEquity', 'N/A')}")
col8.metric("P/B Ratio", f"{info.get('priceToBook', 'N/A')}")
col9.metric("Market Cap", f"${info.get('marketCap', 0):,.0f}")

# Investment Insights
st.subheader("💡 Investment Insights")
if 'RSI' in indicators and 'RSI' in data and not data['RSI'].isna().all():
    latest_rsi = data['RSI'].dropna().iloc[-1]
    if latest_rsi > 70:
        st.warning("RSI > 70: Overbought – Consider waiting for a dip.")
    elif latest_rsi < 30:
        st.success("RSI < 30: Oversold – Potential buying opportunity.")
    else:
        st.info("RSI in neutral range (30–70).")

if 'MACD' in indicators and data['MACD'] is not None and not data['MACD'].isna().all():
    macd_curr = data['MACD'].dropna().iloc[-1]
    signal_curr = data['Signal_Line'].dropna().iloc[-1]
    if macd_curr > signal_curr:
        st.success("MACD crossover (MACD > Signal): Bullish signal.")
    elif macd_curr < signal_curr:
        st.warning("MACD crossover (MACD < Signal): Bearish signal.")
    else:
        st.info("MACD ≈ Signal – No strong trend detected.")

# Raw Data
with st.expander("📋 View Raw Data"):
    st.dataframe(data.tail(100))

# News Sentiment
st.subheader("🗞️ News Sentiment Analysis")
try:
    news = yf.Ticker(ticker).news
    if news:
        seen_titles = set()
        for article in news[:5]:
            title = article['title']
            if title in seen_titles:
                continue
            seen_titles.add(title)

            sentiment = TextBlob(title).sentiment.polarity
            label = f"🕒 {article.get('publisher', '')} – {title}"

            if sentiment > 0.1:
                st.success(f"🔼 {label}")
            elif sentiment < -0.1:
                st.error(f"🔻 {label}")
            else:
                st.info(f"➖ {label}")
    else:
        st.write("No recent news available.")
except Exception as e:
    st.warning("Sentiment analysis not available.")

from flask import Flask, render_template_string
import yfinance as yf
import pandas as pd
import requests

app = Flask(__name__)

# Core liquid watchlist for fast loading & reliable execution
WATCHLIST = [
    "NVDA", "AAPL", "GOOGL", "MSFT", "AMZN", "META", "TSLA", 
    "AMD", "PLTR", "GME", "QQQ", "SPY", "COIN", "MU", "SMCI"
]

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>⚡ PRE-MARKET & SIGNAL TERMINAL</title>
    <meta http-equiv="refresh" content="30">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { background-color: #0d1117; color: #c9d1d9; font-family: monospace; padding: 15px; margin: 0; }
        h1 { color: #58a6ff; text-align: center; margin: 10px 0 5px 0; font-size: 1.3rem; }
        .sub { text-align: center; color: #8b949e; font-size: 0.8rem; margin-bottom: 20px; }
        .card { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 12px; margin-bottom: 20px; overflow-x: auto; }
        h2 { border-bottom: 2px solid #30363d; padding-bottom: 6px; font-size: 0.95rem; margin-top: 0; }
        .green { color: #3fb950; font-weight: bold; }
        .red { color: #f85149; font-weight: bold; }
        .rvol-high { background-color: #238636; color: #ffffff; padding: 2px 6px; border-radius: 4px; font-weight: bold; }
        table { width: 100%; border-collapse: collapse; margin-top: 5px; font-size: 0.85rem; }
        td, th { padding: 8px 6px; text-align: left; border-bottom: 1px solid #21262d; white-space: nowrap; }
        th { color: #8b949e; font-size: 0.75rem; text-transform: uppercase; }
        tr:nth-child(even) { background-color: #161b22; }
        tr:hover { background-color: #21262d; }
        .ticker { font-weight: bold; font-size: 0.95rem; color: #f0f6fc; }
        .wsb-header { color: #f0883e; font-weight: bold; }
        
        /* SIGNAL BADGES */
        .signal-buy { background-color: #238636; color: #ffffff; padding: 3px 8px; border-radius: 4px; font-weight: bold; font-size: 0.75rem; }
        .signal-caution { background-color: #d29922; color: #000000; padding: 3px 8px; border-radius: 4px; font-weight: bold; font-size: 0.75rem; }
        .signal-noplay { background-color: #21262d; color: #8b949e; padding: 3px 8px; border-radius: 4px; font-size: 0.75rem; }
    </style>
</head>
<body>
    <h1>⚡ PRE-MARKET SIGNAL TERMINAL</h1>
    <div class="sub">RVOL ≥ 1.5x & Volume ≥ 100K Rules Engine</div>
    
    <!-- PRE-MARKET GAINERS WITH BUY SIGNAL -->
    <div class="card">
        <h2 class="green">🚀 PRE-MARKET GAINERS & SIGNALS</h2>
        <table>
            <tr>
                <th>Trade Signal</th>
                <th>Ticker</th>
                <th>Price</th>
                <th>Pre Chg %</th>
                <th>Pre Vol</th>
                <th>RVOL</th>
            </tr>
            {% for stock in pre_gainers %}
            <tr>
                <td>
                    {% if stock.signal == 'BUYABLE' %}
                        <span class="signal-buy">BUYABLE 🚀</span>
                    {% elif stock.signal == 'CAUTION' %}
                        <span class="signal-caution">LOW VOL ⚠️</span>
                    {% else %}
                        <span class="signal-noplay">NO PLAY</span>
                    {% endif %}
                </td>
                <td class="ticker">{{ stock.ticker }}</td>
                <td>${{ stock.ext_price }}</td>
                <td class="green">+{{ stock.ext_change }}%</td>
                <td>{{ stock.pre_vol_fmt }}</td>
                <td>
                    {% if stock.rvol >= 1.5 %}
                        <span class="rvol-high">{{ stock.rvol }}x 🔥</span>
                    {% else %}
                        {{ stock.rvol }}x
                    {% endif %}
                </td>
            </tr>
            {% endfor %}
        </table>
    </div>

    <!-- REDDIT SENTIMENT SECTION -->
    <div class="card">
        <h2 class="wsb-header">🦍 TOP TRENDING ON REDDIT (WSB)</h2>
        <table>
            <tr>
                <th>Rank</th>
                <th>Ticker</th>
                <th>Mentions</th>
                <th>Upvotes</th>
            </tr>
            {% for item in reddit_trending %}
            <tr>
                <td>#{{ item.rank }}</td>
                <td class="ticker">{{ item.ticker }}</td>
                <td class="green">{{ item.mentions }} 🔥</td>
                <td>{{ item.upvotes }}</td>
            </tr>
            {% endfor %}
        </table>
    </div>
</body>
</html>
"""

def format_vol(n):
    if not n or n == 0:
        return "-"
    if n >= 1e6:
        return f"{round(n/1e6, 2)}M"
    if n >= 1e3:
        return f"{round(n/1e3, 1)}K"
    return str(n)

def evaluate_signal(ext_change, pre_vol, rvol):
    # Buy signal rules
    if ext_change >= 2.0 and rvol >= 1.5 and pre_vol >= 100000:
        return 'BUYABLE'
    elif ext_change >= 2.0 and (rvol < 1.5 or pre_vol < 100000):
        return 'CAUTION'
    return 'NO PLAY'

def get_reddit_sentiment():
    try:
        url = "https://apewisdom.io/api/v1/filter/all-stocks/page/1"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        res = requests.get(url, headers=headers, timeout=5)
        
        if res.status_code == 200:
            data = res.json()
            results = data.get('results', [])[:10]
            
            parsed = []
            for item in results:
                parsed.append({
                    'rank': item.get('rank', '-'),
                    'ticker': item.get('ticker', ''),
                    'mentions': item.get('mentions', 0),
                    'upvotes': item.get('upvotes', 0)
                })
            return parsed
        return []
    except Exception:
        return []

@app.route('/')
def index():
    data_list = []

    for symbol in WATCHLIST:
        try:
            t = yf.Ticker(symbol)
            info = t.info
            
            previous_close = info.get('previousClose', 1) or 1
            current_price = info.get('currentPrice') or info.get('regularMarketPrice') or previous_close
            
            ext_price = info.get('preMarketPrice') or info.get('postMarketPrice') or current_price
            ext_change = round(((ext_price - previous_close) / previous_close) * 100, 2)
            
            pre_vol = info.get('preMarketVolume') or info.get('volume') or 0
            avg_vol = info.get('averageVolume10days') or info.get('averageDailyVolume10Day') or 1
            
            rvol = round(pre_vol / (avg_vol / 13), 2) if avg_vol > 0 else 0
            signal = evaluate_signal(ext_change, pre_vol, rvol)

            data_list.append({
                'ticker': symbol,
                'ext_price': round(ext_price, 2),
                'ext_change': ext_change,
                'pre_vol_fmt': format_vol(pre_vol),
                'rvol': rvol,
                'signal': signal
            })
        except Exception:
            continue

    if data_list:
        df = pd.DataFrame(data_list)
        pre_gainers = df.sort_values(by='ext_change', ascending=False).head(10).to_dict('records')
    else:
        pre_gainers = []

    reddit_trending = get_reddit_sentiment()

    return render_template_string(
        HTML_TEMPLATE, 
        pre_gainers=pre_gainers, 
        reddit_trending=reddit_trending
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=5000)

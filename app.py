from flask import Flask, render_template_string
import yfinance as yf
import pandas as pd
import requests
from datetime import datetime

app = Flask(__name__)

WATCHLIST = [
    "NVDA", "AAPL", "GOOGL", "MSFT", "AMZN", "AVGO", "META", "TSLA", 
    "LLY", "BRK-A", "MU", "JPM", "WMT", "AMD", "PLTR", "GME", "QQQ", 
    "SPY", "BAC", "XOM", "UNH", "V", "MA", "PG", "HD", "CVX", "COST", 
    "ABBV", "MRK", "NFLX", "CRM", "BABA", "COIN", "ORCL", "SMCI", "INTC",
    "RKLB", "SNDK"
]

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>⚡ PRE-MARKET, WSB & NEWS TERMINAL</title>
    <meta http-equiv="refresh" content="30">
    <style>
        body { background-color: #0d1117; color: #c9d1d9; font-family: monospace; padding: 15px; margin: 0; }
        h1 { color: #58a6ff; text-align: center; margin: 10px 0 5px 0; font-size: 1.4rem; }
        .sub { text-align: center; color: #8b949e; font-size: 0.8rem; margin-bottom: 20px; }
        .card { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 12px; margin-bottom: 20px; overflow-x: auto; }
        h2 { border-bottom: 2px solid #30363d; padding-bottom: 6px; font-size: 1rem; margin-top: 0; }
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
        .news-header { color: #d2a8ff; font-weight: bold; }
        
        .tag-bullish { background-color: #238636; color: #fff; padding: 2px 6px; border-radius: 4px; font-size: 0.75rem; font-weight: bold; }
        .tag-bearish { background-color: #da3633; color: #fff; padding: 2px 6px; border-radius: 4px; font-size: 0.75rem; font-weight: bold; }
        .tag-neutral { background-color: #30363d; color: #8b949e; padding: 2px 6px; border-radius: 4px; font-size: 0.75rem; }
        .news-title { white-space: normal; word-break: break-word; max-width: 300px; font-size: 0.8rem; }
    </style>
</head>
<body>
    <h1>⚡ PRE-MARKET MOMENTUM TERMINAL</h1>
    <div class="sub">Large Cap ($10B+) • Pure Pre-Market, WSB & News Radar</div>
    
    <!-- PRE-MARKET GAINERS -->
    <div class="card">
        <h2 class="green">🚀 TOP PRE-MARKET GAINERS</h2>
        <table>
            <tr>
                <th>Ticker</th>
                <th>Pre Price</th>
                <th>Pre Chg %</th>
                <th>Pre Vol</th>
                <th>RVOL</th>
                <th>52W High</th>
                <th>52W Low</th>
            </tr>
            {% for stock in pre_gainers %}
            <tr>
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
                <td>${{ stock.fifty_two_high }}</td>
                <td>${{ stock.fifty_two_low }}</td>
            </tr>
            {% endfor %}
        </table>
    </div>

    <!-- PRE-MARKET LOSERS -->
    <div class="card">
        <h2 class="red">📉 TOP PRE-MARKET LOSERS</h2>
        <table>
            <tr>
                <th>Ticker</th>
                <th>Pre Price</th>
                <th>Pre Chg %</th>
                <th>Pre Vol</th>
                <th>RVOL</th>
                <th>52W High</th>
                <th>52W Low</th>
            </tr>
            {% for stock in pre_losers %}
            <tr>
                <td class="ticker">{{ stock.ticker }}</td>
                <td>${{ stock.ext_price }}</td>
                <td class="red">{{ stock.ext_change }}%</td>
                <td>{{ stock.pre_vol_fmt }}</td>
                <td>{{ stock.rvol }}x</td>
                <td>${{ stock.fifty_two_high }}</td>
                <td>${{ stock.fifty_two_low }}</td>
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

    <!-- NEWS & SENTIMENT RADAR -->
    <div class="card">
        <h2 class="news-header">📰 LATEST NEWS & SENTIMENT</h2>
        <table>
            <tr>
                <th>Ticker</th>
                <th>Sentiment</th>
                <th>Headline</th>
                <th>Publisher</th>
            </tr>
            {% for news in news_list %}
            <tr>
                <td class="ticker">{{ news.ticker }}</td>
                <td>
                    {% if news.sentiment == 'BULLISH' %}
                        <span class="tag-bullish">BULLISH 🚀</span>
                    {% elif news.sentiment == 'BEARISH' %}
                        <span class="tag-bearish">BEARISH 📉</span>
                    {% else %}
                        <span class="tag-neutral">NEUTRAL</span>
                    {% endif %}
                </td>
                <td class="news-title"><a href="{{ news.link }}" target="_blank" style="color: #c9d1d9; text-decoration: none;">{{ news.title }}</a></td>
                <td style="color: #8b949e;">{{ news.publisher }}</td>
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

def analyze_sentiment(title):
    title_lower = title.lower()
    bullish_keywords = ['surge', 'soar', 'record', 'gain', 'jump', 'upgrade', 'profit', 'beat', 'buy', 'rally', 'bull', 'high']
    bearish_keywords = ['drop', 'plunge', 'fall', 'sink', 'downgrade', 'miss', 'loss', 'lawsuit', 'sell', 'bear', 'low', 'dump']
    
    bull_score = sum(1 for word in bullish_keywords if word in title_lower)
    bear_score = sum(1 for word in bearish_keywords if word in title_lower)
    
    if bull_score > bear_score:
        return 'BULLISH'
    elif bear_score > bull_score:
        return 'BEARISH'
    return 'NEUTRAL'

def get_reddit_sentiment():
    try:
        url = "https://apewisdom.io/api/v1/by-market/all-stocks"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=5)
        data = res.json()
        results = data.get('results', [])[:10]
        return [{
            'rank': item.get('rank'),
            'ticker': item.get('ticker'),
            'mentions': item.get('mentions'),
            'upvotes': item.get('upvotes')
        } for item in results]
    except Exception:
        return []

def get_stock_news(top_tickers):
    news_items = []
    for symbol in top_tickers[:5]: # Get news for top 5 gainers/movers
        try:
            t = yf.Ticker(symbol)
            news = t.news
            for item in news[:2]: # Top 2 stories per ticker
                content = item.get('content', {})
                title = content.get('title') or item.get('title', '')
                provider = content.get('provider', {}).get('displayName') or item.get('publisher', 'News')
                link = content.get('canonicalUrl', {}).get('url') or item.get('link', '#')
                
                if title:
                    news_items.append({
                        'ticker': symbol,
                        'title': title,
                        'publisher': provider,
                        'link': link,
                        'sentiment': analyze_sentiment(title)
                    })
        except Exception:
            continue
    return news_items

@app.route('/')
def index():
    tickers = yf.Tickers(' '.join(WATCHLIST))
    data_list = []

    for symbol in WATCHLIST:
        try:
            info = tickers.tickers[symbol].info
            
            previous_close = info.get('previousClose', 1)
            current_price = info.get('currentPrice') or info.get('regularMarketPrice', previous_close)
            
            ext_price = info.get('preMarketPrice') or info.get('postMarketPrice') or current_price
            ext_change = round(((ext_price - previous_close) / previous_close) * 100, 2)
            
            pre_vol = info.get('preMarketVolume') or info.get('volume') or 0
            avg_vol = info.get('averageVolume10days') or info.get('averageDailyVolume10Day') or 1
            
            rvol = round(pre_vol / (avg_vol / 13), 2) if avg_vol > 0 else 0
            
            fifty_two_high = info.get('fiftyTwoWeekHigh', 0)
            fifty_two_low = info.get('fiftyTwoWeekLow', 0)

            data_list.append({
                'ticker': symbol,
                'ext_price': round(ext_price, 2),
                'ext_change': ext_change,
                'pre_vol_fmt': format_vol(pre_vol),
                'rvol': rvol,
                'fifty_two_high': round(fifty_two_high, 2),
                'fifty_two_low': round(fifty_two_low, 2)
            })
        except Exception:
            continue

    df = pd.DataFrame(data_list)
    
    pre_gainers_df = df.sort_values(by='ext_change', ascending=False).head(10)
    pre_losers_df = df.sort_values(by='ext_change', ascending=True).head(10)
    
    pre_gainers = pre_gainers_df.to_dict('records')
    pre_losers = pre_losers_df.to_dict('records')
    
    # Get top tickers to fetch news for
    top_movers = [s['ticker'] for s in pre_gainers[:5]]
    news_list = get_stock_news(top_movers)
    
    # Reddit Sentiment
    reddit_trending = get_reddit_sentiment()

    return render_template_string(
        HTML_TEMPLATE, 
        pre_gainers=pre_gainers, 
        pre_losers=pre_losers,
        reddit_trending=reddit_trending,
        news_list=news_list
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=5000)
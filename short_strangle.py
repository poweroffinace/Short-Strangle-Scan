import pandas as pd
import numpy as np
import yfinance as yf
from bs4 import BeautifulSoup
from io import StringIO
from scipy.stats import norm
from nselib import derivatives, capital_market
import requests
import datetime
import os


# ----------------------------
# CONFIG
# ----------------------------
EXPIRY = '26-05-2026'
DAYS_TO_EXPIRY = (pd.to_datetime(EXPIRY, format='%d-%m-%Y') - pd.Timestamp.today()).days
MARGIN = 95000
MIN_RETURN_PCT = 3.5


class MarketScreenerScraper:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Referer": "https://in.marketscreener.com/",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    }
    def __init__(self, nse_code):
        self.nse_code = nse_code
        self.base_url = 'https://in.marketscreener.com'
        self.session = self._create_session()
        self.slug = self.search_slug()

    def _create_session(self):
      session = requests.Session()
      session.headers.update(self.headers)
      return session

    def get_event_calendar_and_news(self):
      data = self.get_event_calendar()
      data.update(self.get_news())
      return data

    def search_slug(self):

        # 1. Get the landing page to establish a session and grab the CSRF token
            res = self.session.get(self.base_url)
            res.raise_for_status()
            soup = BeautifulSoup(res.text, 'html.parser')

            # Extract CSRF token from the element you identified
            csrf_token_tag = soup.select_one('#header-search-csrf')
            if not csrf_token_tag:
                print("Error: Could not find CSRF token.")
                return None

            csrf_token = csrf_token_tag.text.strip()

            # 2. Prepare the POST request for the quick search
            async_search_url = f"{self.base_url}/async/search/quick"
            payload = {
                'csrf_token': csrf_token,
                'search': self.nse_code.lower(),
                'search-type': 1
            }

            # The site expects an XMLHttpRequest (AJAX)
            ajax_headers = {
                'X-Requested-With': 'XMLHttpRequest',
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'
            }

            search_res = self.session.post(async_search_url, data=payload, headers=ajax_headers)
            search_res.raise_for_status()
            soup = BeautifulSoup(search_res.json().get('data', ''), 'html.parser')
            rows = soup.find_all('tr')
            for row in rows:
              cells = row.find_all('td')
              if len(cells) > 3:
                company_name = cells[1].text.strip()
                symbol = cells[2].text.strip()
                if 'inr' in company_name.lower() and self.nse_code.lower() == symbol.lower():
                  return row.get('data-href')


    def get_event_calendar(self):
        if not self.slug:
            print("Error: No slug found.")
            return None

        response = self.session.get(f"{self.base_url}{self.slug}calendar")
        soup = BeautifulSoup(response.text, 'html.parser')

        def _get_events(key, element_id):
          events = soup.select_one(f'#{element_id} table')
          if not events:
              return "No upcoming events found."
          # Wrap the HTML string in StringIO to avoid the FutureWarning
          html_data = StringIO(str(events))
          # Read the table and grab the first 5 entries
          df = pd.read_html(html_data)
          if not df:
            return ''
          df = pd.read_html(html_data)[0].iloc[:5]
          # Combine the description and date columns
          df['Desc'] = df[1].astype(str) + ' on ' + df[0].astype(str)
          return ' || '.join(df['Desc'].to_list())

        return {
            'upcoming-events': _get_events('upcoming-events', 'next-events-card'),
            'past-events': _get_events('past-events', 'past-events-card'),
        }

    def get_news(self):
        if not self.slug:
            print("Error: No slug found.")
            return None

        response = self.session.get(f"{self.base_url}{self.slug}news")
        soup = BeautifulSoup(response.text, 'html.parser')

        def _get_events(key, element_id):
          events = soup.select_one(f'table#{element_id}')
          if not events:
              return "No news found."
          # Wrap the HTML string in StringIO to avoid the FutureWarning
          html_data = StringIO(str(events))
          # Read the table and grab the first 10 entries
          df = pd.read_html(html_data)
          if not df:
            return ''
          df = pd.read_html(html_data)[0].iloc[:10]
          # Combine the description and date columns
          df['Desc'] = df[1].astype(str) + ' on ' + df[0].astype(str)
          return ' || '.join(df['Desc'].to_list())

        return {'news' : _get_events('news', 'newsScreener')}

# Execution
# scraper = MarketScreenerScraper('HDFCLIFE')
# scraper.get_event_calendar_and_news()


# ----------------------------
# FETCH SENSIBULL EVENTS
# ----------------------------
def fetch_sensibull_events():
    session = requests.Session()

    initial_url = "https://web.sensibull.com/stock-market-calendar/stock-results-calendar"

    get_headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "en-US,en;q=0.9",
    }

    session.get(initial_url, headers=get_headers)

    post_headers = {
        "Accept": "application/json, text/plain, */*",
        "User-Agent": "Mozilla/5.0",
        "Origin": "https://web.sensibull.com",
        "Referer": "https://web.sensibull.com/",
    }

    payload = {
        "sectors": [],
        "event_types": [],
        "liquid_only": False,
        "from_date": "2026-04-01",
        "to_date": "2026-05-30"
    }

    api_url = "https://oxide.sensibull.com/v1/compute/market_stock_events"

    response = session.post(api_url, headers=post_headers, json=payload)

    if response.status_code == 200:
        data = response.json()
        return data.get('payload', {}).get('data', [])
    else:
        return []


# ----------------------------
# BUILD RESULT MAP
# ----------------------------
def build_results_calendar_map():
    events = fetch_sensibull_events()

    result_map = {}

    for e in events:
        symbol = e.get('trading_symbol')
        date = e.get('date')

        if symbol:
            result_map[symbol] = date

    return result_map


# ----------------------------
# LOT SIZE
# ----------------------------
def get_lot_size(symbol):
    url = 'https://public.fyers.in/sym_details/NSE_FO.csv'
    df = pd.read_csv(url, header=None)
    df_symbol = df[df[13] == symbol]
    lot_sizes = df_symbol[(df_symbol[16] == 'CE') | (df_symbol[16] == 'PE')][3].unique()
    return lot_sizes[0] if len(lot_sizes) > 0 else None


# ----------------------------
# BLACK-76 POP
# ----------------------------
def prob_F_less_than_K(K, F, sigma, T):
    if sigma == 0:
        return 0
    z = (np.log(K / F) + 0.5 * sigma**2 * T) / (sigma * np.sqrt(T))
    return norm.cdf(z)


# ----------------------------
# BOUNDS + META
# ----------------------------
def get_bounds_and_info(symbol, company_name, industry):
    if True:
        stock = symbol + '.NS'

        df = yf.download(
            stock,
            period='1y',
            interval='1d',
            auto_adjust=False,
            progress=False,
            group_by='column'
        )

        if df.empty or len(df) < 50:
            return None, None, None, company_name, industry

        period = 30

        df['DeltaHigh'] = (df['Close'].rolling(period).max().shift(-period) - df['Close']) * 100 / df['Close']
        df['DeltaLow'] = (df['Close'] - df['Close'].rolling(period).min().shift(-period)) * 100 / df['Close']

        df.dropna(inplace=True)

        if df.empty:
            return None, None, None, company_name, industry

        sdHigh = float(df['DeltaHigh'].std())
        sdLow  = float(df['DeltaLow'].std())

        current_price = float(df['Close'].iloc[len(df)-1].iloc[0])
        # current_price = float(df['Close'].iloc[-1])

        ub = current_price + 2 * sdHigh
        lb = current_price - 2 * sdLow

        return int(lb), int(current_price), int(ub), company_name, industry

    # except Exception as e:
    else:
        print(f"Bounds error {symbol}: {e}")
        return None, None, None, company_name, industry


# ----------------------------
# MAIN FUNCTION
# ----------------------------
def generate_short_strangle_csv():

    # 🔥 Fetch result calendar once
    result_calendar = build_results_calendar_map()

    stock_universe = pd.concat([
        capital_market.nifty50_equity_list(),
        capital_market.niftynext50_equity_list()
    ])

    # randomly select 10 rows
    # stock_universe = stock_universe.sample(n=2)

    results = []

    for idx, row in stock_universe.iterrows():

        SYMBOL = row['Symbol']
        company_name = row['Company Name']
        industry = row['Industry']

        # try:
        if True:
            print(f"Processing {SYMBOL}...")

            FUTURES_PRICE = yf.Ticker(SYMBOL + '.NS').info.get('regularMarketPrice')
            if FUTURES_PRICE is None:
                continue

            LOT_SIZE = get_lot_size(SYMBOL)
            if LOT_SIZE is None:
                continue

            df = derivatives.nse_live_option_chain(symbol=SYMBOL, expiry_date=EXPIRY)

            df['CALLS_IV'] = df['CALLS_IV'] / 100
            df['PUTS_IV'] = df['PUTS_IV'] / 100

            df = df[(df['CALLS_LTP'] > 0) | (df['PUTS_LTP'] > 0)]

            if len(df) == 0:
                continue

            T = DAYS_TO_EXPIRY / 365

            candidates = []

            for _, call_row in df.iterrows():
                for _, put_row in df.iterrows():

                    Kc = call_row['Strike_Price']
                    Kp = put_row['Strike_Price']

                    if Kp >= FUTURES_PRICE or Kc <= FUTURES_PRICE:
                        continue

                    call_premium = call_row['CALLS_LTP']
                    put_premium  = put_row['PUTS_LTP']

                    if call_premium == 0 or put_premium == 0:
                        continue

                    total_premium = call_premium + put_premium

                    max_profit_abs = total_premium * LOT_SIZE
                    max_profit_pct = (max_profit_abs / MARGIN) * 100

                    if max_profit_pct < MIN_RETURN_PCT:
                        continue

                    sigma_call = call_row['CALLS_IV']
                    sigma_put  = put_row['PUTS_IV']

                    avg_sigma = (sigma_call + sigma_put) / 2
                    std_move = FUTURES_PRICE * avg_sigma * np.sqrt(T)

                    if std_move == 0:
                        continue

                    call_std = (Kc - FUTURES_PRICE) / std_move
                    put_std  = (FUTURES_PRICE - Kp) / std_move

                    std_multiple = min(call_std, put_std)

                    prob_below_call = prob_F_less_than_K(Kc, FUTURES_PRICE, sigma_call, T)
                    prob_below_put  = prob_F_less_than_K(Kp, FUTURES_PRICE, sigma_put, T)

                    POP = (prob_below_call - prob_below_put) * 100

                    lower_be = Kp - total_premium
                    upper_be = Kc + total_premium

                    candidates.append({
                        "Kc": Kc,
                        "Kp": Kp,
                        "call_premium": call_premium,
                        "put_premium": put_premium,
                        "total_premium": total_premium,
                        "max_profit_abs": max_profit_abs,
                        "max_profit_pct": max_profit_pct,
                        "POP": POP,
                        "std_multiple": std_multiple,
                        "lower_be": lower_be,
                        "upper_be": upper_be
                    })

            if len(candidates) == 0:
                continue

            best = sorted(candidates, key=lambda x: x['std_multiple'], reverse=True)[0]

            lb, current_price, ub, cname, ind = get_bounds_and_info(
                SYMBOL, company_name, industry
            )

            # 🔥 Result date + days calculation
            result_date = result_calendar.get(SYMBOL, None)

            days_to_result = (
                (pd.to_datetime(result_date) - pd.Timestamp.today()).days
                if result_date else None
            )

            scraper = MarketScreenerScraper(SYMBOL)
            event_calendar_and_news = scraper.get_event_calendar_and_news()

            results.append({
                "Symbol": SYMBOL,
                "Company Name": cname,
                "Industry": ind,
                "Current Price": current_price,
                "Lower Bound": lb,
                "Upper Bound": ub,
                "Result Date": result_date,
                "Days to Result": days_to_result,
                "Sell Put @": best['Kp'],
                "Sell Put Premium": best['put_premium'],
                "Sell Call @": best['Kc'],
                "Sell Call Premium": best['call_premium'],
                "Max Profit (₹)": round(best['max_profit_abs'], 2),
                "Max Profit (%)": round(best['max_profit_pct'], 2),
                "POP (%)": round(best['POP'], 2),
                "Std Multiple": round(best['std_multiple'], 2),
                "Break Even Lower": round(best['lower_be'], 2),
                "Break Even Upper": round(best['upper_be'], 2),
                "Upcoming Events": event_calendar_and_news['upcoming-events'],
                "Past Events": event_calendar_and_news['past-events'],
                "News": event_calendar_and_news['news']
            })

        # except Exception as e:
        else:
            print(f"Skipping {SYMBOL}: {e}")
            continue

    result_df = pd.DataFrame(results)

    result_df = result_df.sort_values(by="Std Multiple", ascending=False)

    # result_df.to_csv("short_strangle_pro.csv", index=False)
    # result_df save to short_strangle_pro_<date_time in yyyy-mm-dd-hh-mm format>
    os.makedirs(os.path.join('data'), exist_ok=True)
    result_df.to_csv(os.path.join('data', f"short_strangle_pro_{datetime.datetime.now().strftime('%Y-%m-%d-%H-%M')}.csv"), index=False)

    print("\n✅ CSV Generated: short_strangle_pro.csv")
    print(result_df.head())


# ----------------------------
# RUN
# ----------------------------
generate_short_strangle_csv()

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
import time  # Added for retry delays
from optionlab import run_strategy

# ----------------------------
# CONFIG
# ----------------------------
EXPIRY = '30-06-2026'
DAYS_TO_EXPIRY = (pd.to_datetime(EXPIRY, format='%d-%m-%Y') - pd.Timestamp.today()).days

# ----------------------------
# MARKETSCREENER SCRAPER to get events and news
# ----------------------------
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

    slugs = {
        "AXISBANK" : "/quote/stock/AXIS-BANK-LIMITED-17067783/",
        "ADANIENT" : "/quote/stock/ADANI-ENTERPRISES-LIMITED-9059510/",
        "ADANIPORTS" : "/quote/stock/ADANI-PORTS-SPECIAL-ECONO-9059803/",
        "APOLLOHOSP" : "/quote/stock/APOLLO-HOSPITALS-ENTERPRI-9058923/",
        "ASIANPAINT" : "/quote/stock/ASIAN-PAINTS-LIMITED-13891348/",
        "BAJAJ-AUTO" : "/quote/stock/BAJAJ-AUTO-LIMITED-9059975/",
        "BAJFINANCE" : "/quote/stock/BAJAJ-FINANCE-LIMITED-190468329/",
        "BAJAJFINSV" : "/quote/stock/BAJAJ-FINSERV-LTD-9059974/",
        "CIPLA" : "/quote/stock/CIPLA-LIMITED-9058821/",
        "COALINDIA" : "/quote/stock/COAL-INDIA-LIMITED-9060008/",
        "ETERNAL" : "/quote/stock/ETERNAL-LIMITED-125138034/",
        "GRASIM" : "/quote/stock/GRASIM-INDUSTRIES-LIMITED-33647063/",
        "HCLTECH" : "/quote/stock/HCL-TECHNOLOGIES-LIMITED-9058931/",
        "HDFCBANK" : "/quote/stock/HDFC-BANK-LIMITED-105516154/",
        "HDFCLIFE" : "/quote/stock/HDFC-LIFE-INSURANCE-COMPA-105516321/",
        "HINDUNILVR" : "/quote/stock/HINDUSTAN-UNILEVER-LIMITE-9058826/",
        "ICICIBANK" : "/quote/stock/ICICI-BANK-LIMITED-23672738/",
        "ITC" : "/quote/stock/ITC-LIMITED-9743470/",
        "INFY" : "/quote/stock/INFOSYS-LIMITED-9743342/",
        "INDIGO" : "/quote/stock/INTERGLOBE-AVIATION-LIMIT-25531239/",
        "JIOFIN" : "/quote/stock/JIO-FINANCIAL-SERVICES-LI-157409091/",
        "M&M" : "/quote/stock/MAHINDRA-MAHINDRA-LIMITED-9058830/",
        "MARUTI" : "/quote/stock/MARUTI-SUZUKI-INDIA-LTD-9059169/",
        "NTPC" : "/quote/stock/NTPC-LTD-9743456/",
        "ONGC" : "/quote/stock/OIL-AND-NATURAL-GAS-CORPO-9743117/",
        "POWERGRID" : "/quote/stock/POWER-GRID-CORPORATION-OF-9059859/",
        "RELIANCE" : "/quote/stock/RELIANCE-INDUSTRIES-LTD-9058833/",
        "SBILIFE" : "/quote/stock/SBI-LIFE-INSURANCE-COMPAN-105516292/",
        "SBIN" : "/quote/stock/STATE-BANK-OF-INDIA-18603402/",
        "SUNPHARMA" : "/quote/stock/SUN-PHARMACEUTICAL-INDUST-9058928/",
        "TCS" : "/quote/stock/TATA-CONSULTANCY-SERVICES-9743454/",
        "TATACONSUM" : "/quote/stock/TATA-CONSUMER-PRODUCTS-LI-9058838/",
        "TECHM" : "/quote/stock/TECH-MAHINDRA-LIMITED-33647041/",
        "ULTRACEMCO" : "/quote/stock/ULTRATECH-CEMENT-LIMITED-9059270/",
        "ADANIENSOL" : "/quote/stock/ADANI-ENERGY-SOLUTIONS-LI-23437234/",
        "ADANIGREEN" : "/quote/stock/ADANI-GREEN-ENERGY-LIMITE-46901469/",
        "ADANIPOWER" : "/quote/stock/ADANI-POWER-LIMITED-9059969/",
        "DMART" : "/quote/stock/AVENUE-SUPERMARTS-LIMITED-34491272/",
        "BANKBARODA" : "/quote/stock/BANK-OF-BARODA-23320361/",
        "BPCL" : "/quote/stock/BHARAT-PETROLEUM-CORPORAT-9743071/",
        "BRITANNIA" : "/quote/stock/BRITANNIA-INDUSTRIES-LIMI-105516157/",
        "CGPOWER" : "/quote/stock/CG-POWER-AND-INDUSTRIAL-S-9058926/",
        "CANBK" : "/quote/stock/CANARA-BANK-9059113/",
        "DLF" : "/quote/stock/DLF-LIMITED-9743639/",
        "DIVISLAB" : "/quote/stock/DIVI-S-LABORATORIES-LIMIT-9059190/",
        "GAIL" : "/quote/stock/GAIL-INDIA-LIMITED-9743098/",
        "GODREJCP" : "/quote/stock/GODREJ-CONSUMER-PRODUCTS--9059191/",
        "HDFCAMC" : "/quote/stock/HDFC-ASSET-MANAGEMENT-COM-45228895/",
        "HAL" : "/quote/stock/HINDUSTAN-AERONAUTICS-LIM-47006646/",
        "HYUNDAI" : "/quote/stock/HYUNDAI-MOTOR-INDIA-LIMIT-176859164/",
        "IOC" : "/quote/stock/INDIAN-OIL-CORPORATION-LI-9743425/",
        "IRFC" : "/quote/stock/INDIAN-RAILWAY-FINANCE-CO-119082036/",
        "JINDALSTEL" : "/quote/stock/JINDAL-STEEL-POWER-LIMITE-9059230/",
        "LTM" : "/quote/stock/LTIMINDTREE-LIMITED-31496899/",
        "LODHA" : "/quote/stock/LODHA-DEVELOPERS-LIMITED-121553374/",
        "MAZDOCK" : "/quote/stock/MAZAGON-DOCK-SHIPBUILDERS-113582671/",
        "MUTHOOTFIN" : "/quote/stock/MUTHOOT-FINANCE-LIMITED-9743895/",
        "PIDILITIND" : "/quote/stock/PIDILITE-INDUSTRIES-LIMIT-9058912/",
        "PFC" : "/quote/stock/POWER-FINANCE-CORPORATION-9059675/",
        "PNB" : "/quote/stock/PUNJAB-NATIONAL-BANK-19165555/",
        "RECLTD" : "/quote/stock/REC-LIMITED-9059899/",
        "SHREECEM" : "/quote/stock/SHREE-CEMENT-LIMITED-9059180/",
        "SIEMENS" : "/quote/stock/SIEMENS-LIMITED-9058964/",
        "SOLARINDS" : "/quote/stock/SOLAR-INDUSTRIES-INDIA-LI-29752167/",
        "UNIONBANK" : "/quote/stock/UNION-BANK-OF-INDIA-9058857/",
        "UNITDSPR" : "/quote/stock/UNITED-SPIRITS-LIMITED-45456076/",
        "VBL" : "/quote/stock/VARUN-BEVERAGES-LIMITED-34067670/",
        "VEDL" : "/quote/stock/VEDANTA-LIMITED-37569657/",
        "ZYDUSLIFE" : "/quote/stock/ZYDUS-LIFESCIENCES-LIMITE-34067618/",
        "DRREDDY" : "/quote/stock/DR-REDDY-S-LABORATORIES-L-9058869/",
        "TMPV" : "/quote/stock/TATA-MOTORS-LIMITED-9058835/",
        "TATASTEEL" : "/quote/stock/TATA-STEEL-LIMITED-6491942/",
        "TITAN" : "/quote/stock/TITAN-COMPANY-LIMITED-9059025/",
        "TRENT" : "/quote/stock/TRENT-LIMITED-31311737/",
        "WIPRO" : "/quote/stock/WIPRO-LIMITED-9059079/",
        "ABB" : "/quote/stock/ABB-LTD-9365000/",
        "AMBUJACEM" : "/quote/stock/AMBUJA-CEMENTS-6491917/",
        "BAJAJHLDNG" : "/quote/stock/BAJAJ-HOLDINGS-INVESTMENT-9058815/",
        "BOSCHLTD" : "/quote/stock/BOSCH-LIMITED-9058976/",
        "CHOLAFIN" : "/quote/stock/CHOLAMANDALAM-INVESTMENT--6498532/",
        "CUMMINSIND" : "/quote/stock/CUMMINS-INDIA-LIMITED-6493116/",
        "HINDZINC" : "/quote/stock/HINDUSTAN-ZINC-LIMITED-9058942/",
        "INDHOTEL" : "/quote/stock/THE-INDIAN-HOTELS-COMPANY-9058952/",
        "MOTHERSON" : "/quote/stock/SAMVARDHANA-MOTHERSON-INT-9059209/",
        "TVSMOTOR" : "/quote/stock/TVS-MOTOR-COMPANY-LIMITED-9059148/",
        "TATAPOWER" : "/quote/stock/TATA-POWER-COMPANY-LIMITE-9062790/",
        "TORNTPHARM" : "/quote/stock/TORRENT-PHARMACEUTICALS-L-9058968/",
        "BEL" : "/quote/stock/BHARAT-ELECTRONICS-LIMITE-34491260/",
        "BHARTIARTL" : "/quote/stock/BHARTI-AIRTEL-LIMITED-9059084/",
        "EICHERMOT" : "/quote/stock/EICHER-MOTORS-LIMITED-9058962/",
        "HINDALCO" : "/quote/stock/HINDALCO-INDUSTRIES-LIMIT-6493281/",
        "JSWSTEEL" : "/quote/stock/JSW-STEEL-LIMITED-33647024/",
        "KOTAKBANK" : "/quote/stock/KOTAK-MAHINDRA-BANK-LIMIT-46728631/",
        "LT" : "/quote/stock/LARSEN-TOUBRO-LIMITED-9058829/",
        "MAXHEALTH" : "/quote/stock/MAX-HEALTHCARE-INSTITUTE--111315625/",
        "NESTLEIND" : "/quote/stock/NESTLE-INDIA-LIMITED-9058921/",
        "SHRIRAMFIN" : "/quote/stock/DR-REDDY-S-LABORATORIES-L-9058869/"
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
            if self.nse_code in self.slugs:
                return self.slugs[self.nse_code]
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
                  self.slugs[self.nse_code] = row.get('data-href')
                  return self.slugs[self.nse_code]

            print(f"ERROR ! SLUG NOT FOUND FOR {self.nse_code}")
            return self.slugs['AXISBANK']

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
# BOUNDS + META
# ----------------------------
def get_bounds_and_info(symbol, company_name, industry):
    # try:
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
# POP Calculator
# ----------------------------
def get_pop(stock_price, option_type, strike_price, premium, lot_size, volatility, start_date, target_date, action='sell', interest_rate=0):
  # print(stock_price, option_type, strike_price, premium, lot_size, volatility, start_date, target_date)
  # print(max(1, stock_price-10000), min(100000, stock_price+100000))
  return run_strategy(
      {
          "stock_price": stock_price,
          "start_date": start_date,
          "target_date": target_date,
          "volatility": volatility,
          "interest_rate": interest_rate,
          "strategy": [{
                "type": 'call' if option_type == 'CE' else 'put',
                "strike": strike_price,
                "premium": premium,
                "n": lot_size,
                "action": action,
            }],
          "min_stock": max(1, stock_price-10000),
          "max_stock": min(100000, stock_price+100000)
      }
  ).probability_of_profit

# ----------------------------
# MARGIN CALCULATION
# ----------------------------
def get_margin_req(symbol, strike_price, expiry_date, option_type, lot_size):
    strike_price = int(strike_price)
    lot_size = int(lot_size)

    # Fix: format should be YY+MMM (e.g., "26JUN"), not DD+MMM
    dt = datetime.datetime.strptime(expiry_date, "%d-%m-%Y")
    expiry_formatted = dt.strftime("%y%b").upper()  # "26JUN"

    option_type = option_type.upper()
    post_url = "https://zerodha.com/margin-calculator/SPAN/"

    if math.ceil(strike_price) == math.floor(strike_price):
        strike_price_str = str(int(strike_price))
    else:
        strike_price_str = str(strike_price)

    payload = {
        "action": "calculate",
        "exchange[]": "NFO",
        "product[]": "OPT",
        "scrip[]": f"{symbol}{expiry_formatted}",  # e.g., "ADANIENT26JUN"
        "option_type[]": option_type,
        "strike_price[]": strike_price_str,
        "qty[]": str(lot_size),
        "trade[]": "sell"
    }

    headers = {
        "Referer": "https://zerodha.com/margin-calculator/SPAN/",
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    # print("Payload:", payload)
    response = requests.post(post_url, data=payload, headers=headers)
    # print("Response:", response.json())

    data = response.json()
    total = max(
        data.get('last', {}).get('total', -1),
        data.get('total', {}).get('total', -1)
    )
    return total


# ----------------------------
# FILTERING FUNCTION
# ----------------------------
def filter(df):
  filter = (df['Sell Put @'] < df['Lower Bound']) & \
       (df['Upper Bound'] < df['Sell Call @']) & \
       ((df['POP (%)'] > 90) | (df['POP (%)'] < 10)) & \
       (df['Upcoming Events'] == 'No upcoming events found.') & \
       ((df['Days to Result'] > 30) | (df['Days to Result'] is pd.NA) | (df['Days to Result'] is None) | (df['Days to Result'].isna()) | (df['Days to Result'] == '') | (df['Days to Result']<0))

  df = df[filter]
  return df.copy()


# ----------------------------
# MAIN FUNCTION
# ----------------------------
def generate_short_strangle_csv():

    # Fetch result calendar once
    result_calendar = build_results_calendar_map()

    stock_universe = pd.concat([
        capital_market.nifty50_equity_list(),
        capital_market.niftynext50_equity_list()
    ])

    results = []

    for idx, row in stock_universe.iterrows():

        SYMBOL = row['Symbol']
        if 'adani' in SYMBOL.lower():
            print(f"{SYMBOL} is a Adani item, thus skipping...")
            
        company_name = row['Company Name']
        industry = row['Industry']

        nifty_50_symbols = [
            'ADANIENT','ADANIPORTS','APOLLOHOSP','ASIANPAINT','AXISBANK','BAJAJ-AUTO','BAJFINANCE','BAJAJFINSV','BEL','BHARTIARTL','CIPLA','COALINDIA','DRREDDY','EICHERMOT','ETERNAL','GRASIM','HCLTECH','HDFCBANK','HDFCLIFE','HINDALCO','HINDUNILVR','ICICIBANK','ITC','INFY','INDIGO','JSWSTEEL','JIOFIN','KOTAKBANK','LT','M&M','MARUTI','MAXHEALTH','NTPC','NESTLEIND','ONGC','POWERGRID','RELIANCE','SBILIFE','SHRIRAMFIN','SBIN','SUNPHARMA','TCS','TATACONSUM','TMPV','TATASTEEL','TECHM','TITAN','TRENT','ULTRACEMCO','WIPRO'
        ]

        nifty_next_50_symbols = [
            'ABB', 'ADANIENSOL', 'ADANIGREEN', 'ADANIPOWER', 'AMBUJACEM', 'DMART', 'BAJAJHLDNG', 'BANKBARODA', 'BPCL', 'BOSCHLTD', 'BRITANNIA', 'CGPOWER', 'CANBK', 'CHOLAFIN', 'CUMMINSIND', 'DLF', 'DIVISLAB', 'GAIL', 'GODREJCP', 'HDFCAMC', 'HAL', 'HINDZINC', 'HYUNDAI', 'INDHOTEL', 'IOC', 'IRFC', 'JINDALSTEL', 'LTM', 'LODHA', 'MAZDOCK', 'MUTHOOTFIN', 'PIDILITIND', 'PFC', 'PNB', 'RECLTD', 'MOTHERSON', 'SHREECEM', 'SIEMENS', 'SOLARINDS', 'TVSMOTOR', 'TATAPOWER', 'TORNTPHARM', 'UNIONBANK', 'UNITDSPR', 'VBL', 'VEDL', 'ZYDUSLIFE'
        ]

        if SYMBOL not in nifty_50_symbols and SYMBOL not in nifty_next_50_symbols:
            continue

        if True:
            print(f"Processing {SYMBOL}...")

            print(f"\tStep 1: Get Futures Price")
            FUTURES_PRICE = yf.Ticker(SYMBOL + '.NS').info.get('regularMarketPrice')
            if FUTURES_PRICE is None:
                continue

            print(f"\tStep 2: Get Lot size")
            LOT_SIZE = get_lot_size(SYMBOL)
            if LOT_SIZE is None:
                continue

            print(f"\tStep 3: Get Live Option Chain Data (with Retries)")
            
            # --- RETRY LOGIC FOR NSE LIVE OPTION CHAIN ---
            df = None
            max_retries = 5
            for attempt in range(max_retries):
                try:
                    df = derivatives.nse_live_option_chain(symbol=SYMBOL, expiry_date=EXPIRY)
                    if df is not None and not df.empty:
                        break # Success!
                except Exception as e:
                    print(f"\t\tAttempt {attempt + 1} failed for {SYMBOL}: {e}")
                    if attempt < max_retries - 1:
                        time.sleep(2) # Wait 2 seconds before retrying
                    else:
                        print(f"\t\tFailed to fetch option chain for {SYMBOL} after {max_retries} attempts.")
            
            if df is None or df.empty:
                continue
            # ---------------------------------------------

            df['CALLS_IV'] = df['CALLS_IV'] / 100
            df['PUTS_IV'] = df['PUTS_IV'] / 100

            df = df[(df['CALLS_LTP'] > 0) | (df['PUTS_LTP'] > 0)]

            if len(df) == 0:
                continue

            START_DATE = datetime.date.today().isoformat()
            TARGET_DATE = "-".join(EXPIRY.split("-")[::-1])

            print(f"\tStep 4: Get bounds and info")
            lb, current_price, ub, cname, ind = get_bounds_and_info(
                SYMBOL, company_name, industry
            )

            result_date = result_calendar.get(SYMBOL, None)
            days_to_result = (
                (pd.to_datetime(result_date) - pd.Timestamp.today()).days
                if result_date else None
            )

            try:
              days_to_result_int = int(days_to_result)
              if 0 < days_to_result_int < 30: 
                continue
            except:
              pass

            print(f"\tStep 5: Get Event Calendar and Stock News")
            scraper = MarketScreenerScraper(SYMBOL)
            event_calendar_and_news = scraper.get_event_calendar_and_news()

            print(f"\tStep 6: Compute the margin, pop")
            for _, row in df.iterrows():
                skip_call = False
                skip_put = False
                strike_price = row['Strike_Price']

                if FUTURES_PRICE * 0.90 < strike_price < FUTURES_PRICE * 1.10:
                  continue

                # call_premium = (row['CALLS_Ask_Price'] - row['CALLS_Bid_Price']) * 0.01 + row['CALLS_Ask_Price']
                # put_premium  = (row['PUTS_Ask_Price'] - row['PUTS_Bid_Price']) * 0.01 + row['PUTS_Ask_Price']

                call_premium = row['CALLS_Ask_Price']
                put_premium  = row['PUTS_Ask_Price']

                if call_premium <= 0: skip_call = True
                if put_premium <= 0: skip_put = True

                sigma_call = row['CALLS_IV']
                sigma_put  = row['PUTS_IV']

                if sigma_call == 0: skip_call = True
                if sigma_put == 0: skip_put = True

                if not skip_call:
                  call_POP = get_pop(FUTURES_PRICE, 'CE', strike_price, call_premium, LOT_SIZE, sigma_call, START_DATE, TARGET_DATE) * 100
                  if call_POP < 90: skip_call = True
                
                if not skip_put:
                  put_POP  = get_pop(FUTURES_PRICE, 'PE', strike_price, put_premium,  LOT_SIZE, sigma_put, START_DATE, TARGET_DATE) * 100
                  if put_POP < 90: skip_put = True

                try:
                  if not skip_call:
                    call_margin = get_margin_req(SYMBOL, strike_price, EXPIRY, 'CE', LOT_SIZE)
                except:
                  skip_call = True

                try:
                  if not skip_put:
                    put_margin  = get_margin_req(SYMBOL, strike_price, EXPIRY, 'PE', LOT_SIZE)
                except:
                  skip_put = True

                if not skip_call: 
                    call_profit = call_premium * LOT_SIZE
                    call_profit_pct = call_profit / call_margin * 100
                    if (strike_price > FUTURES_PRICE) and (call_POP >= 90):
                        results.append({
                            "Symbol": SYMBOL, "Company Name": cname, "Industry": ind,
                            "Current Price": FUTURES_PRICE, "Bound": ub, "Result Date": result_date,
                            "Days to Result": days_to_result, "Trade Type": "CE", "Sell @": strike_price,
                            "Sell Premium": round(call_premium, 2), "Max Profit (₹)": int(call_profit),
                            "Max Profit (%)": round(call_profit_pct, 2), "POP (%)": round(call_POP, 2),
                            "Margin": call_margin, "Upcoming Events": event_calendar_and_news['upcoming-events'],
                            "Past Events": event_calendar_and_news['past-events'], "News": event_calendar_and_news['news']
                        })

                if not skip_put: 
                    put_profit  = put_premium * LOT_SIZE
                    put_profit_pct  = put_profit / put_margin * 100
                    if (strike_price < FUTURES_PRICE) and (put_POP >= 90):
                        results.append({
                            "Symbol": SYMBOL, "Company Name": cname, "Industry": ind,
                            "Current Price": FUTURES_PRICE, "Bound": lb, "Result Date": result_date,
                            "Days to Result": days_to_result, "Trade Type": "PE", "Sell @": strike_price,
                            "Sell Premium": round(put_premium, 2), "Max Profit (₹)": int(put_profit),
                            "Max Profit (%)": round(put_profit_pct, 2), "POP (%)": round(put_POP, 2),
                            "Margin": put_margin, "Upcoming Events": event_calendar_and_news['upcoming-events'],
                            "Past Events": event_calendar_and_news['past-events'], "News": event_calendar_and_news['news']
                        })

        else:
            print(f"Skipping {SYMBOL}")
            continue

    result_df = pd.DataFrame(results)
    if not result_df.empty:
        result_df = result_df.sort_values(by="Max Profit (₹)", ascending=False)
    
    os.makedirs(os.path.join('data'), exist_ok=True)
    filename = f"short_strangle_pro_{datetime.datetime.now().strftime('%Y-%m-%d-%H-%M')}.csv"
    result_df.to_csv(os.path.join('data', filename), index=False)

    print(f"\nCSV Generated: {filename}")
    print(result_df.head())

    return result_df

# ----------------------------
# RUN
# ----------------------------
if __name__ == "__main__":
    res_df = generate_short_strangle_csv()

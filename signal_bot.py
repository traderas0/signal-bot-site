import pandas as pd
import requests
import json
import pytz
from datetime import datetime
import os

API_KEY = "b3d6542f78a841d28fc16bcc30629842"
PKT = pytz.timezone("Asia/Karachi")
USERS_FILE = os.path.join(os.path.dirname(__file__), 'users.json')

def is_user_verified(trader_id):
    try:
        with open(USERS_FILE, 'r') as f:
            users = json.load(f)
        return trader_id in users and users[trader_id]['status'] == 'verified'
    except:
        return False

def fetch_candles(symbol, interval="1min", limit=50):
    url = f"https://api.twelvedata.com/time_series"
    params = {"symbol": symbol, "interval": interval, "outputsize": limit, "apikey": API_KEY}
    try:
        response = requests.get(url, params=params).json()
        if "values" in response:
            df = pd.DataFrame(response["values"])
            df["datetime"] = pd.to_datetime(df["datetime"])
            df = df.sort_values("datetime")
            df[["open", "high", "low", "close"]] = df[["open", "high", "low", "close"]].astype(float)
            return df.reset_index(drop=True)
        return None
    except:
        return None

def calculate_ema(df, period=21):
    return df["close"].ewm(span=period, adjust=False).mean()

def detect_order_block_zone(df):
    zones = []
    for i in range(2, len(df) - 3):
        c = df.iloc[i]
        body = abs(c["close"] - c["open"])
        wick = abs(c["high"] - c["low"])
        if wick == 0 or body / wick > 0.5:
            zones.append({
                "index": i,
                "type": "bearish" if c["close"] < c["open"] else "bullish",
                "zone_high": max(c["open"], c["close"]),
                "zone_low": min(c["open"], c["close"])
            })
    return zones[-3:]

def is_rejection(candle, zone):
    wick = candle["high"] - candle["low"]
    body = abs(candle["close"] - candle["open"])
    if wick == 0 or body / wick > 0.6:
        return False
    return zone["zone_low"] <= candle["low"] <= zone["zone_high"] or zone["zone_low"] <= candle["high"] <= zone["zone_high"]

def is_multiple_rejection(df, zone, count=3):
    return sum(is_rejection(df.iloc[i], zone) for i in range(-count-1, -1)) >= count

def analyze_pair(pair):
    df = fetch_candles(pair)
    if df is None or len(df) < 22:
        return None
    df["EMA21"] = calculate_ema(df)
    last = df.iloc[-2]
    trend = "up" if last["close"] > df["EMA21"].iloc[-2] else "down"
    ob_zones = detect_order_block_zone(df)
    for zone in ob_zones:
        if is_multiple_rejection(df, zone):
            now = datetime.now(PKT).strftime("%H:%M:%S")
            if zone["type"] == "bearish" and last["close"] < last["open"] and trend == "down":
                return {"pair": pair, "action": "PUT", "time": now}
            elif zone["type"] == "bullish" and last["close"] > last["open"] and trend == "up":
                return {"pair": pair, "action": "CALL", "time": now}
    return None

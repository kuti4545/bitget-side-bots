"""Bitget public API + Telegram + state."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pandas as pd
import requests

import config

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "bitget-side-bots/1.0"})
TR_TZ = timezone(timedelta(hours=3))

GRAN_MS = {
    "15m": 15 * 60 * 1000,
    "1H": 60 * 60 * 1000,
    "4H": 4 * 60 * 60 * 1000,
}


def now_tr() -> str:
    return datetime.now(TR_TZ).strftime("%Y-%m-%d %H:%M TR")


def get_tickers() -> list[dict]:
    url = f"{config.BITGET_BASE}/api/v2/mix/market/tickers"
    r = SESSION.get(url, params={"productType": config.PRODUCT_TYPE}, timeout=20)
    r.raise_for_status()
    body = r.json()
    if body.get("code") != "00000":
        raise RuntimeError(body)
    return body.get("data") or []


def ticker_map() -> dict[str, dict]:
    return {row.get("symbol"): row for row in get_tickers()}


def get_candles(symbol: str, granularity: str, limit: int = 80, closed_only: bool = False) -> pd.DataFrame | None:
    url = f"{config.BITGET_BASE}/api/v2/mix/market/candles"
    params = {
        "symbol": symbol,
        "granularity": granularity,
        "limit": str(limit),
        "productType": config.PRODUCT_TYPE,
    }
    try:
        r = SESSION.get(url, params=params, timeout=15)
        r.raise_for_status()
        body = r.json()
        if body.get("code") != "00000":
            return None
        raw = body.get("data") or []
        if len(raw) < 30:
            return None
        df = pd.DataFrame(raw, columns=["ts", "open", "high", "low", "close", "base_vol", "quote_vol"])
        for col in ["open", "high", "low", "close", "base_vol", "quote_vol"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df["ts"] = pd.to_numeric(df["ts"], errors="coerce")
        df = df.dropna().sort_values("ts").reset_index(drop=True)
        df["volume"] = df["base_vol"]
        if closed_only:
            width = GRAN_MS.get(granularity)
            if width and not df.empty:
                last_open = int(df["ts"].iloc[-1])
                now_ms = int(time.time() * 1000)
                if now_ms < last_open + width - 8000:
                    df = df.iloc[:-1].reset_index(drop=True)
        if len(df) < 30:
            return None
        return df
    except requests.RequestException:
        return None


def funding_rate(symbol: str) -> dict | None:
    url = f"{config.BITGET_BASE}/api/v2/mix/market/current-fund-rate"
    try:
        r = SESSION.get(
            url,
            params={"symbol": symbol, "productType": config.PRODUCT_TYPE},
            timeout=12,
        )
        r.raise_for_status()
        body = r.json()
        rows = body.get("data") or []
        return rows[0] if rows else None
    except requests.RequestException:
        return None


def open_interest(symbol: str) -> float | None:
    url = f"{config.BITGET_BASE}/api/v2/mix/market/open-interest"
    try:
        r = SESSION.get(
            url,
            params={"symbol": symbol, "productType": config.PRODUCT_TYPE},
            timeout=12,
        )
        r.raise_for_status()
        body = r.json()
        data = body.get("data") or {}
        rows = data.get("openInterestList") or []
        if not rows:
            return None
        return float(rows[0].get("size") or 0)
    except (requests.RequestException, TypeError, ValueError):
        return None


def ema(series: pd.Series, n: int) -> pd.Series:
    return series.ewm(span=n, adjust=False).mean()


def rsi(close: pd.Series, n: int = 14) -> pd.Series:
    delta = close.diff()
    up = delta.clip(lower=0)
    down = -delta.clip(upper=0)
    au = up.ewm(alpha=1 / n, min_periods=n, adjust=False).mean()
    ad = down.ewm(alpha=1 / n, min_periods=n, adjust=False).mean()
    rs = au / ad.replace(0, float("nan"))
    return 100 - (100 / (1 + rs))


def atr(df: pd.DataFrame, n: int = 14) -> float:
    high, low, close = df["high"], df["low"], df["close"]
    prev = close.shift(1)
    tr = pd.concat([(high - low), (high - prev).abs(), (low - prev).abs()], axis=1).max(axis=1)
    val = float(tr.ewm(alpha=1 / n, adjust=False).mean().iloc[-1])
    return val if val == val else float(close.iloc[-1]) * 0.01


def htf_trend(df: pd.DataFrame | None) -> str:
    if df is None or len(df) < 55:
        return "YOK"
    e20 = ema(df["close"], 20)
    e50 = ema(df["close"], 50)
    c = float(df["close"].iloc[-1])
    a, b = float(e20.iloc[-1]), float(e50.iloc[-1])
    if c > a > b:
        return "YUKARI"
    if c < a < b:
        return "AŞAĞI"
    if c > a:
        return "ZAYIF YUKARI"
    if c < a:
        return "ZAYIF AŞAĞI"
    return "YATAY"


def px(price: float) -> float:
    p = abs(price)
    if p >= 1000:
        return round(price, 2)
    if p >= 100:
        return round(price, 3)
    if p >= 1:
        return round(price, 4)
    if p >= 0.01:
        return round(price, 6)
    return round(price, 8)


def load_state() -> dict:
    path = Path(config.STATE_PATH)
    if not path.exists():
        return {"cooldowns": {}, "oi": {}}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"cooldowns": {}, "oi": {}}


def save_state(state: dict) -> None:
    path = Path(config.STATE_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def cooldown_ok(state: dict, key: str, minutes: int) -> bool:
    last = (state.get("cooldowns") or {}).get(key)
    if not last:
        return True
    try:
        ts = datetime.fromisoformat(last)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
    except ValueError:
        return True
    return datetime.now(timezone.utc) - ts >= timedelta(minutes=minutes)


def mark(state: dict, key: str) -> None:
    state.setdefault("cooldowns", {})
    state["cooldowns"][key] = datetime.now(timezone.utc).isoformat()


def send_telegram(text: str) -> bool:
    token = config.TELEGRAM_BOT_TOKEN
    chat = config.TELEGRAM_CHAT_ID
    if not token or not chat:
        print("Telegram yok:\n", text)
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    try:
        r = SESSION.post(url, json=payload, timeout=20)
        if r.status_code != 200:
            print("Telegram hata:", r.text[:300])
            return False
        return True
    except requests.RequestException as exc:
        print("Telegram exception:", exc)
        return False

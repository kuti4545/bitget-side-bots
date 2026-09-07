"""BTC-only: 4H yon + 15m geri cekilme. Alt yok."""

from __future__ import annotations

import config
from bitget import atr, get_candles, htf_trend, now_tr, px, rsi


def run() -> dict | None:
    d15 = get_candles("BTCUSDT", "15m", 80, closed_only=True)
    d1h = get_candles("BTCUSDT", "1H", 80, closed_only=False)
    d4h = get_candles("BTCUSDT", "4H", 80, closed_only=False)
    if d15 is None or d1h is None or d4h is None:
        print("btc pullback: mum yok")
        return None

    t4 = htf_trend(d4h)
    t1 = htf_trend(d1h)
    price = float(d15["close"].iloc[-1])
    r15 = float(rsi(d15["close"]).iloc[-1])
    r1 = float(rsi(d1h["close"]).iloc[-1])
    e20_1h = float(d1h["close"].ewm(span=20, adjust=False).mean().iloc[-1])
    a = atr(d15, 14)
    swing_lo = float(d15["low"].iloc[-16:].min())
    swing_hi = float(d15["high"].iloc[-16:].max())
    last_low = float(d15["low"].iloc[-1])
    last_high = float(d15["high"].iloc[-1])
    last_close = price
    last_open = float(d15["open"].iloc[-1])
    bull = last_close > last_open
    bear = last_close < last_open

    dist_ema = abs(price - e20_1h) / price
    near_ema = dist_ema <= 0.012

    long_ok = (
        t4 == "YUKARI"
        and t1 in ("YUKARI", "ZAYIF YUKARI", "YATAY")
        and r15 <= 38
        and r1 <= 55
        and (near_ema or last_low <= e20_1h * 1.004)
        and bull
    )
    short_ok = (
        t4 == "AŞAĞI"
        and t1 in ("AŞAĞI", "ZAYIF AŞAĞI", "YATAY")
        and r15 >= 62
        and r1 >= 45
        and (near_ema or last_high >= e20_1h * 0.996)
        and bear
    )

    if long_ok == short_ok:
        print("btc pullback: setup yok", t4, t1, "RSI15", round(r15, 1))
        return None

    if long_ok:
        direction = "LONG"
        sl_raw = min(swing_lo, price - 1.2 * a)
        sl = min(sl_raw, price * (1 - config.MIN_SL_PCT))
        risk = price - sl
        tp1 = price + 1.5 * risk
        tp2 = price + 2.5 * risk
        why = "4H yukarı, 15m RSI çekildi, 1H EMA yakını tepki mumu."
    else:
        direction = "SHORT"
        sl_raw = max(swing_hi, price + 1.2 * a)
        sl = max(sl_raw, price * (1 + config.MIN_SL_PCT))
        risk = sl - price
        tp1 = price - 1.5 * risk
        tp2 = price - 2.5 * risk
        why = "4H aşağı, 15m RSI gerildi, 1H EMA yakını red mumu."

    sl_pct = abs(price - sl) / price
    if sl_pct < config.MIN_SL_PCT:
        sl = price * (1 - config.MIN_SL_PCT) if direction == "LONG" else price * (1 + config.MIN_SL_PCT)
        sl_pct = config.MIN_SL_PCT
        risk = abs(price - sl)
        if direction == "LONG":
            tp1, tp2 = price + 1.5 * risk, price + 2.5 * risk
        else:
            tp1, tp2 = price - 1.5 * risk, price - 2.5 * risk

    risk_usd = min(6.0, config.ACCOUNT_EQUITY * 0.015)
    notional = risk_usd / sl_pct
    lev = min(5.0, notional / max(20.0, config.ACCOUNT_EQUITY * 0.08))
    margin = max(20.0, notional / lev)

    return {
        "bot": "BTC_PULLBACK",
        "symbol": "BTCUSDT",
        "direction": direction,
        "price": px(price),
        "sl": px(sl),
        "tp1": px(tp1),
        "tp2": px(tp2),
        "h4": t4,
        "h1": t1,
        "rsi15": round(r15, 1),
        "rsi1h": round(r1, 1),
        "sl_pct": round(sl_pct * 100, 2),
        "margin": round(margin, 2),
        "leverage": round(lev, 1),
        "risk_usd": round(margin * lev * sl_pct, 2),
        "why": why,
        "when": now_tr(),
    }


def format_msg(sig: dict) -> str:
    arrow = "🟢 LONG" if sig["direction"] == "LONG" else "🔴 SHORT"
    return (
        f"{arrow}  <b>BTCUSDT</b>  [PULLBACK]\n"
        f"Bot: BTC-only   {sig['when']}\n"
        f"4H {sig['h4']}  |  1H {sig['h1']}\n"
        f"RSI15 {sig['rsi15']}  RSI1H {sig['rsi1h']}\n"
        f"Fiyat: <b>{sig['price']}</b>\n"
        f"SL: <b>{sig['sl']}</b>  ({sig['sl_pct']}%)\n"
        f"TP1: {sig['tp1']}  |  TP2: {sig['tp2']}\n"
        f"Marj ~${sig['margin']}   {sig['leverage']}x   risk ~${sig['risk_usd']}\n"
        f"{sig['why']}\n"
        f"<i>Alt yok. SL daraltma. Tavsiye değildir.</i>"
    )

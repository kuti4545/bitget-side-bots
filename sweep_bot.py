"""Onceki swing high/low fitille alindi, mum iceri kapandi."""

from __future__ import annotations

import config
from bitget import atr, get_candles, htf_trend, now_tr, px, rsi


def _swing(df, order: int = 3):
    lows, highs = [], []
    lows_i, highs_i = [], []
    n = len(df)
    low = df["low"].to_numpy()
    high = df["high"].to_numpy()
    for i in range(order, n - order - 1):
        w_lo = low[i - order : i + order + 1]
        w_hi = high[i - order : i + order + 1]
        if low[i] <= w_lo.min():
            lows.append(float(low[i]))
            lows_i.append(i)
        if high[i] >= w_hi.max():
            highs.append(float(high[i]))
            highs_i.append(i)
    return lows, highs


def scan_symbol(symbol: str) -> dict | None:
    d15 = get_candles(symbol, "15m", 80, closed_only=True)
    d4h = get_candles(symbol, "4H", 60, closed_only=False)
    if d15 is None or len(d15) < 40:
        return None
    t4 = htf_trend(d4h)
    last = d15.iloc[-1]
    prev = d15.iloc[:-1]
    price = float(last["close"])
    lo = float(last["low"])
    hi = float(last["high"])
    op = float(last["open"])
    r15 = float(rsi(d15["close"]).iloc[-1])
    a = atr(d15, 14)
    rng = hi - lo
    if rng <= 0:
        return None

    lows, highs = _swing(prev.tail(40), 3)
    if not lows or not highs:
        return None
    prior_low = min(lows[-3:]) if len(lows) >= 1 else float(prev["low"].iloc[-20:].min())
    prior_high = max(highs[-3:]) if len(highs) >= 1 else float(prev["high"].iloc[-20:].max())

    lower_wick = min(op, price) - lo
    upper_wick = hi - max(op, price)
    swept_low = lo < prior_low and price > prior_low and lower_wick / rng >= 0.35
    swept_high = hi > prior_high and price < prior_high and upper_wick / rng >= 0.35

    if swept_low and not swept_high and t4 != "AŞAĞI" and r15 <= 45:
        direction = "LONG"
        sl = min(lo, price * (1 - config.MIN_SL_PCT)) - 0.1 * a
        if (price - sl) / price < config.MIN_SL_PCT:
            sl = price * (1 - config.MIN_SL_PCT)
        risk = price - sl
        tp1, tp2 = price + 1.5 * risk, price + 2.5 * risk
        why = f"15m önceki swing low {px(prior_low)} süpürüldü, mum içeri kapandı."
    elif swept_high and not swept_low and t4 != "YUKARI" and r15 >= 55:
        direction = "SHORT"
        sl = max(hi, price * (1 + config.MIN_SL_PCT)) + 0.1 * a
        if (sl - price) / price < config.MIN_SL_PCT:
            sl = price * (1 + config.MIN_SL_PCT)
        risk = sl - price
        tp1, tp2 = price - 1.5 * risk, price - 2.5 * risk
        why = f"15m önceki swing high {px(prior_high)} süpürüldü, mum içeri kapandı."
    else:
        return None

    sl_pct = abs(price - sl) / price
    risk_usd = min(6.0, config.ACCOUNT_EQUITY * 0.015)
    notional = risk_usd / sl_pct
    lev = min(5.0, notional / max(20.0, config.ACCOUNT_EQUITY * 0.07))
    margin = max(18.0, notional / lev)

    return {
        "bot": "SWEEP",
        "symbol": symbol,
        "direction": direction,
        "price": px(price),
        "sl": px(sl),
        "tp1": px(tp1),
        "tp2": px(tp2),
        "h4": t4,
        "rsi15": round(r15, 1),
        "sl_pct": round(sl_pct * 100, 2),
        "margin": round(margin, 2),
        "leverage": round(lev, 1),
        "risk_usd": round(margin * lev * sl_pct, 2),
        "why": why,
        "when": now_tr(),
    }


def run() -> list[dict]:
    found = []
    for symbol in config.SWEEP_SYMBOLS:
        try:
            sig = scan_symbol(symbol)
        except Exception as exc:
            print("sweep hata", symbol, exc)
            continue
        if sig:
            found.append(sig)
    found.sort(key=lambda x: x["sl_pct"], reverse=True)
    return found[: config.SWEEP_MAX_PER_RUN]


def format_msg(sig: dict) -> str:
    arrow = "🟢 LONG" if sig["direction"] == "LONG" else "🔴 SHORT"
    return (
        f"{arrow}  <b>{sig['symbol']}</b>  [SÜPÜRME]\n"
        f"{sig['when']}   4H {sig['h4']}   RSI15 {sig['rsi15']}\n"
        f"Fiyat: <b>{sig['price']}</b>\n"
        f"SL: <b>{sig['sl']}</b>  ({sig['sl_pct']}%)\n"
        f"TP1: {sig['tp1']}  |  TP2: {sig['tp2']}\n"
        f"Marj ~${sig['margin']}   {sig['leverage']}x   risk ~${sig['risk_usd']}\n"
        f"{sig['why']}\n"
        f"<i>Süpürme = stop avı sonrası. Kovalama. Tavsiye değildir.</i>"
    )

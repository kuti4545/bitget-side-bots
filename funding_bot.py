"""Asiri funding + OI degisimi. Kalabalik yonun tersine fikir."""

from __future__ import annotations

import time

import config
from bitget import funding_rate, now_tr, open_interest, px


SKIP = {
    "SPYUSDT", "QQQUSDT", "TSLAUSDT", "NVDAUSDT", "AAPLUSDT",
    "SOXLUSDT", "SOXSUSDT", "MUUSDT", "SKHYUSDT", "SKHYNIXUSDT",
}


def run(tickers: list[dict], state: dict) -> list[dict]:
    ranked = []
    for row in tickers:
        try:
            vol = float(row.get("usdtVolume") or 0)
        except (TypeError, ValueError):
            vol = 0.0
        if vol >= config.FUNDING_MIN_VOLUME:
            ranked.append(row)
    ranked.sort(key=lambda x: float(x.get("usdtVolume") or 0), reverse=True)
    ranked = ranked[: config.FUNDING_MAX_SYMBOLS]

    out = []
    oi_prev = state.setdefault("oi", {})
    for row in ranked:
        symbol = row.get("symbol")
        if not symbol or symbol in SKIP:
            continue
        fr = funding_rate(symbol)
        time.sleep(0.05)
        if not fr:
            continue
        try:
            rate = float(fr.get("fundingRate") or 0)
        except (TypeError, ValueError):
            continue
        if abs(rate) < config.FUNDING_ABS_MIN:
            continue

        oi_now = open_interest(symbol)
        time.sleep(0.05)
        prev = oi_prev.get(symbol)
        oi_chg = None
        if oi_now is not None:
            if prev:
                try:
                    oi_chg = (oi_now / float(prev) - 1) * 100
                except (TypeError, ValueError, ZeroDivisionError):
                    oi_chg = None
            oi_prev[symbol] = oi_now

        try:
            last = float(row.get("lastPr") or 0)
            chg = float(row.get("change24h") or 0) * 100
            high = float(row.get("high24h") or 0)
            low = float(row.get("low24h") or 0)
        except (TypeError, ValueError):
            continue
        if last <= 0:
            continue

        # Pozitif funding = long kalabalik -> short fikir
        if rate > 0:
            direction = "SHORT"
            crowded = "LONG kalabalık (longs pay)"
        else:
            direction = "LONG"
            crowded = "SHORT kalabalık (shorts pay)"

        if direction == "SHORT" and high and (high - last) / high >= 0.12:
            continue
        if direction == "LONG" and low and (last - low) / low >= 0.12:
            continue
        if abs(chg) >= 12:
            continue

        oi_note = "OI ilk kayıt" if oi_chg is None else f"OI {oi_chg:+.2f}%"
        if oi_chg is not None and direction == "SHORT" and oi_chg < -3:
            continue
        if oi_chg is not None and direction == "LONG" and oi_chg < -3:
            continue

        out.append(
            {
                "bot": "FUNDING",
                "symbol": symbol,
                "direction": direction,
                "price": px(last),
                "funding": rate,
                "funding_pct": round(rate * 100, 4),
                "change24h": round(chg, 2),
                "oi_note": oi_note,
                "crowded": crowded,
                "volume": float(row.get("usdtVolume") or 0),
                "when": now_tr(),
            }
        )
    out.sort(key=lambda x: abs(x["funding"]), reverse=True)
    return out[:2]


def format_msg(sig: dict) -> str:
    arrow = "🟢 LONG fikir" if sig["direction"] == "LONG" else "🔴 SHORT fikir"
    vol_m = sig["volume"] / 1_000_000
    return (
        f"{arrow}  <b>{sig['symbol']}</b>  [FUNDING]\n"
        f"{sig['when']}\n"
        f"Funding: <b>{sig['funding_pct']}%</b> / 8s\n"
        f"{sig['crowded']}\n"
        f"{sig['oi_note']}   24s {sig['change24h']:+.2f}%   {vol_m:.1f}M\n"
        f"Fiyat: {sig['price']}\n"
        f"Bu tarayıcı SL üretmez. Kalabalık yönü söyler, entry senin.\n"
        f"<i>Tavsiye değildir. Pompa artığı elendi.</i>"
    )

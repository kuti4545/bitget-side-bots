#!/usr/bin/env python3
"""Uc yan bot: BTC pullback, funding, likidite supurme."""

from __future__ import annotations

import config
from bitget import cooldown_ok, load_state, mark, save_state, send_telegram, ticker_map
from btc_pullback import format_msg as fmt_btc
from btc_pullback import run as run_btc
from funding_bot import format_msg as fmt_fund
from funding_bot import run as run_fund
from sweep_bot import format_msg as fmt_sweep
from sweep_bot import run as run_sweep


def main() -> None:
    state = load_state()
    sent = 0

    if cooldown_ok(state, "btc_pullback", config.PULLBACK_COOLDOWN_MIN):
        sig = run_btc()
        if sig:
            if send_telegram(fmt_btc(sig)):
                mark(state, "btc_pullback")
                mark(state, f"btc_pullback:{sig['direction']}")
                sent += 1
                print("btc", sig["direction"], sig["price"])
        else:
            print("btc: sinyal yok")
    else:
        print("btc: cooldown")

    tickers = list(ticker_map().values())
    if cooldown_ok(state, "funding_batch", 30):
        funds = run_fund(tickers, state)
        mark(state, "funding_batch")
        for sig in funds:
            key = f"funding:{sig['symbol']}:{sig['direction']}"
            if not cooldown_ok(state, key, config.FUNDING_COOLDOWN_MIN):
                print("funding cooldown", sig["symbol"])
                continue
            if send_telegram(fmt_fund(sig)):
                mark(state, key)
                sent += 1
                print("funding", sig["symbol"], sig["funding_pct"])
        if not funds:
            print("funding: asiri oran yok")
    else:
        print("funding: batch cooldown")

    sweeps = run_sweep()
    for sig in sweeps:
        key = f"sweep:{sig['symbol']}:{sig['direction']}"
        if not cooldown_ok(state, key, config.SWEEP_COOLDOWN_MIN):
            print("sweep cooldown", sig["symbol"])
            continue
        if send_telegram(fmt_sweep(sig)):
            mark(state, key)
            sent += 1
            print("sweep", sig["symbol"], sig["direction"])
    if not sweeps:
        print("sweep: setup yok")

    save_state(state)
    print(f"bitti. telegram {sent}")


if __name__ == "__main__":
    main()

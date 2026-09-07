"""Yan botlar — BTC pullback, funding, likidite. Telegram GitHub Secrets."""

import os

BITGET_BASE = "https://api.bitget.com"
PRODUCT_TYPE = "USDT-FUTURES"

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

ACCOUNT_EQUITY = float(os.getenv("ACCOUNT_EQUITY", "300"))
STATE_PATH = os.getenv("STATE_PATH", "docs/side_state.json")

# BTC pullback
PULLBACK_COOLDOWN_MIN = int(os.getenv("PULLBACK_COOLDOWN_MIN", "240"))
MIN_SL_PCT = float(os.getenv("MIN_SL_PCT", "0.015"))

# Funding: 0.0004 = %0.04 / 8s
FUNDING_ABS_MIN = float(os.getenv("FUNDING_ABS_MIN", "0.00035"))
FUNDING_MAX_SYMBOLS = int(os.getenv("FUNDING_MAX_SYMBOLS", "40"))
FUNDING_MIN_VOLUME = float(os.getenv("FUNDING_MIN_VOLUME", "15000000"))
FUNDING_COOLDOWN_MIN = int(os.getenv("FUNDING_COOLDOWN_MIN", "360"))

# Sweep
SWEEP_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
    "DOGEUSDT", "ADAUSDT", "LINKUSDT", "LTCUSDT", "BCHUSDT",
    "AVAXUSDT", "DOTUSDT", "SUIUSDT", "NEARUSDT", "ATOMUSDT",
]
SWEEP_COOLDOWN_MIN = int(os.getenv("SWEEP_COOLDOWN_MIN", "240"))
SWEEP_MAX_PER_RUN = int(os.getenv("SWEEP_MAX_PER_RUN", "2"))

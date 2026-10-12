import os
from datetime import datetime, timedelta

from flask import Flask, jsonify, redirect, request
from kiteconnect import KiteConnect

app = Flask(__name__)

API_KEY = os.environ.get("KITE_API_KEY")
API_SECRET = os.environ.get("KITE_API_SECRET")

kite = None
access_token = None
login_message = "Login required"


def get_kite():
    if not API_KEY:
        raise RuntimeError("KITE_API_KEY is not configured")

    client = KiteConnect(api_key=API_KEY)

    if access_token:
        client.set_access_token(access_token)

    return client


@app.route("/")
def home():
    return jsonify({
        "system": "FAYAZ PRO",
        "status": "Backend running",
        "market_data": (
            "Connected" if access_token else "Login required"
        ),
        "trading_mode": "Paper",
        "login_endpoint": "/login",
        "quote_endpoint": "/api/quote",
        "candles_endpoint": "/api/candles?interval=5minute",
        "orders_enabled": False
    })


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/login")
def login():
    if not API_KEY or not API_SECRET:
        return jsonify({
            "error": "Kite API credentials are not configured"
        }), 500

    client = get_kite()
    return redirect(client.login_url())


@app.route("/callback")
def callback():
    global kite, access_token, login_message

    request_token = request.args.get("request_token")

    if not request_token:
        return jsonify({
            "error": "Missing request_token. Start from /login."
        }), 400

    try:
        client = get_kite()
        session = client.generate_session(
            request_token,
            api_secret=API_SECRET
        )

        access_token = session["access_token"]
        client.set_access_token(access_token)
        kite = client
        login_message = "Login successful"

        return jsonify({
            "status": "Login successful",
            "market_data": "Ready to test",
            "next_step": "/api/quote",
            "orders_enabled": False
        })

    except Exception:
        access_token = None
        kite = None
        login_message = "Login failed"

        return jsonify({
            "error": "Login failed. Check API settings and try /login again."
        }), 400


@app.route("/api/status")
def api_status():
    return jsonify({
        "api_key_configured": bool(API_KEY),
        "access_token_available": bool(access_token),
        "login_status": login_message,
        "orders_enabled": False
    })


@app.route("/api/quote")
def quote():
    if not access_token:
        return jsonify({
            "error": "Login first at /login"
        }), 401

    try:
        data = get_kite().ltp(["NSE:NIFTY 50"])

        return jsonify({
            "symbol": "NIFTY 50",
            "data": data["NSE:NIFTY 50"],
            "orders_enabled": False
        })

    except Exception:
        return jsonify({
            "error": "Could not fetch quote. Check Kite session and API plan."
        }), 502


@app.route("/api/candles")
def candles():
    if not access_token:
        return jsonify({
            "error": "Login first at /login"
        }), 401

    interval = request.args.get("interval", "5minute")

    if interval not in ("5minute", "15minute"):
        return jsonify({
            "error": "Use interval=5minute or interval=15minute"
        }), 400

    try:
        end = datetime.now()
        start = end - timedelta(days=5)

        data = get_kite().historical_data(
            instrument_token=256265,
            from_date=start,
            to_date=end,
            interval=interval
        )

        return jsonify({
            "symbol": "NIFTY 50",
            "interval": interval,
            "count": len(data),
            "candles": data,
            "orders_enabled": False
        })

    except Exception:
        return jsonify({
            "error": "Could not fetch candles. Check Kite session and API plan."
        }), 502


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000))
    )

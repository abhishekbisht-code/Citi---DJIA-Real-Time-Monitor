"""
Citi Internal Tool — DJIA Real-Time Stock Monitor
==================================================
Fetches the Dow Jones Industrial Average (^DJI) from Yahoo Finance
every 5 seconds and stores each reading in a capped queue.

Usage:
    python djia_monitor.py                  # Run live monitor (prints to console)
    python djia_monitor.py --export csv     # Also write readings to djia_log.csv

Requirements:
    pip install yfinance
"""

import time
import queue
import threading
import datetime
import argparse
import csv
import os
import random  # used only for simulation fallback

# ── Try to import yfinance ──────────────────────────────────────────────────
try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    print("[WARNING] yfinance not installed. Run: pip install yfinance")
    print("[WARNING] Falling back to simulated data for demonstration.\n")

# ── Configuration ──────────────────────────────────────────────────────────
TICKER          = "^DJI"          # Yahoo Finance symbol for Dow Jones
POLL_INTERVAL   = 5               # seconds between fetches
QUEUE_MAXSIZE   = 500             # cap: oldest entries dropped when full
DISPLAY_ROWS    = 10              # how many rows to show in the live table

# ── Queue (thread-safe, capped) ────────────────────────────────────────────
# Each item: {"timestamp": datetime, "price": float, "change": float, "pct_change": float}
data_queue = queue.Queue(maxsize=QUEUE_MAXSIZE)

# ── Shared state for display ────────────────────────────────────────────────
_lock           = threading.Lock()
_last_price     = None
_fetch_count    = 0
_error_count    = 0
_running        = True

# ── Simulated base price (fallback only) ───────────────────────────────────
_sim_price      = 42_850.0


def fetch_djia_price() -> float | None:
    """
    Fetch the latest DJIA price from Yahoo Finance.
    Returns the closing/current price as a float, or None on failure.
    """
    if not YFINANCE_AVAILABLE:
        return None

    try:
        ticker = yf.Ticker(TICKER)
        # fast_info is the lightest call — no full history download
        info = ticker.fast_info
        price = info.last_price
        if price and price > 0:
            return float(price)

        # Fallback: grab 1-day 1-minute bars and take the last close
        hist = ticker.history(period="1d", interval="1m")
        if not hist.empty:
            return float(hist["Close"].iloc[-1])

    except Exception as e:
        # Network failure, rate limit, market closed, etc.
        pass

    return None


def simulate_price() -> float:
    """
    Generate a realistic-looking DJIA price tick for demo / offline use.
    Applies a random walk with slight mean-reversion around 42,850.
    """
    global _sim_price
    drift   = (_sim_price - 42_850.0) * -0.01  # gentle mean reversion
    shock   = random.gauss(0, 15)               # ±$15 std dev per tick
    _sim_price = round(_sim_price + drift + shock, 2)
    return _sim_price


def enqueue(price: float, prev_price: float | None):
    """Package a reading and push it onto the queue (drops oldest if full)."""
    now     = datetime.datetime.now()
    change  = round(price - prev_price, 2) if prev_price is not None else 0.0
    pct     = round((change / prev_price) * 100, 4) if prev_price else 0.0

    record = {
        "timestamp":  now,
        "price":      price,
        "change":     change,
        "pct_change": pct,
    }

    if data_queue.full():
        try:
            data_queue.get_nowait()   # discard oldest
        except queue.Empty:
            pass

    data_queue.put_nowait(record)
    return record


def polling_thread(export_csv: bool, csv_path: str):
    """
    Background thread: fetch → enqueue → (optionally) write CSV.
    Runs until _running is set to False.
    """
    global _last_price, _fetch_count, _error_count

    csv_writer = None
    csv_file   = None

    if export_csv:
        csv_file   = open(csv_path, "w", newline="")
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow(["timestamp", "price", "change", "pct_change"])

    try:
        while _running:
            start = time.monotonic()

            # ── Fetch ──
            price = fetch_djia_price()

            if price is None:
                # Use simulation as fallback
                price = simulate_price()
                mode  = "SIM"
            else:
                mode  = "LIVE"

            with _lock:
                record = enqueue(price, _last_price)
                _last_price = price
                _fetch_count += 1
                count = _fetch_count

            # ── CSV export ──
            if csv_writer:
                csv_writer.writerow([
                    record["timestamp"].isoformat(),
                    record["price"],
                    record["change"],
                    record["pct_change"],
                ])
                csv_file.flush()

            # ── Console output ──
            arrow = "▲" if record["change"] >= 0 else "▼"
            clr   = "\033[92m" if record["change"] >= 0 else "\033[91m"
            rst   = "\033[0m"
            ts    = record["timestamp"].strftime("%H:%M:%S")

            print(
                f"[{ts}] [{mode}] #{count:>4}  "
                f"DJIA: {clr}{record['price']:>10,.2f}{rst}  "
                f"{clr}{arrow} {abs(record['change']):>7,.2f} "
                f"({record['pct_change']:+.4f}%){rst}  "
                f"Queue size: {data_queue.qsize()}"
            )

            # ── Sleep for remainder of interval ──
            elapsed = time.monotonic() - start
            sleep   = max(0.0, POLL_INTERVAL - elapsed)
            time.sleep(sleep)

    finally:
        if csv_file:
            csv_file.close()


def get_recent_readings(n: int = 10) -> list[dict]:
    """
    Return the n most recent readings from the queue as a list (non-destructive).
    """
    items = list(data_queue.queue)   # access underlying deque safely
    return items[-n:]


def main():
    global _running

    parser = argparse.ArgumentParser(description="Citi DJIA Real-Time Monitor")
    parser.add_argument(
        "--export", choices=["csv"], default=None,
        help="Also export readings to a CSV file"
    )
    parser.add_argument(
        "--csv-path", default="djia_log.csv",
        help="Path for CSV export (default: djia_log.csv)"
    )
    args = parser.parse_args()

    print("=" * 72)
    print("  Citi Internal Tool — DJIA Real-Time Monitor")
    print(f"  Polling ^DJI every {POLL_INTERVAL}s  |  Queue cap: {QUEUE_MAXSIZE} records")
    if not YFINANCE_AVAILABLE:
        print("  Mode: SIMULATION (install yfinance for live data)")
    else:
        print("  Mode: LIVE  (Yahoo Finance via yfinance)")
    if args.export:
        print(f"  CSV export → {args.csv_path}")
    print("  Press Ctrl+C to stop.")
    print("=" * 72)

    thread = threading.Thread(
        target=polling_thread,
        args=(args.export == "csv", args.csv_path),
        daemon=True
    )
    thread.start()

    try:
        thread.join()
    except KeyboardInterrupt:
        _running = False
        print("\n\n[STOPPED]")
        print(f"Total readings captured: {_fetch_count}")
        print(f"Final queue size:        {data_queue.qsize()}")
        print("\nLast 5 readings:")
        for r in get_recent_readings(5):
            print(f"  {r['timestamp'].strftime('%H:%M:%S')}  ${r['price']:>10,.2f}  "
                  f"({r['pct_change']:+.4f}%)")


if __name__ == "__main__":
    main()


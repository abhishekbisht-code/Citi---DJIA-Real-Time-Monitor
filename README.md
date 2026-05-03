# Citi DJIA Real-Time Stock Monitor 📈

A high-frequency stock monitoring tool that fetches the Dow Jones Industrial Average (^DJI) every 5 seconds. This project features a robust Python backend for data ingestion and a polished HTML5/JS dashboard for real-time visualization.

## 🚀 Key Features

- **Real-Time Polling:** Queries Yahoo Finance every 5 seconds using a background threading architecture.
- **Capped Data Queue:** Implements a thread-safe queue with a 500-record limit to ensure optimal memory management.
- **Simulated Fallback:** Includes a "Smart Simulation" mode that uses a random-walk algorithm if live market data is unreachable or the market is closed.
- **Interactive Dashboard:** A dark-themed UI featuring:
  - Dynamic 60-point sparkline chart.
  - Session high/low tracking.
  - Live data table with directional color indicators (Up/Down).
  - Manual controls to pause the feed or clear the queue.
- **CSV Export:** Optional logging for historical data analysis.

## 🛠️ Tech Stack

- **Backend:** Python 3.x
- **Libraries:** `yfinance` (Live Data), `threading`, `queue`, `argparse`
- **Frontend:** HTML5, CSS3 (Flexbox/Grid), JavaScript (Canvas API)
- **Environment Management:** `uv` (Fast Python package installer)

## 📦 Installation & Setup

### 1. Prerequisites
Ensure you have the `uv` package manager installed for the fastest setup:
```powershell
powershell -ExecutionPolicy Bypass -c 'irm [https://astral.sh/uv/install.ps1](https://astral.sh/uv/install.ps1) | iex'

# Sheratan Service Scripts

## Quick Start

```bash
# Start everything
sheratan start all

# Or start individually
sheratan start chrome      # Chrome with debug port 9222
sheratan start hub         # Core API + Broker + Dispatcher
sheratan start webrelay    # WebRelay worker (auto-starts Chrome)
sheratan start dashboard   # Dashboard UI

# Check health
sheratan health

# Stop all
sheratan stop
```

## Individual Scripts

### START_CHROME.bat
- Starts Chrome with `--remote-debugging-port=9222`
- Uses persistent profile: `data/chrome_profile`
- Opens ChatGPT + Gemini tabs
- **First time:** Log in to both services (session saved)

### START_HUB.bat
- Starts Core API (port 8001)
- Starts Broker (port 9000)
- Dispatcher runs inside Core (no separate process)

### START_WEBRELAY.bat
- Checks if Chrome is running (starts it if needed)
- Waits 5 seconds for Chrome initialization
- Starts WebRelay worker (port 3000)

### START_DASHBOARD.bat
- Starts Dashboard UI (port 3001)
- Auto-installs npm dependencies if needed

## CLI Commands

```bash
sheratan start [service]   # Start chrome|webrelay|hub|dashboard|all
sheratan stop              # Stop all services
sheratan health            # Check which services are running
sheratan status            # Get detailed system status
sheratan logs [file]       # View log files
```

## Service Dependencies

```
Chrome (9222)
  ↓
WebRelay (3000) ──→ Hub (Core 8001 + Broker 9000)
                      ↓
                    Dashboard (3001)
```

## Ports

- **9222** - Chrome Debug Port
- **8001** - Core API
- **9000** - Broker
- **3000** - WebRelay
- **3001** - Dashboard

## First-Time Setup

1. Start Chrome: `sheratan start chrome`
2. **Log in to ChatGPT and Gemini** (one-time, session saved)
3. Start Hub: `sheratan start hub`
4. Start WebRelay: `sheratan start webrelay`
5. Start Dashboard: `sheratan start dashboard`

Or simply: `sheratan start all` (but you still need to log in to ChatGPT/Gemini on first run)

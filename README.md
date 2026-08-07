# OWNd (Fork)

This package is an event listener and command forwarder for the OpenWebNet protocol, tailored for Home Assistant integration.

> **Note on this Fork:** This is a modified fork of the original `OWNd` library by **anotherjulien** (v0.7.48). It includes critical hardening for connection stability, keepalive fixes for MH201 gateways, and updates to comply with modern Home Assistant development standards.

## Key Enhancements in this Fork
- **Connection Hardening:** Reconnection mechanism now handles all connectivity drops (EOF, TCP resets/RST, aborted connections). Modernized `connect()` with strict timeouts to prevent hangs on unreachable hosts.
- **Robust Command Delivery:** `OWNCommandSession.send` rewritten as an iterative loop (3 retries max) instead of recursion, preventing stack overflows on unstable lines.
- **HA Modernization & Security:** Upgraded to target Python 3.14+, replaced `pytz` with native `zoneinfo`, and migrated `xml.dom.minidom` to `defusedxml` to address potential security vectors (Bandit/Ruff clean).
- **Injectable Sessions:** `aiohttp` sessions can now be injected directly from Home Assistant's `config_flow`.

---

## Using OWNd

Clone this repository and then execute:

```bash
cd OWNd
pip3 install .
python3 -m OWNd --help
```

### Auto-Discovery Connection
To automatically discover the first available OpenWebNet gateway via SSDP on your local network:
```bash
python3 -m OWNd
```

### Manual Connection
To skip discovery and force connection to a specific gateway:
```bash
python3 -m OWNd --address <IP_ADDRESS> --port <PORT> --password <PASSWORD> --mac <MAC_ADDRESS>
```
*Note: Gateway configuration parameters can be retrieved using the BTicino Home+Project application.*

## Development checks

The same checks run by GitHub Actions can be executed locally from the repository root:

```bash
ruff check OWNd tests setup.py
mypy OWNd
python -m unittest discover -s tests -v
```

Current development status and pending validation work are tracked in [ROADMAP.md](ROADMAP.md).

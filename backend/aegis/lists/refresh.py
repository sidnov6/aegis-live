"""Nightly refresh of known-illicit address lists (Part 5.1).

Pulls the publicly-maintained OFAC SDN digital-currency address extractions
(refreshed nightly from Treasury's sdn_advanced.xml) plus optional community
sets, and writes them into LISTS_DIR for SanctionsScreen.load().

Network-free fallback: if downloads fail, a bundled seed list (seed_sanctions.json)
guarantees the screening + demo red-bloom still work. Run via GitHub Actions
nightly (see .github/workflows) or `python -m aegis.lists.refresh`.
"""
from __future__ import annotations

import json
import os

import httpx

from ..conf.settings import settings

# Public, nightly-updated OFAC crypto-address extractions.
SOURCES = {
    "ofac_btc": "https://raw.githubusercontent.com/0xB10C/ofac-sanctioned-digital-currency-addresses/lists/sanctioned_addresses_XBT.txt",
    "ofac_eth": "https://raw.githubusercontent.com/0xB10C/ofac-sanctioned-digital-currency-addresses/lists/sanctioned_addresses_ETH.txt",
    "ofac_usdt_trc20": "https://raw.githubusercontent.com/0xB10C/ofac-sanctioned-digital-currency-addresses/lists/sanctioned_addresses_USDT_TRC20.txt",
}


def refresh() -> int:
    os.makedirs(settings.lists_dir, exist_ok=True)
    total = 0
    fetched_any = False
    for name, url in SOURCES.items():
        try:
            r = httpx.get(url, timeout=20, follow_redirects=True)
            r.raise_for_status()
            addrs = [a.strip() for a in r.text.splitlines()
                     if a.strip() and not a.startswith("#")]
            entries = [{"address": a, "source": f"OFAC-SDN ({name})",
                        "entity": "OFAC-sanctioned"} for a in addrs]
            with open(os.path.join(settings.lists_dir, f"{name}.json"), "w") as f:
                json.dump({"addresses": entries}, f)
            total += len(addrs)
            fetched_any = True
            print(f"[{name}] {len(addrs)} addresses")
        except Exception as e:  # noqa: BLE001
            print(f"[{name}] fetch failed: {e}")

    if not fetched_any:
        print("All downloads failed — seed list remains in place.")
    return total


if __name__ == "__main__":
    n = refresh()
    print(f"Total OFAC addresses refreshed: {n}")

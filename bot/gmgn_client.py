#!/usr/bin/env python3
"""
GMGN API wrapper for the memecoin bot.
Provides real-time whale/concentration/rug data via GMGN CLI.
"""

import subprocess
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

GMGN_CLI = "/opt/data/home/.npm-global/bin/gmgn-cli"
CACHE_DIR = Path("/opt/data/hermes_work/wiki/trading/gmgn_cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Cache TTL in seconds
CACHE_TTL = 300  # 5 minutes


def _run_gmgn(args: list, timeout: int = 30) -> Optional[Dict]:
    """Run gmgn-cli and return parsed JSON."""
    try:
        result = subprocess.run(
            [GMGN_CLI] + args + ["--raw"],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode != 0:
            logger.warning(f"gmgn-cli failed: {result.stderr[:200]}")
            return None
        return json.loads(result.stdout)
    except subprocess.TimeoutExpired:
        logger.warning("gmgn-cli timeout")
        return None
    except json.JSONDecodeError as e:
        logger.warning(f"gmgn-cli JSON decode error: {e}")
        return None


def _cache_get(mint: str, endpoint: str) -> Optional[Dict]:
    """Get cached data if fresh."""
    cache_file = CACHE_DIR / f"{mint}_{endpoint}.json"
    if not cache_file.exists():
        return None
    import time
    if time.time() - cache_file.stat().st_mtime > CACHE_TTL:
        return None
    try:
        return json.loads(cache_file.read_text())
    except Exception:
        return None


def _cache_set(mint: str, endpoint: str, data: Dict) -> None:
    """Cache data."""
    cache_file = CACHE_DIR / f"{mint}_{endpoint}.json"
    try:
        cache_file.write_text(json.dumps(data))
    except Exception:
        pass


def get_token_info(mint: str) -> Optional[Dict]:
    """Get full token info from GMGN."""
    cached = _cache_get(mint, "info")
    if cached:
        return cached
    data = _run_gmgn(["token", "info", "--chain", "sol", "--address", mint])
    if data:
        _cache_set(mint, "info", data)
    return data


def get_token_security(mint: str) -> Optional[Dict]:
    """Get security metrics from GMGN."""
    cached = _cache_get(mint, "security")
    if cached:
        return cached
    data = _run_gmgn(["token", "security", "--chain", "sol", "--address", mint])
    if data:
        _cache_set(mint, "security", data)
    return data


def get_token_holders(mint: str, limit: int = 20, tag: Optional[str] = None) -> Optional[Dict]:
    """Get top holders from GMGN."""
    args = ["token", "holders", "--chain", "sol", "--address", mint, "--limit", str(limit)]
    if tag:
        args.extend(["--tag", tag])
    data = _run_gmgn(args)
    return data


def get_token_traders(mint: str, limit: int = 20, tag: Optional[str] = None) -> Optional[Dict]:
    """Get top traders from GMGN."""
    args = ["token", "traders", "--chain", "sol", "--address", mint, "--limit", str(limit)]
    if tag:
        args.extend(["--tag", tag])
    data = _run_gmgn(args)
    return data


def evaluate_fragility(mint: str) -> Dict[str, Any]:
    """
    Evaluate ME2F-style fragility using GMGN data.
    Returns a dict with scores and recommendation.
    """
    info = get_token_info(mint)
    security = get_token_security(mint)

    if not info:
        return {"error": "GMGN info fetch failed", "fragile": True, "score": 1.0}

    # Extract key metrics
    stat = info.get("stat", {})
    dev = info.get("dev", {})
    wallet_tags = info.get("wallet_tags_stat", {})
    price_obj = info.get("price", {})

    top_10_rate = float(stat.get("top_10_holder_rate", 1.0))
    dev_hold_rate = float(stat.get("dev_team_hold_rate", 0))
    creator_status = dev.get("creator_token_status", "creator_close")
    creator_hold_rate = float(stat.get("creator_hold_rate", 0))
    rug_ratio = 0.0  # not in info, check security
    if security:
        rug_ratio = float(security.get("rug_ratio", 0))

    smart_wallets = wallet_tags.get("smart_wallets", 0)
    renowned_wallets = wallet_tags.get("renowned_wallets", 0)
    whale_wallets = wallet_tags.get("whale_wallets", 0)
    sniper_wallets = wallet_tags.get("sniper_wallets", 0)
    rat_trader_wallets = wallet_tags.get("rat_trader_wallets", 0)
    bundler_wallets = wallet_tags.get("bundler_wallets", 0)
    bot_degen_rate = float(stat.get("bot_degen_rate", 0))
    entrapment_rate = float(stat.get("top_entrapment_trader_percentage", 0))
    rat_trader_rate = float(stat.get("top_rat_trader_percentage", 0))
    bundler_rate = float(stat.get("top_bundler_trader_percentage", 0))

    # Compute fragility score (0 = resilient, 1 = extremely fragile)
    # Based on ME2F framework
    score = 0.0
    signals = []

    # WDS component (whale dominance) - weight 0.4
    if top_10_rate > 0.9:
        score += 0.4
        signals.append(f"EXTREME whale concentration: top10={top_10_rate:.1%}")
    elif top_10_rate > 0.7:
        score += 0.3
        signals.append(f"HIGH whale concentration: top10={top_10_rate:.1%}")
    elif top_10_rate > 0.5:
        score += 0.2
        signals.append(f"MEDIUM whale concentration: top10={top_10_rate:.1%}")
    elif top_10_rate > 0.3:
        score += 0.1
        signals.append(f"LOW whale concentration: top10={top_10_rate:.1%}")
    else:
        signals.append(f"RESILIENT whale distribution: top10={top_10_rate:.1%}")

    # Dev behavior - weight 0.2
    if creator_status == "creator_close":
        score += 0.2
        signals.append("DEV EXITED (sold all)")
    elif creator_hold_rate > 0.1:
        score += 0.1
        signals.append(f"DEV HOLDS {creator_hold_rate:.1%}")
    else:
        signals.append("DEV HOLDING (small amount)")

    # Smart money presence - weight 0.15 (negative = good)
    if smart_wallets > 5:
        score -= 0.15
        signals.append(f"SMART MONEY: {smart_wallets} wallets")
    elif smart_wallets > 0:
        score -= 0.1
        signals.append(f"Some smart money: {smart_wallets}")

    # Renowned/KOL presence - weight 0.1
    if renowned_wallets > 10:
        score -= 0.1
        signals.append(f"KOLs PRESENT: {renowned_wallets}")
    elif renowned_wallets > 0:
        score -= 0.05
        signals.append(f"Some KOLs: {renowned_wallets}")

    # Bot/sniper/rat activity - weight 0.15
    if rat_trader_rate > 0.1 or bundler_rate > 0.1 or entrapment_rate > 0.2:
        score += 0.15
        signals.append(f"SUSPICIOUS ACTIVITY: rat={rat_trader_rate:.1%} bundler={bundler_rate:.1%} entrap={entrapment_rate:.1%}")

    # Sniper count - weight 0.1
    if sniper_wallets > 5:
        score += 0.1
        signals.append(f"MANY SNIPERS: {sniper_wallets}")
    elif sniper_wallets > 0:
        score += 0.05
        signals.append(f"Some snipers: {sniper_wallets}")

    # Liquidity check - weight 0.1
    liquidity = float(info.get("liquidity", 0))
    if liquidity < 5000:
        score += 0.1
        signals.append(f"LOW LIQUIDITY: ${liquidity:.0f}")
    elif liquidity < 20000:
        score += 0.05
        signals.append(f"MEDIUM LIQUIDITY: ${liquidity:.0f}")
    else:
        signals.append(f"GOOD LIQUIDITY: ${liquidity:.0f}")

    # Clamp
    score = max(0.0, min(1.0, score))

    # Classification
    if score >= 0.7:
        level = "EXTREME"
        action = "AVOID"
    elif score >= 0.5:
        level = "HIGH"
        action = "REDUCE SIZE"
    elif score >= 0.3:
        level = "MEDIUM"
        action = "STANDARD SIZE"
    else:
        level = "LOW"
        action = "FULL SIZE"

    return {
        "fragile": score >= 0.5,
        "score": round(score, 3),
        "level": level,
        "action": action,
        "signals": signals,
        "raw": {
            "top_10_rate": top_10_rate,
            "creator_status": creator_status,
            "smart_wallets": smart_wallets,
            "renowned_wallets": renowned_wallets,
            "whale_wallets": whale_wallets,
            "sniper_wallets": sniper_wallets,
            "rat_trader_wallets": rat_trader_wallets,
            "bundler_wallets": bundler_wallets,
            "liquidity": liquidity,
            "rug_ratio": rug_ratio,
        },
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python gmgn_client.py <mint>")
        sys.exit(1)

    mint = sys.argv[1]
    result = evaluate_fragility(mint)
    print(json.dumps(result, indent=2))
"""
Decoder for Solana swap transactions.
Handles Jupiter, Raydium, Pump.fun, pump_swap AMM transactions.

Approach: detect transfers of SOL and SPL tokens within the tx,
and infer which tokens were swapped.
"""
import json
import urllib.request
from typing import Optional

# Known program IDs
JUPITER_V6 = "JUP6LkbZbiS2gQt4xfGZGE2xK8KJp8ZJ8ZJ8ZJ8ZJ8ZJ"
RAYDIUM_AMM_V4 = "675kPX9MHTjS1ztvg78csmR64ZHH798gY4T9oTEs8Kv"
PUMPSWAP = "PSwapMdHGfP7Z4F7rjvNxqna37BgZBUdv1FpT26MphMq"
PUMP_FUN = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
TOKEN_PROGRAM = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
SOL_MINT = "So11111111111111111111111111111111111111112"

# Known wallet programs
WSOL_MINT = SOL_MINT


def decode_swap(tx: dict, watched_wallet: str) -> Optional[dict]:
    """Decode a Solana tx into a trade signal if it's a swap.

    Returns dict with: side, sol_amount, token_amount, token_mint, slot, sig
    Returns None if it's not a swap we care about.

    Detection logic:
    - Find watched_wallet in transaction keys
    - Find any SPL token accounts owned by watched_wallet whose balance changed
    - Find any SOL balance change for watched_wallet
    - Pair them up as a swap

    Side heuristic: watched_wallet's SOL went UP = they SOLD tokens
                     watched_wallet's SOL went DOWN = they BOUGHT tokens
    """
    try:
        result = tx.get("result", {})
        if not result:
            return None

        message = result.get("transaction", {}).get("message", {})
        keys = message.get("accountKeys", [])
        meta = result.get("meta", {})

        if watched_wallet not in keys:
            return None

        idx = keys.index(watched_wallet)
        pre_sol = meta.get("preBalances", [0] * len(keys))
        post_sol = meta.get("postBalances", [0] * len(keys))
        sol_change = (post_sol[idx] - pre_sol[idx]) / 1e9  # SOL delta

        # Get SPL token balance changes for watched wallet
        pre_tokens = {t["account"]: t for t in meta.get("preTokenBalances", [])}
        post_tokens = {t["account"]: t for t in meta.get("postTokenBalances", [])}

        token_changes = []
        for acct, post in post_tokens.items():
            if pre_tokens.get(acct, post).get("owner") != watched_wallet:
                continue
            pre_amt = float(pre_tokens[acct].get("uiTokenAmount", {}).get("uiAmount", 0) or 0)
            post_amt = float(post.get("uiTokenAmount", {}).get("uiAmount", 0) or 0)
            mint = post["mint"]
            change = post_amt - pre_amt
            if abs(change) > 0.000001:
                token_changes.append({
                    "mint": mint,
                    "change": change,
                    "pre": pre_amt,
                    "post": post_amt,
                })

        # Filter out WSOL-only changes (wrap/unwrap, not a real swap)
        non_wsol = [t for t in token_changes if t["mint"] != WSOL_MINT]

        if not non_wsol:
            return None  # just SOL transfer or wrap/unwrap

        # Get fee
        fee_sol = meta.get("fee", 0) / 1e9

        # Build swap signal
        # Side by: positive SOL change = sold tokens for SOL (SELL side = took profit)
        # Negative SOL change = bought tokens with SOL (BUY side = entry)
        side = "sell" if sol_change > 0.001 else ("buy" if sol_change < -0.001 else None)
        if side is None:
            return None

        # Primary token = the one with biggest change
        primary = max(non_wsol, key=lambda t: abs(t["change"]))
        token_change = primary["change"]

        # For buy: negative token change = token increased in wallet = direction was BUY
        # For sell: positive token change = token decreased = sell signal? No wait,
        # If we SELL tokens, our token balance DECREASES (negative change).
        # Confusing! Let me re-derive:
        # BUY: spend SOL +0, get token +N. So change = +N (token increased)
        # SELL: get SOL +S, give token -N. So change = -N (token decreased)

        if side == "buy" and token_change < 0:
            # token change should be positive for buy
            return None
        if side == "sell" and token_change > 0:
            return None

        amount_token = abs(token_change)

        return {
            "side": side,
            "sol_amount": abs(sol_change),
            "token_amount": amount_token,
            "token_mint": primary["mint"],
            "fee_sol": fee_sol,
            "sig": result.get("transaction", {}).get("signatures", [""])[0],
            "slot": result.get("slot"),
            "watched_wallet": watched_wallet,
        }
    except Exception as e:
        return None

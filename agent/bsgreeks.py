"""Black-Scholes Greeks closed-form solver (exemplar family).

Covers units whose input table is an options schema (S, K, T, r, sigma,
option_type) and whose deliverable is results.parquet — the exemplar
``t1-EXAMPLE-bs-greeks-pde`` and its public twin. Ported from the official
examples/exemplar_agent/solve.py (transport example), vectorised with numpy.
"""

from __future__ import annotations

import math
import pathlib

import numpy as np
import pandas as pd

REQUIRED_COLUMNS = {"S", "K", "T", "r", "sigma", "option_type"}


def find_options_table(task_dir: pathlib.Path) -> pathlib.Path | None:
    """Locate a parquet input with the options schema, if any."""
    try:
        import pyarrow.parquet as pq
    except ImportError:  # pragma: no cover
        return None
    for path in sorted(task_dir.rglob("*.parquet")):
        try:
            schema = {f.name for f in pq.read_schema(path)}
        except Exception:  # noqa: BLE001 — unreadable candidate, skip
            continue
        if REQUIRED_COLUMNS.issubset(schema):
            return path
    return None


def solve(options_parquet: pathlib.Path, out_dir: pathlib.Path) -> pathlib.Path:
    options = pd.read_parquet(options_parquet)
    spot = options["S"].to_numpy(dtype=float)
    strike = options["K"].to_numpy(dtype=float)
    maturity = options["T"].to_numpy(dtype=float)
    rate = options["r"].to_numpy(dtype=float)
    volatility = options["sigma"].to_numpy(dtype=float)
    option_type = options["option_type"].astype(str).to_numpy()

    erf = np.vectorize(math.erf, otypes=[float])

    def cdf(x: np.ndarray) -> np.ndarray:
        return 0.5 * (1.0 + erf(x / math.sqrt(2.0)))

    sqrt_t = np.sqrt(maturity)
    d1 = (np.log(spot / strike) + (rate + 0.5 * volatility**2) * maturity) / (
        volatility * sqrt_t
    )
    d2 = d1 - volatility * sqrt_t
    discount = np.exp(-rate * maturity)
    density = np.exp(-0.5 * d1**2) / math.sqrt(2.0 * math.pi)
    is_call = option_type == "call"

    cdf_d1, cdf_d2 = cdf(d1), cdf(d2)
    cdf_minus_d1, cdf_minus_d2 = cdf(-d1), cdf(-d2)
    call_price = spot * cdf_d1 - strike * discount * cdf_d2
    put_price = strike * discount * cdf_minus_d2 - spot * cdf_minus_d1
    call_theta = (
        -spot * density * volatility / (2.0 * sqrt_t)
        - rate * strike * discount * cdf_d2
    )
    put_theta = (
        -spot * density * volatility / (2.0 * sqrt_t)
        + rate * strike * discount * cdf_minus_d2
    )

    result = pd.DataFrame(
        {
            "option_id": options["option_id"],
            "price": np.where(is_call, call_price, put_price),
            "delta": np.where(is_call, cdf_d1, cdf_d1 - 1.0),
            "gamma": density / (spot * volatility * sqrt_t),
            "vega": spot * density * sqrt_t,
            "theta": np.where(is_call, call_theta, put_theta) / 365.0,
        }
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / "results.parquet"
    result.to_parquet(target, index=False)
    return target

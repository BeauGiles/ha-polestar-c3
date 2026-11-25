"""Probe the Polestar app's Service Plan / Service Booking GraphQL operations.

See service-plans-and-bookings.md at the repo root for why this script exists.
On an Australian fleet-ordered account these come back empty. We don't yet
know whether that's a fleet-order thing, a country thing, or both — this
script lets someone in a different country or with a different order type
run the same read-only queries and report back what they see.

Nothing is written or changed on your account: every operation here is a
plain GraphQL *query* (no mutations), using the same read-only login this
library already uses for Home Assistant. VINs are stripped from the printed
output; nothing is written to disk.

Usage:
    PS_EMAIL=you@example.com PS_PASS='your password' \\
        uv run --with httpx --with grpclib env PYTHONPATH=src \\
        python scripts/probe_service_plans.py
"""

from __future__ import annotations

import asyncio
import json
import os
import uuid

import httpx

from polestar_api import PolestarApi
from polestar_api import discovery as d

# (operation name, GraphQL query, variables-from-context)
OPS = {
    "ServicePlan": (
        "PolestarServicePlansForVin",
        "query PolestarServicePlansForVin($vin: String!) { servicePlan { getServicePlan(vin: $vin) { "
        "id vin name mileageUnit status productStatus products { id name qw90ClaimType startDate endDate mileage } } } }",
        lambda ctx: {"vin": ctx["vin"]},
    ),
    "ServiceBookings": (
        "ServiceBookingBookings",
        "query ServiceBookingBookings($vin: String!) { serviceBooking { bookings(vin: $vin) { booking { "
        "mileage mileageUnit status timeSlots { start end } dealer { name cityName } } } } }",
        lambda ctx: {"vin": ctx["vin"]},
    ),
    # No VIN needed: this is a market-level feature flag, so it's useful even
    # without a car that has ever had a plan or booking.
    "MarketConfig": (
        "MarketConfiguration",
        "query MarketConfiguration { marketConfigurations { getMarketConfiguration { marketCode "
        "featuresConfiguration { servicesConfiguration { servicePlanEnabled } } "
        "serviceBookingConfiguration { serviceFlow } } } }",
        lambda ctx: {},
    ),
}


def redact(obj, vin: str):
    """Strip the VIN and keep the rest - these queries don't carry other PII,
    except ServiceBookings' dealer name/city if you actually have a booking."""
    if isinstance(obj, dict):
        return {k: redact(v, vin) for k, v in obj.items()}
    if isinstance(obj, list):
        return [redact(x, vin) for x in obj]
    if isinstance(obj, str) and vin and vin in obj:
        return obj.replace(vin, "<vin>")
    return obj


async def gql(client: httpx.AsyncClient, token: str, op: str, query: str, variables: dict) -> dict:
    headers = {
        **d._app_backend_headers(token),
        "X-APOLLO-OPERATION-NAME": op,
        "X-APOLLO-REQUEST-UUID": str(uuid.uuid4()),
        "Accept": d.APP_BACKEND_ACCEPT_HEADER,
        "Content-Type": "application/json",
    }
    response = await client.post(
        d.APP_BACKEND_GRAPHQL_URL,
        headers=headers,
        json={
            "operationName": op,
            "variables": variables,
            "query": query,
            "extensions": {"clientLibrary": d.APP_BACKEND_CLIENT_LIBRARY},
        },
    )
    try:
        body = response.json()
    except ValueError:
        return {"http": response.status_code, "not_json": response.text[:200]}
    out: dict = {"http": response.status_code}
    if body.get("errors"):
        out["errors"] = [e.get("message") for e in body["errors"]][:3]
    if body.get("data") is not None:
        out["data"] = body["data"]
    return out


async def main() -> None:
    email = os.environ["PS_EMAIL"]
    password = os.environ["PS_PASS"]

    results: dict[str, dict] = {}
    async with PolestarApi(email=email, password=password) as api:
        token = await api._auth.ensure_valid_token()
        vehicles = await api.get_vehicles()
        if not vehicles:
            print("No vehicles returned for this account - nothing to probe.")
            return
        vin = vehicles[0].vin
        ctx = {"vin": vin}

        async with httpx.AsyncClient(timeout=30) as client:
            for name, (op, query, make_vars) in OPS.items():
                results[name] = await gql(client, token, op, query, make_vars(ctx))

    red = redact(results, vin)
    print(json.dumps(red, indent=2, ensure_ascii=False))
    print(
        "\nPlease paste the JSON above into a comment on the tracking issue, along with:\n"
        "  - your country\n"
        "  - whether the car is a private purchase, a fleet/company order, or a lease\n"
        "  - your Polestar model and whether it's new or used\n"
    )


if __name__ == "__main__":
    asyncio.run(main())

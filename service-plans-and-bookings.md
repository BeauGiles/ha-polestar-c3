# Service Plan & Service Booking: help us test your country/order type

The Polestar app has GraphQL operations for a vehicle's **service plan** and **service bookings** that this integration doesn't expose as entities, because on the one account it's been tested against, they come back empty. This is a call for people in other countries, or with a different order type, to run the same read-only queries and report back what they see — so we know whether it's worth building entities around this at all, and for whom.

## What we found

Decompiling the Polestar Android app turned up three relevant GraphQL operations on the app-backend (`pc-api.polestar.com`), the same backend and login this integration already uses for vehicle discovery:

- **`PolestarServicePlansForVin`** — a vehicle's service plan: name, status, and the individual products/claims on it (mileage, start/end dates).
- **`ServiceBookingBookings`** — upcoming service appointments: mileage, status, time slots, dealer.
- **`MarketConfiguration`** — not vehicle-specific; a market-level feature-flag query that includes `servicePlanEnabled` and a service-booking `serviceFlow`, so it's useful even for an account whose car has never had a plan or a booking.

## What we know so far

On the one account this has been tested against — a 2026 Polestar 2, **fleet-ordered**, registered in **Australia** — all three come back empty:

- `PolestarServicePlansForVin` returns no plan.
- `ServiceBookingBookings` returns no bookings.
- `MarketConfiguration`'s `servicePlanEnabled`/`serviceFlow` read as not offered for this market.

We don't know whether that's because:
1. the car is a **fleet order** rather than a private purchase/lease, or
2. **Australia** specifically doesn't offer service plans or online booking through the app, or
3. both, or
4. something else entirely (a new/used distinction, a specific model, an account-linking quirk).

We also checked the Volvo side (this project has a sibling, [`ha-volvo-c3`](https://github.com/BeauGiles/ha-volvo-c3)): the equivalent Volvo operations (`VehicleFlags`, `Addons`) belong to the same service-booking feature, and read the same way — not offered for this market. No Volvo probe script was built for it, since there was nothing to test beyond the same country question.

## How to test it

This only runs read-only GraphQL **queries** — no mutations, nothing is changed on your account. It reuses this repo's own login code, the same one the Home Assistant integration uses.

1. Clone this repo (or your own fork) and make sure you can run its test suite (see [`README.md`](README.md#for-developers) under "For developers").
2. Run:
   ```bash
   PS_EMAIL=you@example.com PS_PASS='your password' \
       uv run --with httpx --with grpclib env PYTHONPATH=src \
       python scripts/probe_service_plans.py
   ```
3. It prints a small JSON block with the three operations' results. VINs are stripped automatically before anything is printed; nothing is written to disk.
4. Post what you got as a comment on the tracking issue (or open a new issue if there isn't one yet), along with:
   - your **country**
   - whether the car is a **private purchase, fleet/company order, or lease**
   - your **Polestar model**, and whether it's **new or used**

If you'd rather not run a script at all, just checking whether **Service** shows up as a real feature (with an actual plan, or a working "book a service" flow) in your own Polestar app and telling us your country and order type is still useful data.

## Why this matters for the integration

If `servicePlanEnabled`/bookings turn out to be available for private orders or in other markets, this is a candidate for:
- a **service plan sensor** (status, expiry/mileage limit), and
- a **service booking** sensor or calendar, similar to the existing parking-climate-timer calendars.

Nothing will be built until it's confirmed working for an account type and market combination that would actually show data — building entities around a feature that's permanently empty for most installs isn't worth the maintenance.

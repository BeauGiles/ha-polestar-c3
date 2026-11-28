# Changelog

All notable changes to Polestar C3 (domain `polestar`), the Home Assistant integration in this repository. This integration and [Volvo C3](https://github.com/BeauGiles/ha-volvo-c3) talk to the same Volvo C3 backend and were brought in line with each other on 18 and 19 November 2026, so most entries here have a matching entry in the Volvo changelog.

Dates are 2026.

## Unreleased

### Added

- **Has the car got the change yet?**
  - The Charge timer switch has a `sync_status` attribute: `synced` once the car has the change, or `syncing`, `retrying`, `retrying_car_offline` or `error` while it hasn't. It also shows `updated_at` and, when the backend sends one, `sync_message`, and `changed_by` (`mapp` for the app, or `car`). Until now a pending change looked the same as an applied one.
  - Target SoC and Charge current show `updated_at` (when the backend last changed the setting) and `changed_by`. These settings have no sync status.
  - Climate timers aren't included, because neither car sends a sync status for them.

  Matches Volvo C3.
- **Air purification last cycle has attributes:**
  - `started_at`: when the cycle started.
  - `measured_at`: when the cabin air was last measured.
  - `air_quality_index`: the car's own index, a different value from the PM2.5 that the Air quality sensor shows.
  - `pm2_5`.
  - `last_cycle_valid`.

  Matches Volvo C3.
- **Climate time remaining shows the longest climate run** as `max_runtime_minutes`, from the car record (30 on a Polestar 2). Matches Volvo C3.
- **Vehicle info shows more facts from the car record:**
  - `c3_driver_side`
  - `c3_gross_vehicle_weight_rating` (kg)
  - `c3_supports_pilot_assist`
  - `c3_charging_electric_inlet_dc_location`
  - `c3_parking_climatization_type`, `c3_parking_climatization_heating_type` and `c3_parking_climatization_max_runtime`
- **Charge now.** A binary sensor shows whether charge now is overriding the charge timer, read from the same backend state the app uses. Its attributes say the exact state, including pending, and which charge-now button the app offers (`charge_now`, `resume_schedule` or `not_applicable`). It's refreshed after Start or Stop charging. Matches Volvo C3.
- **Last charging error.** A diagnostic timestamp sensor listens to the backend's error stream, which stays silent until the car can't apply a change to charging or the climate timers. It then shows when that happened, with `setting`, `error` and `action` attributes, for example charge now, `car`, `start_override_charge_timer`. Its state changes, so automations can trigger on it. Matches Volvo C3.
- **The software update shows when the current software was installed.** An `installed_at` attribute comes from a car record field neither app names (92). An XC40 sends it about 47 s after its last OTA install finished. A car that has never had an OTA, such as a Polestar 2 still on its factory software, doesn't send it, so the attribute stays empty until the first OTA. The car record is now re-read every 6 hours and right after an install completes, instead of only at startup.
- **The VIN sensor shows the vehicle type code** from the car record: 534 for a Polestar 2, 536 for an XC40 / EX40.
- **The software update shows its full release notes** under "Release notes", converted from the backend's markup to plain text with the converter Volvo C3 uses. The summary is now only the short description, without the markup.
- **Diagnostics include more of what the backend sends:**
  - The whole car record, with the VIN, PCID, battery pack serial, visual ID and registration redacted.
  - Fields the integration doesn't know yet, as `unknown_<n>` in every reply: for example charging fields 43, 44 and 45 in the car record. New fields now show up in a download before anyone maps them.
  - A few read-only calls the integration doesn't poll, made once when diagnostics are downloaded: car preview, connected services, Plug & Charge on/off, the error stream, charge now and data sharing.
  - The VIN, PCID and registration are also removed from values, not only from known keys.
- **Vehicle info shows whether the car is set up for Plug & Charge.** A new `plug_and_charge_ready` attribute on the Vehicle info sensor comes from the car record: true when the car has a Plug & Charge contract ID. `plug_and_charge_pcid` shows the contract ID, as the Polestar app does. Both are read-only, because Polestar's backend doesn't offer a remote on/off for a Polestar 2. Diagnostics redact the ID.
- **Air purification last cycle.** A diagnostic timestamp sensor shows when the last air purification cycle finished, as Volvo C3 already does. It comes from the pre-cleaning reply the integration already reads.
- **Diagnostics show what the car lets the app set for parking climate.** These are the car record's flags for front seat, rear seat and steering wheel settings, the number of heat levels for each, and the steering wheel level count the select uses. The field numbers come from the Volvo app's proto: 8, 9, 10, 11, 15 and 16. Nothing changes in which entities appear. The Polestar 2 still has no climate seat, steering wheel or temperature settings, which matches the Polestar app, where it can only set these in the car.

### Fixed

- **The alarm sensor now sees a triggered alarm.** The car reports its alarm in a field of the exterior reply that the integration skipped (15), so Alarm triggered could never turn on, even while the app showed the alarm and sent a notification. It now reads that field, and still checks the per-door alarm states as before. Both cars report `IDLE` when parked. Matches Volvo C3.
- **The charge current slider follows the car's own range.** The car record says which currents the car accepts: 6–32 A on an Australian Polestar 2, up to 48 A in North America. The slider was fixed at 6–32 A. The charge location actions now accept up to 80 A and check the value against the car's maximum.
- **Average speed sensors come back.** Polestar removed the dashboard service the average speeds came from (it now answers "Method not found"), so both sensors stayed hidden. The odometer reply carries the same two values (fields 5 and 6), and the sensors now fall back to it.
- **Reading the remote data-sharing setting no longer times out.** It's a stream in the app, but the library read it as a single reply and waited for a close that never comes. It now takes the first message. No entity uses it today; this is the library getter only.
- **Start charging and Stop charging report the car's answer correctly.** The reply carries its status in field 1, but the integration looked for it inside a field-3 envelope, so it read every reply as undefined and the command could show as failed even when the car accepted it. Only SUCCESS now counts as success; a validation, internal or not-found error is reported as a failure. From ericyew ([67952fd](https://github.com/ericyew/unofficial-polestar-api/commit/67952fdf5d5bf453d52fc3a7a992b613c288598b)), originally upstream v0.4.0.
- **The Target SoC slider starts at the car's own minimum.** The car record says the lowest target charge level the car accepts (40 % on a Polestar 2). The slider used to start at 20 %, so values the car would refuse could be picked. When the car doesn't report a minimum, the slider still starts at 20 %.
- **Steering wheel heating options follow what the car reports.** The car record says how many steering wheel heat levels it has (parking climate field 16). When it says one, the select offers only Off and Level 3, on any model. When the car record isn't available, it still falls back to treating a Polestar 4 as on/off. From ericyew ([4d3f4bf](https://github.com/ericyew/unofficial-polestar-api/commit/4d3f4bf1d2f97e2e2e3f16598285de4b9268d683)).

## 0.5.1 (27 November)

### Added

- **Engine coolant low** binary sensor (health field 7), matching Volvo C3. Diagnostic, Problem when the car says the level is too low. Hidden on a car that never reports a coolant level.

### Fixed

- The **Documentation** link on the integration's page in Home Assistant opened a page that does not exist; it now opens this repository.

## 0.5.0 (27 November)

### Added

- **Cold battery** sensor: whether the high-voltage battery is cold, or predicted to be cold, optionally with low charge (battery field 30). Useful for preconditioning in winter. From ericyew ([5ebf781](https://github.com/ericyew/unofficial-polestar-api/commit/5ebf781e15ea2be9229a3f9fee5e4cc9d3fe5158)), found by comparing Polestar app 5.13.0 and 5.15.1. Not yet seen from a real car.
- **Battery thermal event** binary sensor (safety): a high-voltage battery thermal event reported by the car (health field 48). The car leaves the field out when there is no event, so it reads off. Same source; the Volvo app has the same field and a help screen for it. Listed under Diagnostic. Reads Safe on a Polestar 2.
- **Open boot** and **Close boot** buttons for cars with a power tailgate. They use the same command as the Volvo app (`TailgateControl`) and only appear when the car reports power tailgate control (car record, locks field 7); the Polestar 2 reports it. Open and close both work on a Polestar 2 (27 November).
- **Service plan** diagnostic sensor: the car's prepaid service contract as the Polestar app's Service screen shows it. The state is the plan name; attributes give its status, last day, and each product's start, end and mileage limit (for example car wash, scheduled maintenance, pick-up and delivery). It only appears when Polestar returns a plan for the car, read at startup and every 3 days; a plan that appears later shows after a restart. Many accounts get none (an Australian fleet order did not); a UK-market account reported one. Investigation in [#37](https://github.com/BeauGiles/ha-polestar-c3/pull/37).

### Fixed

- **Software update shows the update icon, not the Polestar logo.** Setting no picture was not enough: Home Assistant's update entity falls back to the brand logo, so the entity now overrides the picture outright.
- **Cold battery is hidden on cars that don't report it.** The Polestar 2 leaves the field empty, so the sensor only ever read Unknown. It is now disabled when the car reports nothing for it, and comes back by itself if the car starts sending it (Polestar 3 and 4 are expected to).
- **Clearer idle states.** Climate request type and Climate running status show "Not running" instead of "Undefined". Unavailable reason shows "Not applicable" while the car is available, instead of Unknown. The state values (`undefined`, `none`) are what automations see.
- **Streamed values survive a full poll.** If a poll endpoint is unsupported for a value that a live stream delivers (for example an odometer that only arrives by stream), the poll used to clear it. The streamed value is now kept, and the poll result is built on the current data so nothing it did not fetch is reset. Port of ericyew's [0da9bc1](https://github.com/ericyew/unofficial-polestar-api/commit/0da9bc1b692d86bf5f115464cd1ed80f2829f6eb); on this fork it only mattered for cars whose poll endpoint is unsupported.

### Changed

- **Charge port hidden on the Polestar 2.** Its charge port status stays closed even with a cable in (as on the electric Volvo XC40 and C40, the same CMA platform), so the sensor is disabled. It is decided from the model, as no capability flag covers it; you can still enable it.
- **Honk and flash is now Lights and horn, and Honk is now Horn**, as the Polestar app calls them (Flash lights already matched). The entity IDs are unchanged.
- **Boot and bonnet, not tailgate and hood.** The Tailgate binary sensor is now called **Boot** and Hood is **Bonnet**, matching Boot lock and the Australian (and UK) wording. Only the names change; existing entity IDs stay.
- **Entity sections tidied** (one rule for both integrations: Diagnostic for health warnings that normally read OK, technical details and versions):
  - to Diagnostic: **12V battery**, **Brake fluid**, **Light status**, **Online** (Connection and In use cover the main view) and **Software version**;
  - to the main section: **Climate time remaining**, which is useful on a dashboard while the climate runs.
- **Name casing:** Battery capacity, Internet activation and Vehicle info (were Battery Capacity, Internet Activation, Vehicle Info).
- **Software update status** (was Software state): the car's over-the-air update progress, with a download icon. "Unknown" now reads **No update** when nothing is downloading or installing; two other states read more clearly.
- **Software update** uses Home Assistant's standard update icons (a package, with an arrow when an update is available) instead of the Polestar logo.
- **Connection reads "In use" while the car is being used**, matching the Polestar app, instead of "Offline: car in use". Polestar reports the car unavailable for remote commands while it is driven, so it never really was offline. Other reasons still read "Offline: …". The In use binary sensor is unchanged.
- The `X-Polestar-Force-Update-Version` header is now `5.15.1`, matching the app version in the user agent (`5.15.1b9417`).

## 0.4.3 (27 November)

### Fixed

- **Accounts asked for a one-time SMS code after the password** got a generic sign-in error in setup and reauth. Polestar ID now sends some accounts to a "required action" page first, usually a one-time text message code to verify the phone number (`otp-phone`). It happens once per account. Setup, reauth and reconfigure now say to sign in once at polestar.com or in the Polestar app, then try again. Accepting new terms lands on the same page and gets the same message. Entering the code in Home Assistant is not supported. Checked against the live flow on two accounts: one with the step pending, one without.
- **No repeated texts.** After Polestar asks for that step, the integration stops signing in with your password by itself (each attempt could text you another code) until you sign in again from Home Assistant.

## 0.4.2 (27 November)

### Fixed

- **Sign-in works again.** Since 26 November Polestar ID hands the login over to a new Keycloak page on `auth.polestar.com`, so every new setup and reauth failed with "Could not find resume path in auth response". The integration now signs in on that page and follows the redirects back to the app. The old login page is still supported if Polestar switches back. Refresh tokens and the token exchange are unchanged. Upstream fix by TheOriginal92 ([kildahldev/unofficial-polestar-api#47](https://github.com/kildahldev/unofficial-polestar-api/pull/47)), tested upstream on a Polestar 4 and with simulated replies here, not yet on our Polestar 2.
- **One-time code (2FA) prompt:** if Polestar asks for a one-time code after the password, the setup and reauth forms now say so ("sign in once at polestar.com with this account, then try again") instead of "Invalid email or password". Entering the code in Home Assistant is not supported.

### Changed

- **README rewritten** for this project (it was still the upstream library's README), with an unofficial and unsupported warning that points to Polestar's official Data Portal where it is available. The separate integration README is folded into it.
- Documentation uses GitHub alert boxes (note, tip, important, warning) for the points that matter.

## 0.4.1 (21 November)

### Fixed

- **Creating and editing parking climate timers from the calendar** (`calendar.create_event`, the calendar UI) failed with "start must be a date-time". Home Assistant passes the start under `dtstart` and the integration read `start`. Upstream fix by Martin Leisssoo ([kildahldev/unofficial-polestar-api#41](https://github.com/kildahldev/unofficial-polestar-api/pull/41)), tested on a Polestar 2. Deleting timers was never affected.
- **Setting the Charging amp limit** now checks the car's delivery status. A refused command (for example car offline) used to look successful. Upstream fix by vladyspavlov ([kildahldev/unofficial-polestar-api#35](https://github.com/kildahldev/unofficial-polestar-api/pull/35)), tested with synthetic replies only, not a real car capture.

### Changed

- **New integration icon and logo** from Rick van der Staaij ([kildahldev/unofficial-polestar-api#28](https://github.com/kildahldev/unofficial-polestar-api/pull/28)), easier to recognise at small sizes. The Inkscape source is included.

## 0.4.0 (11 to 21 November)

### Read this before updating

- **Sensor states are lowercase keys.** Charging status, Charger connection, Usage mode and the other enum sensors report keys such as `charging`, `idle`, `scheduled`, `done`, `connected`, `disconnected`, `driving`, and the frontend shows translated text. Automations and dashboards that compare to `Charging`, `Idle` or `Connected` must use the lowercase keys. Charging status: `charging, idle, scheduled, discharging, error, smart_charging, done, smart_charging_paused`. Charger connection: `connected, disconnected, fault`. Usage mode: `abandoned, inactive, convenience, active, driving, engine_on, engine_off`.
- **The Connection sensor state is short:** `Online`, `Offline: <short reason>` or `Unknown`. The longer explanation and `offline_since` are attributes.
- **Entities were removed or merged** (see Removed). Their registry entries are deleted at setup, and the data they showed moved to attributes on the surviving entity.
- **Display names changed**, entity IDs did not.
- **Climate target temperature and the front seat and steering wheel heating selects are hidden on cars without rear seat settings** (the Polestar 2). The car record has no separate flags for these, so this is a heuristic: a car with front heating but no rear heating would lose them too.
- The three parking climate timer calendars are in the Configuration category and off by default. Existing installs keep their registry state; disable or enable them in the entity settings.
- **Why it is called "Polestar C3":** the integration was renamed (11 November) to tell it apart from the web-based GraphQL [Polestar API](https://github.com/pypolestar/polestar_api) integration (`polestar_api`). This one uses the C3 gRPC services that the Polestar app itself uses, which is why it has live streams, command results and the car's capability flags that the GraphQL one cannot offer. Keeping the two names distinct also avoids confusing their entities in Home Assistant.
- [`polestar_api`](https://github.com/pypolestar/polestar_api) (the older GraphQL integration) is not needed. Move automations and dashboards to this integration's entities before removing it.

### Harmonised with Volvo C3

- Shared entity names in sentence case: Service required, 12V battery, Brake fluid, Washer fluid, Front left door and window, Charge port, Online, State of charge, Outside temperature, Time to full charge, Trip meter (auto) and (manual), Cabin air quality index, Flash lights, Honk and flash, Lock with reduced alarm, Charging amp limit, Target SoC and Target SoC mode, Climate target temperature, Front left seat heating (and the other seats and steering wheel; the timer ones are "Timer front left seat heating"), Climate, Air purification, Charging schedule with Charging schedule start and end, Boot lock.
- Same stored state vocabulary and translated display states as Volvo, whole-number display by default for distance, range, battery, speed and times, entity categories, and the same attribute names for warnings.
- Same behaviour: Start charging is refused with a clear message when the car is not plugged in; Alarm triggered shows OK instead of Unknown when no alarm is reported; In use follows the availability reason; reconfigure flow; entity names from translations; entities hidden for features the car says it lacks.
- Config entry named like Volvo's: model and year.

### Added

- **Tyre warning grade:** per-wheel attributes (`ok`, `very_low`, `low`, `high`) on cars that report individual tyre pressures. Individual pressure sensors appear only on those cars.
- **Service required** attributes `service_urgency` (`almost_due`, `due`, `overdue`) and `service_reason` (`regular`, `engine_hours`, `distance`).
- **Plain-English command failures:** car offline, privacy mode on, car being driven, another command in progress, timeouts. "undefined" is never shown.
- **Average speed** and **Average speed (auto)** sensors. They are hidden when the car sends no value, which is the case on the Polestar 2.
- **Alarm triggered**, **In use**, **Light status** (one attribute per light), fluid and warning problem sensors, and a once-a-minute availability refresh.
- **Adaptive polling:** a shorter interval while charging, driving or running climate, and for 5 minutes after a trip.
- **Lock with reduced alarm**, **Location address**, **Boot lock** (merged with the old Unlock trunk button), **Connection** sensor, **VIN** sensor with model year, battery capacity, internet activation, build week, a verbose **Vehicle info** sensor with one attribute per field, optional registration plate.
- Combustion-only entities are hidden on electric cars.
- Capability gating from the car's own record: charge locations, window and sunroof control, target SoC presets, average consumption sensors, rear seat heating, climate timer slots, tyre pressure, service warning, air purification, honk, flash, light warnings.
- Diagnostics download, reconfigure flow, live streams, and the single-flight token refresh and endpoint handling carried over from the November 11 rework.

### Changed

- **Cabin air quality index** now reports PM2.5 in µg/m³ (PM2.5 device class), like Volvo's, and the separate PM2.5 sensor is gone. The entity keeps its old ID.
- **Target SoC and Charging amp limit** are re-read every minute, so changes made in the Polestar app show up within about a minute. The app does not push these.
- Charge locations are hidden when the car has none saved.
- The privacy setting is read in the background so its timeout no longer stalls polls.
- The vendored `polestar_api` library replaces the PyPI dependency.
- The app version sent to Polestar is now `PolestarApp/5.15.1b9417 Android/14` (was `5.15.0b1118`), matching the current Polestar app.

### Removed

- **Last seen sensor.** It changed every few seconds while charging and filled the activity log. Connection keeps `offline_since`.
- **PM2.5 sensor** (merged into Cabin air quality index).
- **Target SOC sensor** (the Target SoC number shows it).
- **Duplicate Pre-cleaning switch** (one Air Purification switch remains) and the pre-cleaning runtime, start reason and error sensors, which are now attributes of the Air purification switch.
- **Climate sensors** for end time, current temperature, target temperature, seat and steering wheel heating: attributes of the Climate switch, and the heating selects show the choice.
- **Four assumed-power Charging time sensors.**
- **Remote function data sharing (privacy) sensor** and its background fetch.
- **Sunroof sensor** (the Polestar 2 has none).
- Other duplicate entities, with their data folded into the switches.

### Fixed

- Vehicle info attributes are JSON safe (raw bytes used to break state updates).
- The Tyre warning is no longer hidden on cars that omit the tyre warning flag.
- The charge timer switch reads off, not unknown, when no timer is set.
- Software info returns at once when empty and falls back to the installed version from the car record.

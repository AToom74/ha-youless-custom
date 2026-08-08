# YouLess (custom) — Home Assistant integration

A custom Home Assistant integration for the YouLess energy monitor (LS110 / LS120),
built because the built-in `youless` integration does not let you set a **poll interval**
or a **device password**.

Uses its own domain (`youless_custom`), so it runs alongside the built-in integration
without conflict.

## Features

- Configurable poll interval (set at setup, changeable afterwards via **Configure**).
- Optional username / password for password-protected YouLess devices.
- Sensors are created only for the meters your device actually exposes
  (power usage, energy high/low/total, delivery high/low, gas, water, S0 extra,
  and per-phase values where available).
- Sensors are grouped into up to 5 devices — **Power**, **Delivery**, **Gas**,
  **Water**, **Extra** — the same layout as the built-in `youless` integration,
  instead of one device holding every sensor.

## Installation (HACS custom repository)

1. In HACS, open the three-dot menu → **Custom repositories**.
2. Add `https://github.com/AToom74/ha-youless-custom` with category **Integration**.
3. Install **YouLess (custom)** from HACS, then restart Home Assistant.
4. **Settings → Devices & services → Add integration → "YouLess (custom)"**.

## Configuration

Enter the host / IP address of the device. If a password is set in the YouLess web
interface, fill in the password (leave username empty — the LS120 uses a password only).
Set an initial poll interval; you can change it later via **Configure** on the integration.

> Do not set the interval extremely low: the device uses a short HTTP timeout and refreshes
> power roughly once per second, with gas/water far slower. The default of 10 seconds is a
> sensible starting point.

## Changelog

### 1.1.0
- Sensors now live under 5 separate devices (Power / Delivery / Gas / Water / Extra)
  instead of a single device, matching the built-in `youless` integration's layout.
  Existing entities keep their entity ID (unique IDs are unchanged), so history and
  statistics are not affected. After updating and reloading the integration, the old
  single device entry will be left with no entities — you can remove it manually via
  **Settings → Devices & services → Devices**.

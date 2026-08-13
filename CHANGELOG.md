# Changelog

## 0.2.0

- Surface validation and I/O failures as Home Assistant errors so the UI and automations can see them.
- Run Pillow work in an executor, close image handles, convert frames to a GIF-safe RGB mode, and keep frame duration at least 1 ms.
- Guard FPS to 1–60 (default remains 10).
- Register `gif.create_gif` during integration setup (HA action-setup) and require a loaded config entry when the action runs.
- Drop the empty options flow and fix the config flow `@callback` / `async` mix.
- Set `iot_class` to `calculated` for this local service integration.
- Add service selectors, translations, icons, tests, and modern CI (hassfest, HACS, pytest).

## 0.1.2

- Pin Pillow to `>=9.1.0,<13.0.0`.

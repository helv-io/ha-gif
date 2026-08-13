# Changelog

## 0.3.1

- Make `output_path` optional on `gif.create_gif`. Camera mode defaults to `/config/www/gif/<camera_object_id>_<YYYYMMDD_HHMMSS>.gif`; images mode defaults to `/config/www/gif/images_<YYYYMMDD_HHMMSS>.gif`.
- Create `/config/www/gif/` when it is missing.
- Return `output_path` and, when the file is under `www`, a `/local/...` `url` so automations can use `response_variable` without hardcoding a path.

## 0.3.0

- Add optional camera mode to `gif.create_gif`: pass `camera` (a `camera.*` entity), `count` (default 10, range 2–60), and `interval` (default 0.5 s, range 0.1–10 s).
- `images` and `camera` are mutually exclusive. Existing `images` + `fps` + `output_path` + `loop` usage is unchanged.
- Capture stills with `camera.async_get_image`, write temp JPEGs, reuse GIF assembly, and delete temps afterwards.
- Snapshot waits use `asyncio.sleep`; Pillow and disk I/O stay in an executor.
- Validate that the entity exists, is a camera, and is available. Cap count/interval so an automation cannot run forever.

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

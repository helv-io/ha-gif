# HA-GIF

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![Validate](https://github.com/helv-io/ha-gif/actions/workflows/validate.yml/badge.svg)](https://github.com/helv-io/ha-gif/actions/workflows/validate.yml)
[![Tests](https://github.com/helv-io/ha-gif/actions/workflows/test.yml/badge.svg)](https://github.com/helv-io/ha-gif/actions/workflows/test.yml)

A Home Assistant custom integration that creates animated GIFs from image files or a camera entity via `gif.create_gif`.

## Installation

### HACS (Recommended)

#### Option 1: Using My Button

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=helv-io&repository=ha-gif&category=Integration)

After adding the repository, search for **GIF** in HACS → Integrations and install it. Then restart Home Assistant.

#### Option 2: Custom repository

1. Open HACS in Home Assistant.
2. Go to **Integrations**.
3. Click the three dots in the top right and select **Custom repositories**.
4. Add `https://github.com/helv-io/ha-gif` as a repository (category: **Integration**).
5. Search for **GIF** and install it.
6. Restart Home Assistant.

### Manual Installation

1. Download the latest release from the [releases page](https://github.com/helv-io/ha-gif/releases).
2. Extract the contents to `custom_components/gif/` in your Home Assistant configuration directory.
3. Restart Home Assistant.

## Setup

1. Go to **Settings → Devices & services → Add integration**.
2. Search for **GIF** and submit. There is nothing to configure.
3. Only one instance can be added.

The `gif.create_gif` action is registered at startup so automations can be validated even before the entry loads. Calling it without a loaded GIF integration raises an error in the UI.

## Action: `gif.create_gif`

Create an animated GIF from **either** existing image files **or** snapshots of a camera entity. Pass one source, not both.

| Field | Required | Default | Description |
| --- | --- | --- | --- |
| `images` | if no `camera` | — | List of image file paths (JPEG, PNG, and anything else Pillow can open). At least **two** images are required. Mutually exclusive with `camera`. |
| `camera` | if no `images` | — | A `camera.*` entity_id. Snapshots are taken with Home Assistant's `camera.async_get_image` API. Mutually exclusive with `images`. |
| `count` | no | `10` | Number of snapshots in camera mode (`2`–`60`). Ignored when using `images`. |
| `interval` | no | `0.5` | Seconds between snapshots in camera mode (`0.1`–`10`). Ignored when using `images`. Capture length is `(count − 1) × interval`. |
| `fps` | no | `10` | Frames per second of the output GIF (`1`–`60`). |
| `output_path` | yes | — | Path to save the GIF. Parent directories are created if needed. |
| `loop` | no | `true` | Whether the GIF should loop. |

`images` and `camera` are **mutually exclusive**. Providing both raises a validation error (they are not mixed). Providing neither also raises. `output_path` is always required. `fps` and `loop` apply to the output GIF in both modes.

Frames of different sizes are resized to match the first image. Palette and RGBA sources are converted to RGB (transparency is flattened onto white) before save. Invalid input or I/O errors raise a Home Assistant error so the action fails visibly in automations.

The camera entity must exist, be in the `camera` domain, and be available (not `unavailable` / `unknown`). Snapshot files are written to a temp directory and deleted after the GIF is saved.

### YAML example (image files)

```yaml
action: gif.create_gif
data:
  images:
    - /config/www/gif/image1.jpg
    - /config/www/gif/image2.jpg
  fps: 10
  output_path: /config/www/gif/output.gif
  loop: true
```

`service: gif.create_gif` still works.

You can also call this from **Developer Tools → Actions**. The form uses selectors for the image list, camera entity, count, interval, FPS, output path, and loop toggle.

## Camera → GIF

Pass a camera entity and how many frames to grab. This is the usual doorbell / motion pattern:

```yaml
automation:
  - alias: Front door GIF
    triggers:
      - trigger: state
        entity_id: binary_sensor.front_doorbell
        to: "on"
    actions:
      - action: gif.create_gif
        data:
          camera: camera.front_door
          count: 10
          interval: 0.5
          fps: 10
          output_path: /config/www/gif/front_door.gif
          loop: true
```

That captures 10 stills 0.5 s apart (~4.5 s of video), then stitches them. Motion works the same way with `binary_sensor.front_door_motion`.

File-path usage is unchanged if you already snapshot yourself and pass `images`.

Home Assistant can write under `/config/www` by default. The GIF is then available at `/local/gif/front_door.gif`.

## Requirements

- Home Assistant 2024.6.0 or later
- Pillow (installed automatically from `manifest.json`)

## Changelog

See [CHANGELOG.md](CHANGELOG.md).

## License

This integration is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

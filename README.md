# HA-GIF

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)

A custom Home Assistant component to create GIFs from images.

## Installation

### HACS (Recommended)

#### Option 1: Using My Button

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=helv-io&repository=ha.gif&category=Integration)

After adding the repository, search for "GIF" in HACS > Integrations and install it. Then, restart Home Assistant.

#### Option 2: Manual

1. Open HACS in Home Assistant.
2. Go to "Integrations".
3. Click the three dots in the top right and select "Custom repositories".
4. Add `https://github.com/helv-io/ha.gif` as a repository (category: Integration).
5. Search for "GIF" and install it.
6. Restart Home Assistant.

### Manual Installation

1. Download the latest release from the [releases page](https://github.com/helv-io/ha.gif/releases).
2. Extract the contents to `custom_components/gif/` in your Home Assistant configuration directory.
3. Restart Home Assistant.

## Usage

Call the service `gif.create_gif` with the following parameters:

- `images`: List of image file paths (at least 2)
- `fps`: Frames per second (optional, default 10)
- `output_path`: Path to save the GIF

Example in YAML:

```yaml
service: gif.create_gif
data:
  images:
    - /config/images/image1.jpg
    - /config/images/image2.jpg
  fps: 10
  output_path: /config/gifs/output.gif
```

## Requirements

- Pillow library (automatically installed via manifest.json)

## License

See LICENSE file.

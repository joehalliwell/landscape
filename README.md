# Landscape

A surprisingly sophisticated and varied ASCII-style landscape generator. The
trick is that it generates a 3D voxel landscape then projects it to 2D
ASCII-style for display with some non-photorealistic rendering stuff chucked in.

## Installation

```bash
pip install landscape
```

Or run directly with:

```bash
uvx landscape
```

## Usage

Generate a random landscape:

```bash
landscape
```

Use a preset:

```bash
landscape --preset coastal
landscape --preset alpine-lake --time dusk
```

Set the atmosphere and season:

```bash
landscape --atmosphere foggy-day --season mid-autumn
```

Reproduce a specific landscape from its signature:

```bash
landscape -S <signature>
```

Run `landscape --help` for the full list of options.

## License

MIT — see [LICENSE](LICENSE) for details.

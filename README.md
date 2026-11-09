# TJM Extras

The TJM Store's source for the apps whose native parts are built by their own authors: they are not rebuilt here,
the pinned upstream files are mirrored into this repo's `catalog` release, and the four apps are shown as TJM apps.

| TJM app | Based on | License |
|---|---|---|
| TJM Moonride | [JustAnotherPU/moonride](https://github.com/JustAnotherPU/moonride) | see `LICENSES/` |
| TJM RideWatch | [JustAnotherPU/ridewatch](https://github.com/JustAnotherPU/ridewatch) | see `LICENSES/` |
| TJM RideTube | [JustAnotherPU/ridetube](https://github.com/JustAnotherPU/ridetube) | see `LICENSES/` |
| TJM Browser | [pllanaio/mgu-browser](https://github.com/pllanaio/mgu-browser) | see `LICENSES/` |

Also mirrored unchanged, as the apps need them: `jap-node22`, `jap-moonride`, `jap-ridewatch`, `jap-ridetube-d`,
`mgu-browser-engine`, `mgu-browser`.

- `mirror.json`: every upstream entry, pinned by version and sha256, and the TJM name and icon of each app.
- `icons/`: the TJM icons.
- `tools/build_catalog.py`: downloads, checks the sha256, renames the app tile (every language), swaps the icon,
  writes `out/catalog.json` (schema 2). The same input gives the same bytes.
- `.github/workflows/publish.yml`: runs it and uploads `out/` to the `catalog` release.

Changes to the apps: only the tile name and the icon. All credit stays with the original authors.

Local check: `python3 tools/build_catalog.py --repo <owner>/tjm-extras --out out`

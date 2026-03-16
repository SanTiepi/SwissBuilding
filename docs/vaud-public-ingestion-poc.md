# Vaud Public Ingestion PoC

## Goal

Use official public Vaud building data to create a realistic SwissBuilding test dataset without scraping the public map UI.

This PoC is intentionally limited:

- scope: one commune, or a few communes, not the full canton
- purpose: test the app with credible real-world buildings
- output: normalized `Building` records that fit the current SwissBuilding schema

## Why this path

The Vaud public geoservice exposes useful building and address layers:

- `vd.batiment_rcb`: public cantonal building registry attributes
- `vd.adresse`: public addresses with `EGID`
- `vd.batiment`: cadastral building footprint / surface data

The public `MapServer/query` endpoint is usable, but it has `maxRecordCount = 1` on the exposed building layers. That makes it fine for a PoC by commune and small limits, but not for a full-canton bulk import.

For scale-up, the better route is the official bulk distribution mentioned by the Vaud metadata itself:

- public RCBat metadata: `https://viageo.ch/md/af46056f-27ac-423a-af2f-f1880744ee6c`
- public WMS endpoint: `https://www.ogc.vd.ch/public/services/OGC/wmsVD/Mapserver/WMSServer?`
- the metadata also points to the federal public RegBL / housing-stat download for bulk data

## Current mapping to SwissBuilding

The current SwissBuilding `Building` model can absorb only part of the Vaud public attributes.

### Imported now

- `official_id` <- `EGID`
- `address` <- `VOIE_TXT + NO_ENTREE`
- `postal_code` <- `NPA`
- `city` <- `LOCALITE`
- `canton` <- `VD`
- `latitude`, `longitude` <- `vd.batiment_rcb` geometry converted with `outSR=4326`
- `construction_year` <- `CONS_ANNEE`
- `building_type` <- heuristic mapping from `CATEGORIE_TXT` / `CLASSE_TXT`
- `floors_above` <- `NB_NIV_TOT`
- `surface_area_m2` <- `SRE`, fallback `SURFACE`

### Not imported yet

- `egrid`: not available from the public building layers used here
- `parcel_number`: not available from the public layers used here
- `volume_m3`
- owner / land registry data
- full heating / hot-water metadata in the main table

Those source fields are still kept in the normalized JSON export for inspection, but the current DB schema does not persist them.

## Implemented tool

`backend/app/importers/vaud_public.py`

The importer:

- requires a narrow filter (`--commune`, `--municipality-ofs`, or `--postal-code`)
- harvests public address ids first
- deduplicates addresses by `EGID`
- fetches matching `vd.batiment_rcb` records
- normalizes them into the SwissBuilding `Building` shape
- optionally writes a JSON export
- optionally imports the records into the local DB

## Recommended PoC scope

Start small:

1. Lausanne or Yverdon-les-Bains
2. `100` to `300` buildings
3. verify list, filters, map, building detail, risk scoring
4. only then widen to more communes

## Example commands

Dry-run + JSON export:

```bash
cd backend
python -m app.importers.vaud_public --commune Lausanne --limit 150 --output-json ../tmp/vaud-lausanne-150.json
```

Synthetic demo seed + Vaud enrichment in one step:

```bash
cd backend
python -m app.seeds.seed_demo --commune Lausanne --limit 150
```

Synthetic demo seed + Vaud dry-run:

```bash
cd backend
python -m app.seeds.seed_demo --commune Lausanne --limit 150 --dry-run-vaud --output-json ../tmp/vaud-lausanne-150.json
```

Synthetic demo seed only:

```bash
cd backend
python -m app.seeds.seed_demo --skip-vaud
```

Import into local SwissBuilding DB:

```bash
cd backend
python -m app.importers.vaud_public --commune Lausanne --limit 150 --apply
```

Target a municipality by OFS code instead of name:

```bash
cd backend
python -m app.importers.vaud_public --municipality-ofs 5586 --limit 150 --apply
```

## Next step after PoC

If the PoC works well, switch from one-feature public geoservice harvesting to an official bulk source:

- federal public RegBL / housing-stat export
- or an official Vaud bulk extract where allowed

That will be necessary to ingest the whole canton efficiently.

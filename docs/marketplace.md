# Marketplace Integration

Search and import CAD models from the three largest community model repositories directly from the webapp.

## Supported Sources

| Source | API Type | Auth Required | Download Format |
|:---|:---|:---|:---|
| **Printables** | GraphQL | No | STL, STEP (direct) |
| **Thingiverse** | REST | No | ZIP (auto-extracted) |
| **GrabCAD** | REST | No | Varies (model page link) |

## Search Endpoint

```
GET /api/v1/marketplace/search?source=printables&query=robot+chassis&limit=20&page=1
```

Returns normalized results across all sources:

```json
{
  "success": true,
  "source": "printables",
  "results": [
    {
      "id": "123456",
      "title": "Robot Chassis v2",
      "summary": "Modular robot chassis with mounting holes...",
      "author": "maker42",
      "downloads": 1520,
      "likes": 87,
      "image_url": "https://media.printables.com/...",
      "model_url": "https://www.printables.com/model/123456",
      "download_url": "https://www.printables.com/model/123456/download",
      "source": "printables"
    }
  ],
  "total": 230
}
```

## Download Endpoint

```
POST /api/v1/marketplace/download
{
  "source": "thingiverse",
  "model_id": "67890",
  "file_url": "https://www.thingiverse.com/thing:67890/zip",
  "filename": "robot_chassis_v2.zip"
}
```

The server downloads the file to the `uploads/` directory. For Thingiverse (ZIP downloads), it auto-extracts STL and STEP files:

```json
{
  "success": true,
  "filename": "robot_chassis_v2.zip",
  "size_bytes": 2456789,
  "extracted": [
    {"filename": "chassis_base.stl", "size_bytes": 1234567},
    {"filename": "chassis_top.stl", "size_bytes": 987654}
  ]
}
```

Extracted files appear immediately in the Models page for viewing and slicing.

## Printables

The largest 3D printing community (Prusa Research). GraphQL API at `api.printables.com`.

- No auth needed for search
- Direct STL download URLs
- Rich metadata: likes, downloads, makes, remixes
- Model pages: `printables.com/model/{id}-{slug}`

## Thingiverse

The original 3D model repository (MakerBot/UltiMaker). REST API at `api.thingiverse.com`.

- Unofficial but stable API
- Downloads come as ZIP files — server auto-extracts STL/STEP
- Good for legacy models and classic designs
- Model pages: `thingiverse.com/thing:{id}`

## GrabCAD

Professional CAD model community (Stratasys). REST API at `grabcad.com/api/v1`.

- More engineering-focused (STEP assemblies, mechanical parts)
- Download URLs from model pages (varies by uploader)
- Good source for real mechanical components
- Library: `grabcad.com/library/{slug}`

## Flow

```
Marketplace Page
  │
  ├── Search Printables / Thingiverse / GrabCAD
  │     └── GET /api/v1/marketplace/search
  │
  ├── Browse results (thumbnails, stats)
  │
  ├── Click "Import"
  │     └── POST /api/v1/marketplace/download
  │           └── file saved to uploads/
  │
  ├── Switch to Models page
  │     ├── Click file → 3D viewer (Three.js)
  │     └── Click file → model_info() metadata
  │
  └── Switch to Convert page
        └── STEP → STL → slice in PrusaSlicer
```

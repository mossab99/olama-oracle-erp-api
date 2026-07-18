# Transportation master API

These read-only bridge endpoints are consumed by **Olama Oracle Sync only**:

- `GET /api/transportation/buses`
- `GET /api/transportation/regions?study_year=2026/2027`

The ingestion path is:

`Oracle -> D:\api -> olama-oracle-sync -> Olama Core`

Domain plugins, including Olama Transportation, must never call these
endpoints. They read the canonical `olama_core_transport_buses` and
`olama_core_transport_regions` records through Olama Core services.

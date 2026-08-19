# Transportation master API

These read-only bridge endpoints are consumed by **Olama Oracle Sync only**:

- `GET /api/transportation/buses`
- `GET /api/transportation/regions?study_year=2026/2027`
- `GET /api/transportation/family-locations?limit=500&offset=0`

The ingestion path is:

`Oracle -> D:\api -> olama-oracle-sync -> Olama Core`

Domain plugins, including Olama Transportation, must never call these
endpoints. They read the canonical `olama_core_transport_buses` and
`olama_core_transport_regions` records through Olama Core services. The family
location endpoint refreshes only the canonical family address, building/home
numbers, and Oracle transportation region. It does not write Transportation's
local Planning Area assignment.

Region semantics:

- Only rows whose `SCH_TRANS_REGIONS.IS_ACTIVE` value is `1` are returned.
- `is_active` is included explicitly in every region object.

Bus field semantics:

- `bus_number`: internal school bus code from `BUS_SCHOOL_NUMBER`.
- `government_number`: actual bus number from `BUS_GOV_NUMBER`.
- `driver_license_number`: license number from the `BUS_LICENSE_*` Forms item.

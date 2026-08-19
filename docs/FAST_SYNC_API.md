# Fast Sync API

Fast Sync is an additive, authenticated API. Existing family, student,
financial, and transportation endpoints remain unchanged.

```text
GET /api/v1/sync/families-bulk?study_year=2026%2F2027&limit=50&cursor=0
X-API-Key: <configured key>
```

`limit` must be between 1 and 100. `cursor` is the last processed Oracle
`FAMILY_ID`; use the returned `next_cursor` for the next request while
`has_more` is true. Cursor pagination makes retries idempotent and avoids the
shifting-page problem of offset pagination.

Each item in `families` contains the family projection, students for the
requested study year, the financial summary/dues/transactions, and
transportation rows. The endpoint executes a fixed seven Oracle queries per
page instead of opening several Bridge requests for every family.

Deploy the Bridge changes before enabling Fast Sync in WordPress. The
WordPress client retains Standard Sync and automatically falls back to it if
the first bulk request is unavailable.

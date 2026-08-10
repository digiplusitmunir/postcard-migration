# Useful DB Commands

## 1. Connect to the database (psql)

```bash
# Test database (current DATABASE_URL)
psql postgres://postgres:admin12345@127.0.0.1:5432/postcardv2_test

# Main database
psql postgres://postgres:admin12345@127.0.0.1:5432/postcardv2
```

Or the long form:

```bash
psql -h 127.0.0.1 -p 5432 -U postgres -d postcardv2_test
```

## 2. psql meta-commands (backslash commands)

| Command | What it does |
|---|---|
| `\l` | List all databases |
| `\c dbname` | Connect (switch) to another database |
| `\conninfo` | Show current connection info (db, user, host, port) |
| `\dt` | List all tables in the current schema |
| `\dt+` | List tables with size and description |
| `\d table_name` | Describe a table (columns, types, indexes, FKs) |
| `\d+ table_name` | Describe a table with extra detail (storage, comments) |
| `\ds` | List sequences (auto-increment counters) |
| `\dv` | List views |
| `\di` | List indexes |
| `\df` | List functions |
| `\dn` | List schemas |
| `\du` | List roles/users and their privileges |
| `\dx` | List installed extensions |
| `\dT` | List data types (incl. enums like `ContentStatus`) |
| `\x` | Toggle expanded output (vertical rows — great for wide tables) |
| `\timing` | Toggle query execution time display |
| `\e` | Open last query in editor |
| `\i file.sql` | Run SQL commands from a file |
| `\copy table TO 'file.csv' CSV HEADER` | Export a table to CSV |
| `\! command` | Run a shell command without leaving psql |
| `\h SELECT` | Help/syntax for an SQL command |
| `\?` | Help — list all backslash commands |
| `\q` | Quit psql |

## 3. Prisma Studio (visual DB browser)

```bash
# From the postcard-migration folder (uses prisma.config.ts + .env)
npx prisma studio

# or via the package script
npm run studio
```

Opens at http://localhost:5555 — browse and edit tables in the browser.

## 4. Important SQL queries

```sql
-- Count rows in a table
SELECT COUNT(*) FROM postcards;

-- Row counts for ALL tables at once (approximate, fast)
SELECT relname AS table_name, n_live_tup AS row_count
FROM pg_stat_user_tables
ORDER BY n_live_tup DESC;

-- Table sizes on disk
SELECT relname AS table_name,
       pg_size_pretty(pg_total_relation_size(relid)) AS total_size
FROM pg_catalog.pg_statio_user_tables
ORDER BY pg_total_relation_size(relid) DESC;

-- Peek at data
SELECT * FROM collections LIMIT 10;

-- Filter + sort
SELECT id, name, slug, status
FROM postcards
WHERE status = 'published'
ORDER BY priority DESC
LIMIT 20;

-- Search by partial name (case-insensitive)
SELECT id, name FROM collections WHERE name ILIKE '%beach%';

-- Group + count (postcards per status)
SELECT status, COUNT(*) FROM postcards GROUP BY status;

-- Find duplicate slugs (should return 0 rows)
SELECT slug, COUNT(*) FROM postcards GROUP BY slug HAVING COUNT(*) > 1;

-- Rows created without a required-ish FK (orphan check)
SELECT COUNT(*) FROM postcards WHERE collection_id IS NULL;

-- Empty a table and reset its id sequence (careful!)
TRUNCATE TABLE postcards RESTART IDENTITY CASCADE;

-- Delete with a condition
DELETE FROM postcards WHERE status = 'draft';

-- Update a value
UPDATE collections SET is_featured = true WHERE id = 1;
```

## 5. Join queries

```sql
-- Postcards with their collection name (INNER JOIN — only postcards that have a collection)
SELECT p.id, p.name AS postcard, c.name AS collection
FROM postcards p
JOIN collections c ON c.id = p.collection_id
LIMIT 20;

-- LEFT JOIN — all postcards, collection name NULL when they have none
SELECT p.id, p.name AS postcard, c.name AS collection
FROM postcards p
LEFT JOIN collections c ON c.id = p.collection_id
LIMIT 20;

-- Full geo chain: city -> region -> country
SELECT ci.name AS city, r.name AS region, co.name AS country
FROM cities ci
JOIN regions r ON r.id = ci.region_id
JOIN countries co ON co.id = r.country_id
ORDER BY co.name, r.name, ci.name;

-- Postcards with their full location (LEFT JOINs since geo fields are optional)
SELECT p.name AS postcard,
       co.name AS country, r.name AS region, ci.name AS city
FROM postcards p
LEFT JOIN countries co ON co.id = p.country_id
LEFT JOIN regions   r  ON r.id  = p.region_id
LEFT JOIN cities    ci ON ci.id = p.city_id
LIMIT 20;

-- Count postcards per collection (JOIN + GROUP BY)
SELECT c.name AS collection, COUNT(p.id) AS postcard_count
FROM collections c
LEFT JOIN postcards p ON p.collection_id = c.id
GROUP BY c.id, c.name
ORDER BY postcard_count DESC;

-- Count collections per collection type
SELECT ct.name AS type, COUNT(c.id) AS collections
FROM collection_types ct
LEFT JOIN collections c ON c.collection_type_id = ct.id
GROUP BY ct.id, ct.name
ORDER BY collections DESC;

-- Many-to-many through a join table: postcards in a subcollection, in order
SELECT s.name AS subcollection, sp.sequence_order, p.name AS postcard
FROM subcollection_postcards sp
JOIN subcollections s ON s.id = sp.subcollection_id
JOIN postcards p      ON p.id = sp.postcard_id
ORDER BY s.name, sp.sequence_order;

-- Postcards with their tags (implicit Prisma M2M table "_PostcardTags")
SELECT p.name AS postcard, t.name AS tag
FROM postcards p
JOIN "_PostcardTags" pt ON pt."A" = p.id
JOIN tags t             ON t.id  = pt."B"
ORDER BY p.name;

-- Collections that have NO postcards (anti-join)
SELECT c.id, c.name
FROM collections c
LEFT JOIN postcards p ON p.collection_id = c.id
WHERE p.id IS NULL;
```

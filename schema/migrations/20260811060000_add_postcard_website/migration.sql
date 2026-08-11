-- AlterTable
-- Restaurants/Events/Shopping albums migrate straight into `postcards` (their
-- collection type has has_dedicated_collection = false, so there is no
-- Collection row to hold the album's website). 661 of 667 such legacy albums
-- carry a `website`, so postcards need the same column `collections` has.
ALTER TABLE "postcards" ADD COLUMN     "website" TEXT;

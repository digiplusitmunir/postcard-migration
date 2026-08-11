-- CreateTable
-- Scope of a cluster type: which CollectionTypes it is a cluster OF.
-- City Guide is a cluster of Restaurants + Events + Shopping (3 rows).
CREATE TABLE "cluster_type_collection_types" (
    "id" BIGSERIAL NOT NULL,
    "cluster_type_id" BIGINT NOT NULL,
    "collection_type_id" BIGINT NOT NULL,
    "priority" INTEGER NOT NULL DEFAULT 0,

    CONSTRAINT "cluster_type_collection_types_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE INDEX "cluster_type_collection_types_collection_type_id_idx" ON "cluster_type_collection_types"("collection_type_id");

-- CreateIndex
CREATE UNIQUE INDEX "cluster_type_collection_types_cluster_type_id_collection_typ_key" ON "cluster_type_collection_types"("cluster_type_id", "collection_type_id");

-- AddForeignKey
ALTER TABLE "cluster_type_collection_types" ADD CONSTRAINT "cluster_type_collection_types_cluster_type_id_fkey" FOREIGN KEY ("cluster_type_id") REFERENCES "collection_cluster_types"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "cluster_type_collection_types" ADD CONSTRAINT "cluster_type_collection_types_collection_type_id_fkey" FOREIGN KEY ("collection_type_id") REFERENCES "collection_types"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AlterTable
ALTER TABLE "collection_clusters" ADD COLUMN     "cover_media_id" BIGINT,
ADD COLUMN     "community_link" TEXT;

-- AddForeignKey
ALTER TABLE "collection_clusters" ADD CONSTRAINT "collection_clusters_cover_media_id_fkey" FOREIGN KEY ("cover_media_id") REFERENCES "media"("id") ON DELETE SET NULL ON UPDATE CASCADE;

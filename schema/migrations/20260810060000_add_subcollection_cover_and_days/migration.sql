-- AlterTable
ALTER TABLE "subcollections" ADD COLUMN     "number_of_days" INTEGER,
ADD COLUMN     "cover_media_id" BIGINT;

-- AddForeignKey
ALTER TABLE "subcollections" ADD CONSTRAINT "subcollections_cover_media_id_fkey" FOREIGN KEY ("cover_media_id") REFERENCES "media"("id") ON DELETE SET NULL ON UPDATE CASCADE;

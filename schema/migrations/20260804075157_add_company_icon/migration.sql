-- AlterTable
ALTER TABLE "companies" ADD COLUMN     "icon_media_id" BIGINT;

-- AddForeignKey
ALTER TABLE "companies" ADD CONSTRAINT "companies_icon_media_id_fkey" FOREIGN KEY ("icon_media_id") REFERENCES "media"("id") ON DELETE SET NULL ON UPDATE CASCADE;

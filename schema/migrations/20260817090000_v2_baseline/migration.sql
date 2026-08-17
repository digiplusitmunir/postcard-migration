-- CreateSchema
CREATE SCHEMA IF NOT EXISTS "public";

-- CreateEnum
CREATE TYPE "ContentStatus" AS ENUM ('draft', 'assigned', 'submit', 'rework', 'live');

-- CreateEnum
CREATE TYPE "JourneyStatus" AS ENUM ('draft', 'deckBuild', 'deckFreeze', 'onTrip', 'complete');

-- CreateEnum
CREATE TYPE "CompanyStatus" AS ENUM ('pending', 'active', 'suspended');

-- CreateEnum
CREATE TYPE "Continent" AS ENUM ('africa', 'antarctica', 'asia', 'europe', 'north_america', 'oceania', 'south_america');

-- CreateEnum
CREATE TYPE "MembershipTier" AS ENUM ('free', 'star_life');

-- CreateEnum
CREATE TYPE "MembershipStatus" AS ENUM ('active', 'expired', 'cancelled');

-- CreateEnum
CREATE TYPE "UserRoleStatus" AS ENUM ('active', 'suspended', 'revoked');

-- CreateEnum
CREATE TYPE "FacetOwnedType" AS ENUM ('collection', 'postcard', 'subcollection');

-- CreateEnum
CREATE TYPE "CircleOwnedType" AS ENUM ('postcard', 'collection', 'subcollection', 'collection_cluster', 'facet_value', 'tag', 'company', 'user');

-- CreateEnum
CREATE TYPE "CircleRelationship" AS ENUM ('bookmark', 'booked');

-- CreateEnum
CREATE TYPE "ShareType" AS ENUM ('private', 'public', 'selected');

-- CreateEnum
CREATE TYPE "UserEventType" AS ENUM ('backlink', 'collection_view', 'postcard_view', 'postcard_collect', 'postcard_flip', 'search', 'search_experiences', 'autocomplete_search_initiated', 'autocomplete_search_completed', 'guided_search_initiated', 'guided_search_completed', 'follow_collection', 'follow_user', 'bookmark', 'enquiry_submitted', 'memory_created', 'tag_click');

-- CreateEnum
CREATE TYPE "EventSubjectType" AS ENUM ('postcard', 'collection', 'subcollection', 'collection_cluster', 'tag', 'company', 'user');

-- CreateEnum
CREATE TYPE "EnquirySubjectType" AS ENUM ('subcollection', 'collection', 'postcard');

-- CreateEnum
CREATE TYPE "EnquiryStatus" AS ENUM ('new', 'in_progress', 'responded', 'closed');

-- CreateEnum
CREATE TYPE "PriceAffinity" AS ENUM ('budget', 'mid', 'luxury');

-- CreateEnum
CREATE TYPE "PriceType" AS ENUM ('per_person', 'twin_sharing');

-- CreateTable
CREATE TABLE "collection_types" (
    "id" BIGSERIAL NOT NULL,
    "name" TEXT NOT NULL,
    "slug" TEXT NOT NULL,
    "description" TEXT,
    "icon" TEXT,
    "has_dedicated_collection" BOOLEAN NOT NULL DEFAULT false,
    "priority" INTEGER NOT NULL DEFAULT 0,

    CONSTRAINT "collection_types_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "collections" (
    "id" BIGSERIAL NOT NULL,
    "collection_type_id" BIGINT NOT NULL,
    "name" TEXT NOT NULL,
    "intro" TEXT,
    "story" TEXT,
    "slug" TEXT NOT NULL,
    "cover_media_id" BIGINT,
    "seo" JSONB,
    "gallery" JSONB,
    "is_featured" BOOLEAN NOT NULL DEFAULT false,
    "priority" INTEGER NOT NULL DEFAULT 0,
    "country_id" BIGINT,
    "region_id" BIGINT,
    "locality_id" BIGINT,
    "location" JSONB,
    "managed_by_company_id" BIGINT,
    "owner_user_id" BIGINT,
    "assigned_to_user_id" BIGINT,
    "website" TEXT,
    "signature" TEXT,
    "about" TEXT,
    "status" "ContentStatus" NOT NULL DEFAULT 'draft',

    CONSTRAINT "collections_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "postcards" (
    "id" BIGSERIAL NOT NULL,
    "name" TEXT NOT NULL,
    "intro" TEXT,
    "slug" TEXT NOT NULL,
    "story" TEXT,
    "collection_type_id" BIGINT NOT NULL,
    "collection_id" BIGINT,
    "user_id" BIGINT,
    "country_id" BIGINT,
    "region_id" BIGINT,
    "locality_id" BIGINT,
    "location" JSONB,
    "seo" JSONB,
    "event_details" JSONB,
    "website" TEXT,
    "signature" TEXT,
    "copyright" TEXT,
    "is_founder_story" BOOLEAN NOT NULL DEFAULT false,
    "is_featured" BOOLEAN NOT NULL DEFAULT false,
    "priority" INTEGER NOT NULL DEFAULT 0,
    "cover_media_id" BIGINT,
    "status" "ContentStatus" NOT NULL DEFAULT 'draft',
    "published_at" TIMESTAMP(3),

    CONSTRAINT "postcards_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "subcollection_types" (
    "id" BIGSERIAL NOT NULL,
    "collection_type_id" BIGINT NOT NULL,
    "name" TEXT NOT NULL,
    "slug" TEXT NOT NULL,
    "description" TEXT,
    "priority" INTEGER NOT NULL DEFAULT 0,

    CONSTRAINT "subcollection_types_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "subcollections" (
    "id" BIGSERIAL NOT NULL,
    "subcollection_type_id" BIGINT NOT NULL,
    "collection_id" BIGINT NOT NULL,
    "name" TEXT NOT NULL,
    "intro" TEXT,
    "story" TEXT,
    "slug" TEXT NOT NULL,
    "tour_info" TEXT,
    "day_wise_itinerary" TEXT,
    "terms_and_conditions" TEXT,
    "price" DECIMAL(12,2),
    "price_type" "PriceType",
    "number_of_nights" INTEGER,
    "number_of_days" INTEGER,
    "number_of_rooms" INTEGER,
    "guests_per_room" INTEGER,
    "best_months" JSONB,
    "cover_media_id" BIGINT,
    "managed_by_company_id" BIGINT,
    "created_by_user_id" BIGINT,
    "status" "JourneyStatus" NOT NULL DEFAULT 'draft',

    CONSTRAINT "subcollections_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "subcollection_postcards" (
    "subcollection_id" BIGINT NOT NULL,
    "postcard_id" BIGINT NOT NULL,
    "sequence_order" INTEGER NOT NULL,

    CONSTRAINT "subcollection_postcards_pkey" PRIMARY KEY ("subcollection_id","postcard_id")
);

-- CreateTable
CREATE TABLE "collection_cluster_types" (
    "id" BIGSERIAL NOT NULL,
    "name" TEXT NOT NULL,
    "slug" TEXT NOT NULL,
    "description" TEXT,
    "priority" INTEGER NOT NULL DEFAULT 0,
    "collection_type_ids" BIGINT[] DEFAULT ARRAY[]::BIGINT[],
    "match_field" TEXT NOT NULL DEFAULT 'region_id',

    CONSTRAINT "collection_cluster_types_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "collection_clusters" (
    "id" BIGSERIAL NOT NULL,
    "cluster_type_id" BIGINT NOT NULL,
    "name" TEXT NOT NULL,
    "slug" TEXT NOT NULL,
    "intro" TEXT,
    "story" TEXT,
    "country_id" BIGINT,
    "region_id" BIGINT,
    "managed_by_company_id" BIGINT,
    "cover_media_id" BIGINT,
    "community_link" TEXT,
    "status" "ContentStatus" NOT NULL DEFAULT 'draft',

    CONSTRAINT "collection_clusters_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "countries" (
    "id" BIGSERIAL NOT NULL,
    "name" TEXT NOT NULL,
    "slug" TEXT NOT NULL,
    "code" TEXT,
    "continent" "Continent",
    "flag_media_id" BIGINT,

    CONSTRAINT "countries_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "regions" (
    "id" BIGSERIAL NOT NULL,
    "country_id" BIGINT NOT NULL,
    "name" TEXT NOT NULL,
    "slug" TEXT NOT NULL,
    "lat" DECIMAL(9,6),
    "lng" DECIMAL(9,6),

    CONSTRAINT "regions_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "localities" (
    "id" BIGSERIAL NOT NULL,
    "region_id" BIGINT NOT NULL,
    "name" TEXT NOT NULL,
    "slug" TEXT NOT NULL,
    "google_place_id" TEXT,
    "lat" DECIMAL(9,6),
    "lng" DECIMAL(9,6),

    CONSTRAINT "localities_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "facet_types" (
    "id" BIGSERIAL NOT NULL,
    "name" TEXT NOT NULL,
    "slug" TEXT NOT NULL,
    "applies_to_collection_type_id" BIGINT,
    "applies_to_subcollection_type_id" BIGINT,
    "allows_multiple" BOOLEAN NOT NULL DEFAULT false,

    CONSTRAINT "facet_types_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "facet_values" (
    "id" BIGSERIAL NOT NULL,
    "facet_type_id" BIGINT NOT NULL,
    "name" TEXT NOT NULL,
    "slug" TEXT NOT NULL,

    CONSTRAINT "facet_values_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "facet_assignments" (
    "id" BIGSERIAL NOT NULL,
    "owned_type" "FacetOwnedType" NOT NULL,
    "owned_id" BIGINT NOT NULL,
    "facet_value_id" BIGINT NOT NULL,

    CONSTRAINT "facet_assignments_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "tags" (
    "id" BIGSERIAL NOT NULL,
    "name" TEXT NOT NULL,
    "slug" TEXT NOT NULL,

    CONSTRAINT "tags_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "companies" (
    "id" BIGSERIAL NOT NULL,
    "title" TEXT NOT NULL,
    "slug" TEXT NOT NULL,
    "contact_email" TEXT,
    "contact_phone" TEXT,
    "website" TEXT,
    "logo_media_id" BIGINT,
    "cover_image_media_id" BIGINT,
    "status" "CompanyStatus" NOT NULL DEFAULT 'pending',

    CONSTRAINT "companies_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "user_types" (
    "id" BIGSERIAL NOT NULL,
    "title" TEXT NOT NULL,
    "slug" TEXT NOT NULL,
    "is_default" BOOLEAN NOT NULL DEFAULT false,
    "is_creator" BOOLEAN NOT NULL DEFAULT false,
    "is_admin" BOOLEAN NOT NULL DEFAULT false,

    CONSTRAINT "user_types_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "users" (
    "id" BIGSERIAL NOT NULL,
    "username" TEXT NOT NULL,
    "email" TEXT NOT NULL,
    "slug" TEXT,
    "first_name" TEXT,
    "last_name" TEXT,
    "password_hash" TEXT,
    "auth_provider" TEXT,
    "provider_id" TEXT,
    "email_verified" BOOLEAN NOT NULL DEFAULT false,
    "is_blocked" BOOLEAN NOT NULL DEFAULT false,
    "profile_pic_id" BIGINT,
    "cover_image_id" BIGINT,
    "bio" TEXT,
    "social" JSONB,
    "seo" JSONB,
    "tracking" JSONB,
    "is_featured" BOOLEAN NOT NULL DEFAULT false,
    "priority" INTEGER NOT NULL DEFAULT 0,
    "country_id" BIGINT,
    "region_id" BIGINT,
    "locality_id" BIGINT,
    "city_name" TEXT,
    "is_admin" BOOLEAN NOT NULL DEFAULT false,

    CONSTRAINT "users_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "memberships" (
    "id" BIGSERIAL NOT NULL,
    "user_id" BIGINT NOT NULL,
    "tier" "MembershipTier" NOT NULL DEFAULT 'free',
    "started_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "ends_at" TIMESTAMP(3),
    "status" "MembershipStatus" NOT NULL DEFAULT 'active',

    CONSTRAINT "memberships_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "user_roles" (
    "id" BIGSERIAL NOT NULL,
    "user_id" BIGINT NOT NULL,
    "user_type_id" BIGINT NOT NULL,
    "company_id" BIGINT,
    "manager_user_id" BIGINT,
    "granted_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "status" "UserRoleStatus" NOT NULL DEFAULT 'active',

    CONSTRAINT "user_roles_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "circles" (
    "id" BIGSERIAL NOT NULL,
    "user_id" BIGINT NOT NULL,
    "owned_type" "CircleOwnedType" NOT NULL,
    "owned_id" BIGINT NOT NULL,
    "relationship" "CircleRelationship" NOT NULL,
    "source_enquiry_id" BIGINT,
    "sequence_date" DATE,
    "added_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "circles_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "response_types" (
    "id" BIGSERIAL NOT NULL,
    "name" TEXT NOT NULL,
    "slug" TEXT NOT NULL,
    "description" TEXT,

    CONSTRAINT "response_types_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "response_fields" (
    "id" BIGSERIAL NOT NULL,
    "response_type_id" BIGINT NOT NULL,
    "field_name" TEXT NOT NULL,
    "field_type" TEXT NOT NULL,
    "is_required" BOOLEAN NOT NULL DEFAULT false,
    "placeholder" TEXT,
    "description" TEXT,
    "order" INTEGER NOT NULL DEFAULT 0,

    CONSTRAINT "response_fields_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "responses" (
    "id" BIGSERIAL NOT NULL,
    "response_type_id" BIGINT NOT NULL,
    "user_id" BIGINT,
    "data" JSONB NOT NULL,
    "status" TEXT NOT NULL DEFAULT 'pending',
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "responses_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "memories" (
    "id" BIGSERIAL NOT NULL,
    "user_id" BIGINT NOT NULL,
    "postcard_id" BIGINT,
    "collection_id" BIGINT,
    "name" TEXT NOT NULL,
    "slug" TEXT NOT NULL,
    "intro" TEXT,
    "memory_date" DATE,
    "country_id" BIGINT,
    "region_id" BIGINT,
    "locality_id" BIGINT,
    "external_url" TEXT,
    "internal_url" TEXT,
    "signature" TEXT,
    "share_type" "ShareType" NOT NULL DEFAULT 'private',
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "memories_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "user_events" (
    "id" BIGSERIAL NOT NULL,
    "user_id" BIGINT,
    "event_type" "UserEventType" NOT NULL,
    "subject_type" "EventSubjectType",
    "subject_id" BIGINT,
    "search_query" TEXT,
    "metadata" JSONB,
    "occurred_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "user_events_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "user_personas" (
    "id" BIGSERIAL NOT NULL,
    "user_id" BIGINT NOT NULL,
    "price_affinity" "PriceAffinity",
    "last_computed_at" TIMESTAMP(3),

    CONSTRAINT "user_personas_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "user_persona_tags" (
    "user_id" BIGINT NOT NULL,
    "tag_id" BIGINT NOT NULL,
    "weight" DECIMAL(6,4) NOT NULL,
    "updated_at" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "user_persona_tags_pkey" PRIMARY KEY ("user_id","tag_id")
);

-- CreateTable
CREATE TABLE "media" (
    "id" BIGSERIAL NOT NULL,
    "legacy_id" BIGINT,
    "url" TEXT NOT NULL,
    "name" TEXT,
    "alt" TEXT,
    "caption" TEXT,
    "mime_type" TEXT,
    "ext" TEXT,
    "hash" TEXT,
    "size" DECIMAL(14,2),
    "provider" TEXT,
    "preview_url" TEXT,
    "provider_metadata" JSONB,
    "width" INTEGER,
    "height" INTEGER,

    CONSTRAINT "media_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "enquiries" (
    "id" BIGSERIAL NOT NULL,
    "user_id" BIGINT NOT NULL,
    "subject_type" "EnquirySubjectType" NOT NULL,
    "subject_id" BIGINT NOT NULL,
    "start_date" DATE,
    "end_date" DATE,
    "number_of_travelers" INTEGER,
    "message" TEXT,
    "status" "EnquiryStatus" NOT NULL DEFAULT 'new',
    "assigned_to_user_id" BIGINT,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "enquiries_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "_MemoryTaggedUsers" (
    "A" BIGINT NOT NULL,
    "B" BIGINT NOT NULL,

    CONSTRAINT "_MemoryTaggedUsers_AB_pkey" PRIMARY KEY ("A","B")
);

-- CreateTable
CREATE TABLE "_MemoryGallery" (
    "A" BIGINT NOT NULL,
    "B" BIGINT NOT NULL,

    CONSTRAINT "_MemoryGallery_AB_pkey" PRIMARY KEY ("A","B")
);

-- CreateIndex
CREATE UNIQUE INDEX "collection_types_slug_key" ON "collection_types"("slug");

-- CreateIndex
CREATE UNIQUE INDEX "collections_slug_key" ON "collections"("slug");

-- CreateIndex
CREATE INDEX "collections_collection_type_id_idx" ON "collections"("collection_type_id");

-- CreateIndex
CREATE INDEX "collections_country_id_region_id_locality_id_idx" ON "collections"("country_id", "region_id", "locality_id");

-- CreateIndex
CREATE INDEX "collections_owner_user_id_idx" ON "collections"("owner_user_id");

-- CreateIndex
CREATE UNIQUE INDEX "postcards_slug_key" ON "postcards"("slug");

-- CreateIndex
CREATE INDEX "postcards_collection_id_idx" ON "postcards"("collection_id");

-- CreateIndex
CREATE INDEX "postcards_collection_type_id_idx" ON "postcards"("collection_type_id");

-- CreateIndex
CREATE INDEX "postcards_user_id_idx" ON "postcards"("user_id");

-- CreateIndex
CREATE INDEX "postcards_country_id_region_id_locality_id_idx" ON "postcards"("country_id", "region_id", "locality_id");

-- CreateIndex
CREATE UNIQUE INDEX "subcollection_types_slug_key" ON "subcollection_types"("slug");

-- CreateIndex
CREATE UNIQUE INDEX "subcollections_slug_key" ON "subcollections"("slug");

-- CreateIndex
CREATE INDEX "subcollections_collection_id_idx" ON "subcollections"("collection_id");

-- CreateIndex
CREATE INDEX "subcollections_created_by_user_id_idx" ON "subcollections"("created_by_user_id");

-- CreateIndex
CREATE INDEX "subcollection_postcards_subcollection_id_sequence_order_idx" ON "subcollection_postcards"("subcollection_id", "sequence_order");

-- CreateIndex
CREATE UNIQUE INDEX "collection_cluster_types_slug_key" ON "collection_cluster_types"("slug");

-- CreateIndex
CREATE UNIQUE INDEX "collection_clusters_slug_key" ON "collection_clusters"("slug");

-- CreateIndex
CREATE INDEX "collection_clusters_cluster_type_id_idx" ON "collection_clusters"("cluster_type_id");

-- CreateIndex
CREATE INDEX "collection_clusters_region_id_idx" ON "collection_clusters"("region_id");

-- CreateIndex
CREATE UNIQUE INDEX "countries_name_key" ON "countries"("name");

-- CreateIndex
CREATE UNIQUE INDEX "countries_slug_key" ON "countries"("slug");

-- CreateIndex
CREATE UNIQUE INDEX "regions_name_country_id_key" ON "regions"("name", "country_id");

-- CreateIndex
CREATE UNIQUE INDEX "localities_google_place_id_key" ON "localities"("google_place_id");

-- CreateIndex
CREATE UNIQUE INDEX "localities_name_region_id_key" ON "localities"("name", "region_id");

-- CreateIndex
CREATE UNIQUE INDEX "facet_types_slug_key" ON "facet_types"("slug");

-- CreateIndex
CREATE UNIQUE INDEX "facet_values_facet_type_id_slug_key" ON "facet_values"("facet_type_id", "slug");

-- CreateIndex
CREATE INDEX "facet_assignments_owned_type_owned_id_idx" ON "facet_assignments"("owned_type", "owned_id");

-- CreateIndex
CREATE UNIQUE INDEX "facet_assignments_owned_type_owned_id_facet_value_id_key" ON "facet_assignments"("owned_type", "owned_id", "facet_value_id");

-- CreateIndex
CREATE UNIQUE INDEX "tags_name_key" ON "tags"("name");

-- CreateIndex
CREATE UNIQUE INDEX "tags_slug_key" ON "tags"("slug");

-- CreateIndex
CREATE UNIQUE INDEX "companies_slug_key" ON "companies"("slug");

-- CreateIndex
CREATE UNIQUE INDEX "user_types_slug_key" ON "user_types"("slug");

-- CreateIndex
CREATE UNIQUE INDEX "users_username_key" ON "users"("username");

-- CreateIndex
CREATE UNIQUE INDEX "users_email_key" ON "users"("email");

-- CreateIndex
CREATE UNIQUE INDEX "users_slug_key" ON "users"("slug");

-- CreateIndex
CREATE INDEX "memberships_user_id_status_idx" ON "memberships"("user_id", "status");

-- CreateIndex
CREATE INDEX "user_roles_user_id_idx" ON "user_roles"("user_id");

-- CreateIndex
CREATE INDEX "user_roles_company_id_idx" ON "user_roles"("company_id");

-- CreateIndex
CREATE UNIQUE INDEX "user_roles_user_id_user_type_id_key" ON "user_roles"("user_id", "user_type_id");

-- CreateIndex
CREATE INDEX "circles_user_id_owned_type_idx" ON "circles"("user_id", "owned_type");

-- CreateIndex
CREATE INDEX "circles_user_id_relationship_owned_type_idx" ON "circles"("user_id", "relationship", "owned_type");

-- CreateIndex
CREATE INDEX "circles_owned_type_owned_id_idx" ON "circles"("owned_type", "owned_id");

-- CreateIndex
CREATE UNIQUE INDEX "circles_user_id_owned_type_owned_id_relationship_key" ON "circles"("user_id", "owned_type", "owned_id", "relationship");

-- CreateIndex
CREATE UNIQUE INDEX "response_types_name_key" ON "response_types"("name");

-- CreateIndex
CREATE UNIQUE INDEX "response_types_slug_key" ON "response_types"("slug");

-- CreateIndex
CREATE UNIQUE INDEX "response_fields_response_type_id_field_name_key" ON "response_fields"("response_type_id", "field_name");

-- CreateIndex
CREATE INDEX "responses_response_type_id_idx" ON "responses"("response_type_id");

-- CreateIndex
CREATE INDEX "responses_user_id_created_at_idx" ON "responses"("user_id", "created_at");

-- CreateIndex
CREATE UNIQUE INDEX "memories_slug_key" ON "memories"("slug");

-- CreateIndex
CREATE INDEX "memories_user_id_idx" ON "memories"("user_id");

-- CreateIndex
CREATE INDEX "memories_postcard_id_idx" ON "memories"("postcard_id");

-- CreateIndex
CREATE INDEX "memories_collection_id_idx" ON "memories"("collection_id");

-- CreateIndex
CREATE INDEX "user_events_user_id_occurred_at_idx" ON "user_events"("user_id", "occurred_at");

-- CreateIndex
CREATE INDEX "user_events_event_type_occurred_at_idx" ON "user_events"("event_type", "occurred_at");

-- CreateIndex
CREATE INDEX "user_events_subject_type_subject_id_idx" ON "user_events"("subject_type", "subject_id");

-- CreateIndex
CREATE UNIQUE INDEX "user_personas_user_id_key" ON "user_personas"("user_id");

-- CreateIndex
CREATE INDEX "user_persona_tags_tag_id_weight_idx" ON "user_persona_tags"("tag_id", "weight");

-- CreateIndex
CREATE UNIQUE INDEX "media_legacy_id_key" ON "media"("legacy_id");

-- CreateIndex
CREATE INDEX "media_url_idx" ON "media"("url");

-- CreateIndex
CREATE INDEX "enquiries_user_id_idx" ON "enquiries"("user_id");

-- CreateIndex
CREATE INDEX "enquiries_subject_type_subject_id_idx" ON "enquiries"("subject_type", "subject_id");

-- CreateIndex
CREATE INDEX "enquiries_assigned_to_user_id_idx" ON "enquiries"("assigned_to_user_id");

-- CreateIndex
CREATE INDEX "_MemoryTaggedUsers_B_index" ON "_MemoryTaggedUsers"("B");

-- CreateIndex
CREATE INDEX "_MemoryGallery_B_index" ON "_MemoryGallery"("B");

-- AddForeignKey
ALTER TABLE "collections" ADD CONSTRAINT "collections_collection_type_id_fkey" FOREIGN KEY ("collection_type_id") REFERENCES "collection_types"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "collections" ADD CONSTRAINT "collections_cover_media_id_fkey" FOREIGN KEY ("cover_media_id") REFERENCES "media"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "collections" ADD CONSTRAINT "collections_country_id_fkey" FOREIGN KEY ("country_id") REFERENCES "countries"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "collections" ADD CONSTRAINT "collections_region_id_fkey" FOREIGN KEY ("region_id") REFERENCES "regions"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "collections" ADD CONSTRAINT "collections_locality_id_fkey" FOREIGN KEY ("locality_id") REFERENCES "localities"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "collections" ADD CONSTRAINT "collections_managed_by_company_id_fkey" FOREIGN KEY ("managed_by_company_id") REFERENCES "companies"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "collections" ADD CONSTRAINT "collections_owner_user_id_fkey" FOREIGN KEY ("owner_user_id") REFERENCES "users"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "collections" ADD CONSTRAINT "collections_assigned_to_user_id_fkey" FOREIGN KEY ("assigned_to_user_id") REFERENCES "users"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "postcards" ADD CONSTRAINT "postcards_collection_type_id_fkey" FOREIGN KEY ("collection_type_id") REFERENCES "collection_types"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "postcards" ADD CONSTRAINT "postcards_collection_id_fkey" FOREIGN KEY ("collection_id") REFERENCES "collections"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "postcards" ADD CONSTRAINT "postcards_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "postcards" ADD CONSTRAINT "postcards_cover_media_id_fkey" FOREIGN KEY ("cover_media_id") REFERENCES "media"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "postcards" ADD CONSTRAINT "postcards_country_id_fkey" FOREIGN KEY ("country_id") REFERENCES "countries"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "postcards" ADD CONSTRAINT "postcards_region_id_fkey" FOREIGN KEY ("region_id") REFERENCES "regions"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "postcards" ADD CONSTRAINT "postcards_locality_id_fkey" FOREIGN KEY ("locality_id") REFERENCES "localities"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "subcollection_types" ADD CONSTRAINT "subcollection_types_collection_type_id_fkey" FOREIGN KEY ("collection_type_id") REFERENCES "collection_types"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "subcollections" ADD CONSTRAINT "subcollections_subcollection_type_id_fkey" FOREIGN KEY ("subcollection_type_id") REFERENCES "subcollection_types"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "subcollections" ADD CONSTRAINT "subcollections_collection_id_fkey" FOREIGN KEY ("collection_id") REFERENCES "collections"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "subcollections" ADD CONSTRAINT "subcollections_cover_media_id_fkey" FOREIGN KEY ("cover_media_id") REFERENCES "media"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "subcollections" ADD CONSTRAINT "subcollections_managed_by_company_id_fkey" FOREIGN KEY ("managed_by_company_id") REFERENCES "companies"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "subcollections" ADD CONSTRAINT "subcollections_created_by_user_id_fkey" FOREIGN KEY ("created_by_user_id") REFERENCES "users"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "subcollection_postcards" ADD CONSTRAINT "subcollection_postcards_subcollection_id_fkey" FOREIGN KEY ("subcollection_id") REFERENCES "subcollections"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "subcollection_postcards" ADD CONSTRAINT "subcollection_postcards_postcard_id_fkey" FOREIGN KEY ("postcard_id") REFERENCES "postcards"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "collection_clusters" ADD CONSTRAINT "collection_clusters_cluster_type_id_fkey" FOREIGN KEY ("cluster_type_id") REFERENCES "collection_cluster_types"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "collection_clusters" ADD CONSTRAINT "collection_clusters_cover_media_id_fkey" FOREIGN KEY ("cover_media_id") REFERENCES "media"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "collection_clusters" ADD CONSTRAINT "collection_clusters_country_id_fkey" FOREIGN KEY ("country_id") REFERENCES "countries"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "collection_clusters" ADD CONSTRAINT "collection_clusters_region_id_fkey" FOREIGN KEY ("region_id") REFERENCES "regions"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "collection_clusters" ADD CONSTRAINT "collection_clusters_managed_by_company_id_fkey" FOREIGN KEY ("managed_by_company_id") REFERENCES "companies"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "countries" ADD CONSTRAINT "countries_flag_media_id_fkey" FOREIGN KEY ("flag_media_id") REFERENCES "media"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "regions" ADD CONSTRAINT "regions_country_id_fkey" FOREIGN KEY ("country_id") REFERENCES "countries"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "localities" ADD CONSTRAINT "localities_region_id_fkey" FOREIGN KEY ("region_id") REFERENCES "regions"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "facet_types" ADD CONSTRAINT "facet_types_applies_to_collection_type_id_fkey" FOREIGN KEY ("applies_to_collection_type_id") REFERENCES "collection_types"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "facet_types" ADD CONSTRAINT "facet_types_applies_to_subcollection_type_id_fkey" FOREIGN KEY ("applies_to_subcollection_type_id") REFERENCES "subcollection_types"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "facet_values" ADD CONSTRAINT "facet_values_facet_type_id_fkey" FOREIGN KEY ("facet_type_id") REFERENCES "facet_types"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "facet_assignments" ADD CONSTRAINT "facet_assignments_facet_value_id_fkey" FOREIGN KEY ("facet_value_id") REFERENCES "facet_values"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "companies" ADD CONSTRAINT "companies_logo_media_id_fkey" FOREIGN KEY ("logo_media_id") REFERENCES "media"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "companies" ADD CONSTRAINT "companies_cover_image_media_id_fkey" FOREIGN KEY ("cover_image_media_id") REFERENCES "media"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "users" ADD CONSTRAINT "users_profile_pic_id_fkey" FOREIGN KEY ("profile_pic_id") REFERENCES "media"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "users" ADD CONSTRAINT "users_cover_image_id_fkey" FOREIGN KEY ("cover_image_id") REFERENCES "media"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "users" ADD CONSTRAINT "users_country_id_fkey" FOREIGN KEY ("country_id") REFERENCES "countries"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "users" ADD CONSTRAINT "users_region_id_fkey" FOREIGN KEY ("region_id") REFERENCES "regions"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "users" ADD CONSTRAINT "users_locality_id_fkey" FOREIGN KEY ("locality_id") REFERENCES "localities"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "memberships" ADD CONSTRAINT "memberships_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "user_roles" ADD CONSTRAINT "user_roles_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "user_roles" ADD CONSTRAINT "user_roles_user_type_id_fkey" FOREIGN KEY ("user_type_id") REFERENCES "user_types"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "user_roles" ADD CONSTRAINT "user_roles_company_id_fkey" FOREIGN KEY ("company_id") REFERENCES "companies"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "user_roles" ADD CONSTRAINT "user_roles_manager_user_id_fkey" FOREIGN KEY ("manager_user_id") REFERENCES "users"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "circles" ADD CONSTRAINT "circles_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "circles" ADD CONSTRAINT "circles_source_enquiry_id_fkey" FOREIGN KEY ("source_enquiry_id") REFERENCES "enquiries"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "response_fields" ADD CONSTRAINT "response_fields_response_type_id_fkey" FOREIGN KEY ("response_type_id") REFERENCES "response_types"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "responses" ADD CONSTRAINT "responses_response_type_id_fkey" FOREIGN KEY ("response_type_id") REFERENCES "response_types"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "responses" ADD CONSTRAINT "responses_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "memories" ADD CONSTRAINT "memories_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "memories" ADD CONSTRAINT "memories_postcard_id_fkey" FOREIGN KEY ("postcard_id") REFERENCES "postcards"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "memories" ADD CONSTRAINT "memories_collection_id_fkey" FOREIGN KEY ("collection_id") REFERENCES "collections"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "memories" ADD CONSTRAINT "memories_country_id_fkey" FOREIGN KEY ("country_id") REFERENCES "countries"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "memories" ADD CONSTRAINT "memories_region_id_fkey" FOREIGN KEY ("region_id") REFERENCES "regions"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "memories" ADD CONSTRAINT "memories_locality_id_fkey" FOREIGN KEY ("locality_id") REFERENCES "localities"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "user_events" ADD CONSTRAINT "user_events_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "user_personas" ADD CONSTRAINT "user_personas_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "user_persona_tags" ADD CONSTRAINT "user_persona_tags_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "user_persona_tags" ADD CONSTRAINT "user_persona_tags_tag_id_fkey" FOREIGN KEY ("tag_id") REFERENCES "tags"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "enquiries" ADD CONSTRAINT "enquiries_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "enquiries" ADD CONSTRAINT "enquiries_assigned_to_user_id_fkey" FOREIGN KEY ("assigned_to_user_id") REFERENCES "users"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "_MemoryTaggedUsers" ADD CONSTRAINT "_MemoryTaggedUsers_A_fkey" FOREIGN KEY ("A") REFERENCES "memories"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "_MemoryTaggedUsers" ADD CONSTRAINT "_MemoryTaggedUsers_B_fkey" FOREIGN KEY ("B") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "_MemoryGallery" ADD CONSTRAINT "_MemoryGallery_A_fkey" FOREIGN KEY ("A") REFERENCES "media"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "_MemoryGallery" ADD CONSTRAINT "_MemoryGallery_B_fkey" FOREIGN KEY ("B") REFERENCES "memories"("id") ON DELETE CASCADE ON UPDATE CASCADE;

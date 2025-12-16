/*
  Warnings:

  - You are about to alter the column `event_type` on the `webhook_deliveries` table. The data in that column could be lost. The data in that column will be cast from `VarChar(100)` to `VarChar(50)`.
  - You are about to alter the column `action` on the `webhook_deliveries` table. The data in that column could be lost. The data in that column will be cast from `VarChar(100)` to `VarChar(50)`.
  - You are about to alter the column `repository_id` on the `webhook_deliveries` table. The data in that column could be lost. The data in that column will be cast from `Text` to `VarChar(255)`.
  - A unique constraint covering the columns `[fingerprint]` on the table `webhook_deliveries` will be added. If there are existing duplicate values, this will fail.
  - Added the required column `action` to the `pr_reviews` table without a default value. This is not possible if the table is not empty.

*/
-- DropIndex
DROP INDEX "webhook_deliveries_received_at_idx";

-- AlterTable
ALTER TABLE "point_transactions" ADD COLUMN     "transaction_type" VARCHAR(50) NOT NULL DEFAULT 'AWARD';

-- AlterTable
ALTER TABLE "pr_reviews" ADD COLUMN     "action" VARCHAR(50) NOT NULL,
ADD COLUMN     "internal_comment" TEXT,
ADD COLUMN     "is_conflicting" BOOLEAN NOT NULL DEFAULT false,
ADD COLUMN     "resolved_by" TEXT;

-- AlterTable
ALTER TABLE "pull_requests" ADD COLUMN     "approved_at" TIMESTAMP(3),
ADD COLUMN     "last_synced_at" TIMESTAMP(3),
ADD COLUMN     "reviewed_at" TIMESTAMP(3),
ADD COLUMN     "scoring_metadata" JSONB;

-- AlterTable
ALTER TABLE "webhook_deliveries" ADD COLUMN     "fingerprint" VARCHAR(255),
ADD COLUMN     "pr_id" TEXT,
ADD COLUMN     "scoring_applied" BOOLEAN NOT NULL DEFAULT false,
ALTER COLUMN "delivery_id" SET DATA TYPE TEXT,
ALTER COLUMN "event_type" SET DATA TYPE VARCHAR(50),
ALTER COLUMN "action" SET DATA TYPE VARCHAR(50),
ALTER COLUMN "repository_id" SET DATA TYPE VARCHAR(255);

-- CreateTable
CREATE TABLE "review_comments" (
    "id" TEXT NOT NULL,
    "pull_request_id" TEXT NOT NULL,
    "reviewer_id" TEXT NOT NULL,
    "comment" TEXT NOT NULL,
    "is_internal" BOOLEAN NOT NULL DEFAULT true,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "review_comments_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "review_conflicts" (
    "id" TEXT NOT NULL,
    "pull_request_id" TEXT NOT NULL,
    "conflicting_reviews" JSONB NOT NULL,
    "resolution_method" VARCHAR(50),
    "final_outcome" VARCHAR(50),
    "resolved_by" TEXT,
    "resolved_at" TIMESTAMP(3),
    "is_resolved" BOOLEAN NOT NULL DEFAULT false,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "review_conflicts_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE INDEX "review_comments_pull_request_id_idx" ON "review_comments"("pull_request_id");

-- CreateIndex
CREATE INDEX "review_comments_reviewer_id_idx" ON "review_comments"("reviewer_id");

-- CreateIndex
CREATE INDEX "review_conflicts_pull_request_id_idx" ON "review_conflicts"("pull_request_id");

-- CreateIndex
CREATE INDEX "review_conflicts_is_resolved_idx" ON "review_conflicts"("is_resolved");

-- CreateIndex
CREATE INDEX "point_transactions_transaction_type_idx" ON "point_transactions"("transaction_type");

-- CreateIndex
CREATE INDEX "pr_reviews_action_idx" ON "pr_reviews"("action");

-- CreateIndex
CREATE INDEX "pr_reviews_is_conflicting_idx" ON "pr_reviews"("is_conflicting");

-- CreateIndex
CREATE UNIQUE INDEX "webhook_deliveries_fingerprint_key" ON "webhook_deliveries"("fingerprint");

-- CreateIndex
CREATE INDEX "webhook_deliveries_fingerprint_idx" ON "webhook_deliveries"("fingerprint");

-- CreateIndex
CREATE INDEX "webhook_deliveries_pr_id_idx" ON "webhook_deliveries"("pr_id");

-- AddForeignKey
ALTER TABLE "review_comments" ADD CONSTRAINT "review_comments_pull_request_id_fkey" FOREIGN KEY ("pull_request_id") REFERENCES "pull_requests"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "review_comments" ADD CONSTRAINT "review_comments_reviewer_id_fkey" FOREIGN KEY ("reviewer_id") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;

/*
  Warnings:

  - Added the required column `updated_at` to the `badges` table without a default value. This is not possible if the table is not empty.

*/
-- AlterTable
ALTER TABLE "badges" ADD COLUMN     "category" VARCHAR(50) NOT NULL DEFAULT 'MILESTONE',
ADD COLUMN     "is_active" BOOLEAN NOT NULL DEFAULT true,
ADD COLUMN     "rarity" VARCHAR(20) NOT NULL DEFAULT 'COMMON',
ADD COLUMN     "updated_at" TIMESTAMP(3) NOT NULL,
ADD COLUMN     "version" INTEGER NOT NULL DEFAULT 1;

-- AlterTable
ALTER TABLE "projects" ADD COLUMN     "scoring_rules" JSONB,
ADD COLUMN     "userId" TEXT;

-- AlterTable
ALTER TABLE "user_badges" ADD COLUMN     "awarded_by" TEXT,
ADD COLUMN     "is_manual" BOOLEAN NOT NULL DEFAULT false,
ADD COLUMN     "metadata" JSONB;

-- CreateTable
CREATE TABLE "badge_audit_logs" (
    "id" TEXT NOT NULL,
    "user_id" TEXT NOT NULL,
    "badge_id" TEXT NOT NULL,
    "action" VARCHAR(50) NOT NULL,
    "awarded_by" TEXT,
    "is_manual" BOOLEAN NOT NULL DEFAULT false,
    "justification" TEXT,
    "metadata" JSONB,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "badge_audit_logs_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "rank_snapshots" (
    "id" TEXT NOT NULL,
    "user_id" TEXT NOT NULL,
    "leaderboard_type" VARCHAR(50) NOT NULL,
    "rank" INTEGER NOT NULL,
    "total_points" INTEGER NOT NULL,
    "period" VARCHAR(50),
    "snapshot_at" TIMESTAMP(3) NOT NULL,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "rank_snapshots_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "leaderboard_snapshots" (
    "id" TEXT NOT NULL,
    "leaderboard_type" VARCHAR(50) NOT NULL,
    "period" VARCHAR(50),
    "top_users" JSONB NOT NULL,
    "snapshot_at" TIMESTAMP(3) NOT NULL,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "leaderboard_snapshots_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE INDEX "badge_audit_logs_user_id_idx" ON "badge_audit_logs"("user_id");

-- CreateIndex
CREATE INDEX "badge_audit_logs_badge_id_idx" ON "badge_audit_logs"("badge_id");

-- CreateIndex
CREATE INDEX "badge_audit_logs_action_idx" ON "badge_audit_logs"("action");

-- CreateIndex
CREATE INDEX "badge_audit_logs_created_at_idx" ON "badge_audit_logs"("created_at");

-- CreateIndex
CREATE INDEX "rank_snapshots_user_id_idx" ON "rank_snapshots"("user_id");

-- CreateIndex
CREATE INDEX "rank_snapshots_leaderboard_type_idx" ON "rank_snapshots"("leaderboard_type");

-- CreateIndex
CREATE INDEX "rank_snapshots_period_idx" ON "rank_snapshots"("period");

-- CreateIndex
CREATE INDEX "rank_snapshots_snapshot_at_idx" ON "rank_snapshots"("snapshot_at");

-- CreateIndex
CREATE INDEX "leaderboard_snapshots_leaderboard_type_idx" ON "leaderboard_snapshots"("leaderboard_type");

-- CreateIndex
CREATE INDEX "leaderboard_snapshots_period_idx" ON "leaderboard_snapshots"("period");

-- CreateIndex
CREATE INDEX "leaderboard_snapshots_snapshot_at_idx" ON "leaderboard_snapshots"("snapshot_at");

-- CreateIndex
CREATE INDEX "badges_rarity_idx" ON "badges"("rarity");

-- CreateIndex
CREATE INDEX "badges_category_idx" ON "badges"("category");

-- CreateIndex
CREATE INDEX "badges_is_active_idx" ON "badges"("is_active");

-- CreateIndex
CREATE INDEX "user_badges_is_manual_idx" ON "user_badges"("is_manual");

-- AddForeignKey
ALTER TABLE "projects" ADD CONSTRAINT "projects_userId_fkey" FOREIGN KEY ("userId") REFERENCES "users"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "badge_audit_logs" ADD CONSTRAINT "badge_audit_logs_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "rank_snapshots" ADD CONSTRAINT "rank_snapshots_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;

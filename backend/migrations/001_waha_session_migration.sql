-- Migration: Remove ghl_team_id and rename whatsapp_channel_id to waha_session_id
-- WhatsApp Campaign Interface Improvements

-- Step 1: Add new waha_session_id column
ALTER TABLE campaigns ADD COLUMN waha_session_id VARCHAR(50);

-- Step 2: Copy data from whatsapp_channel_id to waha_session_id (if whatsapp_channel_id exists)
-- UPDATE campaigns SET waha_session_id = whatsapp_channel_id WHERE whatsapp_channel_id IS NOT NULL;

-- Step 3: Set waha_session_id as NOT NULL and add index
ALTER TABLE campaigns ALTER COLUMN waha_session_id SET NOT NULL;
CREATE INDEX idx_campaigns_session_status ON campaigns(waha_session_id, status);

-- Step 4: Drop old columns (if they exist)
-- ALTER TABLE campaigns DROP COLUMN IF EXISTS ghl_team_id;
-- ALTER TABLE campaigns DROP COLUMN IF EXISTS whatsapp_channel_id;

-- Step 5: Drop old indexes (if they exist)
-- DROP INDEX IF EXISTS idx_campaigns_channel_status;

-- Note: Run this migration carefully in production.
-- Test with sample data first and backup the database.
-- Migration: Add interview status tracking to interview_sessions table
-- Date: 2026-06-03
-- Purpose: Support interview workflow improvements (Change 4)

-- Add interview_status column if it doesn't exist
ALTER TABLE interview_sessions 
ADD COLUMN IF NOT EXISTS interview_status VARCHAR(20) DEFAULT 'PENDING';

-- Add timestamp columns if they don't exist
ALTER TABLE interview_sessions 
ADD COLUMN IF NOT EXISTS invited_at DATETIME;

ALTER TABLE interview_sessions 
ADD COLUMN IF NOT EXISTS started_at DATETIME;

-- Update existing records to set invited_at from created_at
UPDATE interview_sessions 
SET invited_at = created_at 
WHERE invited_at IS NULL AND created_at IS NOT NULL;

-- Create index for faster status queries
CREATE INDEX IF NOT EXISTS idx_interview_status 
ON interview_sessions(interview_status);

CREATE INDEX IF NOT EXISTS idx_interview_candidate 
ON interview_sessions(candidate_id);

CREATE INDEX IF NOT EXISTS idx_interview_job 
ON interview_sessions(job_id);

-- Comment: Status values are:
-- - PENDING: Session created, candidate not started yet
-- - IN_PROGRESS: Candidate has started answering questions
-- - COMPLETED: All questions answered, interview finished
-- - EXPIRED: Deadline passed without completion

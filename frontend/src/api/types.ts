export type MasteryLevel = "none" | "beginner" | "intermediate" | "advanced"

export interface StudentSkill {
  skill_id: string
  name: string
  level: MasteryLevel
  depth_score: number
  evidence: string
}

export interface ResumeReviewResult {
  strengths: string[]
  weaknesses: string[]
  formatting_feedback: string
  overall_impression: string
}

export interface StudentProfile {
  raw_text: string
  skills: StudentSkill[]
  education: string
  interests: string[]
  hours_per_week: number
  target_role: string
}

export interface SkillDemand {
  skill_id: string
  name: string
  frequency: number
  share: number
  posting_ids: string[]
}

export interface MarketDemandProfile {
  target_role: string
  postings_analysed: number
  skills: SkillDemand[]
}

export interface SkillGap {
  skill_id: string
  name: string
  demand_share: number
  current_level: MasteryLevel
  required_level: MasteryLevel
  gap_size: number
  priority: number
}

export interface GapReport {
  target_role: string
  gaps: SkillGap[]
  strengths: string[]
}

export interface PathResource {
  course_id: string
  title: string
  provider: string
  url: string
  free: boolean
}

export interface PathStep {
  order: number
  skill_id: string
  skill_name: string
  objective: string
  resources: PathResource[]
  estimated_weeks: number
  milestone: string
}

export interface LearningPath {
  target_role: string
  steps: PathStep[]
  total_weeks: number
  rationale: string
}

export interface FGCRCritique {
  feasibility: number
  groundedness: number
  coverage: number
  realism: number
  passed: boolean
  issues: string[]
  revision_request: string
}

export interface AdvisorResult {
  profile: StudentProfile
  demand: MarketDemandProfile
  gap_report: GapReport
  path: LearningPath | null
  critique: FGCRCritique | null
  resume_review: ResumeReviewResult | null
  revisions_used: number
  notes: string[]
}

export interface AdviseRequest {
  resume_text: string
  target_role: string
  hours_per_week: number
  education: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
}

export type TrackerStepStatus = "pending" | "in_progress" | "struggling" | "completed"

export interface TrackerStepGithubEvidence {
  repo_name: string
  last_pushed_at: string | null
}

export interface TrackerStep {
  id: number
  order: number
  skill_id: string
  skill_name: string
  objective: string
  milestone: string
  estimated_weeks: number
  status: TrackerStepStatus
  quiz_score: number | null
  confidence_rating: number | null
  time_spent_minutes: number
  resources: PathResource[]
  github_evidence: TrackerStepGithubEvidence[]
}

export interface Journey {
  id: number
  target_role: string
  created_at: string
  hours_per_week: number
  steps: TrackerStep[]
}

export interface CompetencyHistoryEntry {
  depth_score: number
  quiz_score: number | null
  confidence_rating: number | null
  has_github_evidence: boolean
  rationale: string
  recorded_at: string
}

export type CompetencyHistory = Record<string, CompetencyHistoryEntry[]>

export interface ProgressUpdate {
  quiz_score?: number | null
  confidence_rating?: number | null
  minutes_delta?: number
}

export interface QuizQuestion {
  question: string
  options: string[]
}

export interface AnalyzedRepo {
  username: string
  repo_name: string
  file_count: number
  analyzed_at: string
}

export interface JobRecommendation {
  posting_id: string
  title: string
  company: string
  location: string
  url: string
  score: number
  matched_skills: string[]
}

export interface InterviewTips {
  role: string
  focus_topics: string[]
  common_questions: string[]
  advice: string
}

export interface LeetcodeSummary {
  username: string
  easy: number
  medium: number
  hard: number
  total: number
  dsa_depth: number | null
  weak_topics: string[]
  last_accepted_at: string | null
  synced_at: string | null
}

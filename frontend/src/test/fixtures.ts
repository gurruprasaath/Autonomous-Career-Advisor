import type { AdvisorResult } from '../api/types'

export const ADVISOR_RESULT_FIXTURE: AdvisorResult = {
  profile: { raw_text: 'x', skills: [], education: '', interests: [], hours_per_week: 10, target_role: 'Data Engineer' },
  demand: { target_role: 'Data Engineer', postings_analysed: 0, skills: [] },
  gap_report: { target_role: 'Data Engineer', gaps: [], strengths: [] },
  path: null,
  critique: null,
  resume_review: null,
  revisions_used: 0,
  notes: [],
}

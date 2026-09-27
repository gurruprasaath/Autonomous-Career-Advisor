import type { Subtopic } from '../api/types'

const LEVEL_LABEL: Record<Subtopic['level'], string> = {
  beginner: 'Beginner',
  intermediate: 'Intermediate',
  advanced: 'Advanced',
}

export default function SubtopicList({ subtopics, roadmapUrl }: { subtopics: Subtopic[]; roadmapUrl: string }) {
  if (subtopics.length === 0 && !roadmapUrl) return null
  return (
    <div className="subtopics">
      {subtopics.length > 0 && (
        <ol className="subtopic-list">
          {subtopics.map((t) => (
            <li key={t.id}>
              {t.name} <span className={`tag level-${t.level}`}>{LEVEL_LABEL[t.level]}</span>
            </li>
          ))}
        </ol>
      )}
      {roadmapUrl && (
        <a className="resource" href={roadmapUrl} target="_blank" rel="noreferrer">
          🗺 See on roadmap.sh ↗
        </a>
      )}
    </div>
  )
}

export function CurriculumAttribution() {
  return (
    <p className="hint">
      Curriculum data: ESCO (CC BY 4.0), OSSU (MIT), Coding Interview University (CC BY-SA 4.0), Microsoft Learn
    </p>
  )
}

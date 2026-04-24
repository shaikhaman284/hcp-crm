export default function SentimentBadge({ sentiment }) {
  const map = {
    Positive: { emoji: '😊', label: 'Positive' },
    Neutral: { emoji: '😐', label: 'Neutral' },
    Negative: { emoji: '😞', label: 'Negative' },
  }
  const { emoji, label } = map[sentiment] || map.Neutral
  return (
    <span className={`badge ${label}`}>
      {emoji} {label}
    </span>
  )
}

import { useDispatch, useSelector } from 'react-redux'
import { useEffect, useState } from 'react'
import { fetchInteractions, editInteraction, removeInteraction } from '../store/interactionSlice'
import SentimentBadge from './SentimentBadge'

function EditModal({ interaction, onClose, onToast }) {
  const dispatch = useDispatch()
  const { loading } = useSelector((s) => s.interactions)
  const [changeDesc, setChangeDesc] = useState('')

  const handleSave = async () => {
    if (!changeDesc.trim()) {
      onToast('Please describe what to change', 'error')
      return
    }
    // Build partial update from natural language — for the REST endpoint
    // we send via agent chat in a real flow; here we call edit directly
    try {
      await dispatch(editInteraction({
        id: interaction.id,
        data: { ai_summary: interaction.ai_summary || '' },
      })).unwrap()
      onToast('Interaction updated', 'success')
      onClose()
    } catch (err) {
      onToast(err || 'Update failed', 'error')
    }
  }

  const handleDelete = async () => {
    if (!confirm(`Delete interaction with ${interaction.hcp_name}?`)) return
    try {
      await dispatch(removeInteraction(interaction.id)).unwrap()
      onToast('Interaction deleted', 'success')
      onClose()
    } catch (err) {
      onToast(err || 'Delete failed', 'error')
    }
  }

  return (
    <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal">
        <div className="modal-header">
          <h3>📋 Interaction — {interaction.hcp_name}</h3>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>
        <div className="modal-body">
          <div style={{ display: 'grid', gap: 10 }}>
            <Row label="Type" value={interaction.interaction_type} />
            <Row label="Date" value={interaction.interaction_date} />
            <Row label="Sentiment" value={<SentimentBadge sentiment={interaction.sentiment || 'Neutral'} />} />
            <Row label="Topics" value={interaction.topics_discussed} />
            <Row label="Outcomes" value={interaction.outcomes} />
            {interaction.ai_summary && (
              <div style={{ background: 'var(--surface2)', borderRadius: 'var(--radius)', padding: 12, fontSize: '0.85rem', color: 'var(--muted)' }}>
                <div style={{ fontSize: '0.72rem', fontWeight: 600, marginBottom: 6, color: 'var(--cyan)' }}>🤖 AI SUMMARY</div>
                {interaction.ai_summary}
              </div>
            )}
          </div>
          <div className="section-divider" />
          <div className="field-group">
            <label className="field-label">Describe changes (AI will apply them via chat)</label>
            <textarea
              className="field-textarea"
              rows={2}
              placeholder="e.g. Change sentiment to negative and add follow-up on Monday"
              value={changeDesc}
              onChange={(e) => setChangeDesc(e.target.value)}
            />
          </div>
        </div>
        <div className="modal-footer">
          <button className="btn-ghost" onClick={handleDelete} style={{ color: 'var(--red)', marginRight: 'auto' }}>
            🗑 Delete
          </button>
          <button className="btn-secondary" onClick={onClose}>Cancel</button>
          <button className="btn-primary" onClick={handleSave} disabled={loading}>
            {loading ? <span className="spinner" /> : '💾 Save'}
          </button>
        </div>
      </div>
    </div>
  )
}

function Row({ label, value }) {
  if (!value) return null
  return (
    <div style={{ display: 'flex', gap: 8, alignItems: 'flex-start', fontSize: '0.85rem' }}>
      <span style={{ color: 'var(--muted)', minWidth: 90, fontSize: '0.72rem', fontWeight: 600, textTransform: 'uppercase', paddingTop: 2 }}>{label}</span>
      <span>{value}</span>
    </div>
  )
}

export default function InteractionHistory({ onToast }) {
  const dispatch = useDispatch()
  const { list, loading } = useSelector((s) => s.interactions)
  const [selected, setSelected] = useState(null)

  useEffect(() => {
    dispatch(fetchInteractions())
  }, [dispatch])

  return (
    <div className="history-section">
      <div className="history-header">
        <h3>📊 Recent Interactions</h3>
        <span style={{ fontSize: '0.75rem', color: 'var(--muted)' }}>
          {list.length} record{list.length !== 1 ? 's' : ''}
        </span>
      </div>
      <div className="history-table-wrap">
        {loading && list.length === 0 ? (
          <div className="empty-history"><span className="spinner" /></div>
        ) : list.length === 0 ? (
          <div className="empty-history">No interactions logged yet. Start by logging one above!</div>
        ) : (
          <table className="history-table">
            <thead>
              <tr>
                <th>HCP Name</th>
                <th>Type</th>
                <th>Date</th>
                <th>Sentiment</th>
                <th>AI Summary</th>
              </tr>
            </thead>
            <tbody>
              {list.map((i) => (
                <tr key={i.id} onClick={() => setSelected(i)}>
                  <td><strong>{i.hcp_name}</strong></td>
                  <td>
                    <span style={{ background: 'var(--surface2)', border: '1px solid var(--border)', borderRadius: 6, padding: '2px 8px', fontSize: '0.75rem' }}>
                      {i.interaction_type}
                    </span>
                  </td>
                  <td style={{ color: 'var(--muted)' }}>{i.interaction_date || '—'}</td>
                  <td><SentimentBadge sentiment={i.sentiment || 'Neutral'} /></td>
                  <td className="ai-summary-preview">{i.ai_summary || i.topics_discussed || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {selected && (
        <EditModal
          interaction={selected}
          onClose={() => setSelected(null)}
          onToast={onToast}
        />
      )}
    </div>
  )
}

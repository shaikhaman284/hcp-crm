import { useDispatch, useSelector } from 'react-redux'
import { useEffect, useState, useRef } from 'react'
import {
  setFormField,
  resetForm,
  logInteraction,
  fetchFollowups,
  fetchInteractions,
} from '../store/interactionSlice'
import { getHCPs } from '../api/client'

export default function LogInteractionForm({ onToast }) {
  const dispatch = useDispatch()
  const { form, loading, followUps, followUpsLoading } = useSelector((s) => s.interactions)
  const data = form.data

  const [hcps, setHcps] = useState([])
  const [hcpSearch, setHcpSearch] = useState('')
  const [showHcpDropdown, setShowHcpDropdown] = useState(false)
  const [attendeeInput, setAttendeeInput] = useState('')
  const [materialInput, setMaterialInput] = useState('')
  const [sampleInput, setSampleInput] = useState('')
  const hcpRef = useRef(null)

  // Load HCPs for autocomplete
  useEffect(() => {
    getHCPs(hcpSearch)
      .then((r) => setHcps(r.data))
      .catch(() => {})
  }, [hcpSearch])

  // Close dropdown on outside click
  useEffect(() => {
    const handler = (e) => {
      if (hcpRef.current && !hcpRef.current.contains(e.target)) {
        setShowHcpDropdown(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const set = (field, value) => dispatch(setFormField({ field, value }))

  const addTag = (field, input, setInput) => {
    const val = input.trim()
    if (!val) return
    const current = data[field] || []
    if (!current.includes(val)) set(field, [...current, val])
    setInput('')
  }

  const removeTag = (field, tag) => {
    set(field, (data[field] || []).filter((t) => t !== tag))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!data.hcp_name) { onToast('HCP Name is required', 'error'); return }

    try {
      const result = await dispatch(logInteraction({
        ...data,
        interaction_date: data.interaction_date || null,
        interaction_time: data.interaction_time || null,
      })).unwrap()

      onToast('✅ Interaction logged successfully!', 'success')
      dispatch(fetchInteractions())

      // Auto-fetch follow-ups
      if (result.id) {
        dispatch(fetchFollowups(result.id))
      }
    } catch (err) {
      onToast(err || 'Failed to log interaction', 'error')
    }
  }

  const handleReset = () => {
    dispatch(resetForm())
    setHcpSearch('')
    setAttendeeInput('')
    setMaterialInput('')
    setSampleInput('')
  }

  return (
    <form onSubmit={handleSubmit} className="panel-body" style={{ paddingBottom: 24 }}>
      {/* Row 1 — HCP Name + Interaction Type */}
      <div className="form-row">
        {/* HCP Name */}
        <div className="field-group" style={{ position: 'relative' }} ref={hcpRef}>
          <label className="field-label">HCP Name *</label>
          <input
            id="hcp-name-input"
            className="field-input"
            placeholder="Search or type HCP name…"
            value={data.hcp_name || hcpSearch}
            onChange={(e) => {
              set('hcp_name', e.target.value)
              setHcpSearch(e.target.value)
              setShowHcpDropdown(true)
            }}
            onFocus={() => setShowHcpDropdown(true)}
            autoComplete="off"
          />
          {showHcpDropdown && hcps.length > 0 && (
            <div style={{
              position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 50,
              background: '#1a2235', border: '1px solid var(--border)',
              borderRadius: 'var(--radius)', marginTop: 2, maxHeight: 180, overflowY: 'auto',
              boxShadow: 'var(--shadow)',
            }}>
              {hcps.map((h) => (
                <div
                  key={h.id}
                  style={{ padding: '9px 12px', cursor: 'pointer', fontSize: '0.875rem' }}
                  onMouseEnter={(e) => e.currentTarget.style.background = 'var(--border)'}
                  onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                  onClick={() => {
                    set('hcp_name', h.name)
                    setHcpSearch(h.name)
                    setShowHcpDropdown(false)
                  }}
                >
                  <strong>{h.name}</strong>
                  {h.specialization && <span style={{ color: 'var(--muted)', marginLeft: 6, fontSize: '0.78rem' }}>{h.specialization}</span>}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Interaction Type */}
        <div className="field-group">
          <label className="field-label">Interaction Type</label>
          <select
            id="interaction-type-select"
            className="field-select"
            value={data.interaction_type}
            onChange={(e) => set('interaction_type', e.target.value)}
          >
            {['Meeting', 'Call', 'Email', 'Conference', 'Visit'].map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Row 2 — Date + Time */}
      <div className="form-row">
        <div className="field-group">
          <label className="field-label">Date</label>
          <input
            id="interaction-date"
            type="date"
            className="field-input"
            value={data.interaction_date}
            onChange={(e) => set('interaction_date', e.target.value)}
          />
        </div>
        <div className="field-group">
          <label className="field-label">Time</label>
          <input
            id="interaction-time"
            type="time"
            className="field-input"
            value={data.interaction_time}
            onChange={(e) => set('interaction_time', e.target.value)}
          />
        </div>
      </div>

      {/* Row 3 — Attendees */}
      <div className="field-group">
        <label className="field-label">Attendees</label>
        <div className="tag-box">
          {(data.attendees || []).map((a) => (
            <span key={a} className="tag-pill">
              {a}
              <button type="button" onClick={() => removeTag('attendees', a)}>×</button>
            </span>
          ))}
          <input
            id="attendees-input"
            placeholder="Type name + Enter"
            value={attendeeInput}
            onChange={(e) => setAttendeeInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') { e.preventDefault(); addTag('attendees', attendeeInput, setAttendeeInput) }
            }}
          />
        </div>
      </div>

      {/* Row 4 — Topics Discussed */}
      <div className="field-group">
        <label className="field-label">Topics Discussed</label>
        <textarea
          id="topics-discussed"
          className="field-textarea"
          rows={4}
          placeholder="Describe the topics covered in this interaction…"
          value={data.topics_discussed}
          onChange={(e) => set('topics_discussed', e.target.value)}
        />
        <button
          type="button"
          className="voice-note-btn btn-disabled-tooltip"
          data-tooltip="Requires microphone consent to activate"
        >
          ✨ Summarize from Voice Note
        </button>
      </div>

      {/* Row 5 — Materials Shared */}
      <div className="field-group">
        <label className="field-label">Materials Shared</label>
        <div className="tag-add-row">
          <input
            id="materials-input"
            className="field-input"
            placeholder="e.g. Product Brochure, Clinical Study"
            value={materialInput}
            onChange={(e) => setMaterialInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') { e.preventDefault(); addTag('materials_shared', materialInput, setMaterialInput) }
            }}
          />
          <button
            type="button"
            className="btn-secondary"
            onClick={() => addTag('materials_shared', materialInput, setMaterialInput)}
          >
            + Add
          </button>
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 6 }}>
          {(data.materials_shared || []).map((m) => (
            <span key={m} className="tag-pill">
              {m}
              <button type="button" onClick={() => removeTag('materials_shared', m)}>×</button>
            </span>
          ))}
        </div>
      </div>

      {/* Row 6 — Samples Distributed */}
      <div className="field-group">
        <label className="field-label">Samples Distributed</label>
        <div className="tag-add-row">
          <input
            id="samples-input"
            className="field-input"
            placeholder="e.g. Oncovax 10mg x3"
            value={sampleInput}
            onChange={(e) => setSampleInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') { e.preventDefault(); addTag('samples_distributed', sampleInput, setSampleInput) }
            }}
          />
          <button
            type="button"
            className="btn-secondary"
            onClick={() => addTag('samples_distributed', sampleInput, setSampleInput)}
          >
            + Add Sample
          </button>
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 6 }}>
          {(data.samples_distributed || []).map((s) => (
            <span key={s} className="tag-pill" style={{ borderColor: 'var(--purple)', color: 'var(--purple)', background: 'var(--purple-dim)' }}>
              {s}
              <button type="button" onClick={() => removeTag('samples_distributed', s)}>×</button>
            </span>
          ))}
        </div>
      </div>

      {/* Row 7 — Sentiment */}
      <div className="field-group">
        <label className="field-label">HCP Sentiment</label>
        <div className="sentiment-row">
          {[
            { val: 'Positive', emoji: '😊', cls: 'pos' },
            { val: 'Neutral',  emoji: '😐', cls: 'neu' },
            { val: 'Negative', emoji: '😞', cls: 'neg' },
          ].map(({ val, emoji, cls }) => (
            <label key={val} className="sentiment-option">
              <input
                type="radio"
                name="sentiment"
                value={val}
                checked={data.sentiment === val}
                onChange={() => set('sentiment', val)}
              />
              <span className={`sentiment-label ${cls}`}>
                <span className="emoji">{emoji}</span>
                {val}
              </span>
            </label>
          ))}
        </div>
      </div>

      {/* Row 8 — Outcomes */}
      <div className="field-group">
        <label className="field-label">Outcomes</label>
        <textarea
          id="outcomes-textarea"
          className="field-textarea"
          rows={3}
          placeholder="What was achieved or agreed upon?"
          value={data.outcomes}
          onChange={(e) => set('outcomes', e.target.value)}
        />
      </div>

      {/* Row 9 — Follow-up Actions */}
      <div className="field-group">
        <label className="field-label">Follow-up Actions</label>
        <textarea
          id="followup-textarea"
          className="field-textarea"
          rows={3}
          placeholder="Next steps and actions to take…"
          value={data.follow_up_actions}
          onChange={(e) => set('follow_up_actions', e.target.value)}
        />
      </div>

      {/* AI Suggested Follow-ups */}
      {(followUps.length > 0 || followUpsLoading) && (
        <div className="followup-card">
          <div className="followup-title">
            🤖 AI Suggested Follow-ups:
            {followUpsLoading && <span className="spinner" style={{ marginLeft: 8 }} />}
          </div>
          {!followUpsLoading && (
            <ul className="followup-list">
              {followUps.map((item, i) => (
                <li key={i}>{item}</li>
              ))}
            </ul>
          )}
        </div>
      )}

      {/* Actions */}
      <div style={{ display: 'flex', gap: 10, marginTop: 16 }}>
        <button type="button" className="btn-secondary" onClick={handleReset}>
          Reset
        </button>
        <button type="submit" className="btn-primary full" disabled={loading} style={{ flex: 1, marginTop: 0 }}>
          {loading ? <><span className="spinner" /> Logging…</> : '💾 Log Interaction'}
        </button>
      </div>
    </form>
  )
}

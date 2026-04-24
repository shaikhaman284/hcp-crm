import { useDispatch, useSelector } from 'react-redux'
import { useRef, useEffect, useState } from 'react'
import { addMessage, setLoading, setPopulatedFromChat } from '../store/chatSlice'
import { setFormDataFromChat, fetchInteractions, editInteraction } from '../store/interactionSlice'
import { sendChatMessage } from '../api/client'

function formatTime(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

export default function ChatInterface({ onToast }) {
  const dispatch = useDispatch()
  const { messages, sessionId, loading, populatedFromChat } = useSelector((s) => s.chat)
  const [input, setInput] = useState('')
  const bottomRef = useRef(null)
  const textareaRef = useRef(null)

  // Auto-scroll to latest message
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const handleSend = async () => {
    const text = input.trim()
    if (!text || loading) return
    setInput('')

    dispatch(addMessage({ role: 'user', content: text }))
    dispatch(setLoading(true))

    try {
      const { data } = await sendChatMessage(text, sessionId)
      dispatch(addMessage({ role: 'assistant', content: data.reply }))

      // log_interaction: populate left form panel
      if (data.tool_used === 'log_interaction' && data.extracted_interaction) {
        dispatch(setFormDataFromChat(data.extracted_interaction))
        dispatch(setPopulatedFromChat(true))
        dispatch(fetchInteractions())
        onToast('✅ Form populated from chat', 'info')
        setTimeout(() => dispatch(setPopulatedFromChat(false)), 4000)
      }

      // edit_interaction: sync updated data back to left form panel
      if (data.tool_used === 'edit_interaction' && data.interaction_data) {
        dispatch(setFormDataFromChat(data.interaction_data))
        dispatch(editInteraction({ id: data.interaction_data.id, data: data.interaction_data }))
        dispatch(setPopulatedFromChat(true))
        dispatch(fetchInteractions())
        onToast('✏️ Form updated from chat edit', 'info')
        setTimeout(() => dispatch(setPopulatedFromChat(false)), 4000)
      }
    } catch (err) {
      dispatch(addMessage({ role: 'assistant', content: `❌ Error: ${err.message}` }))
      onToast(err.message, 'error')
    } finally {
      dispatch(setLoading(false))
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && e.ctrlKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <>
      {/* Populated notice */}
      {populatedFromChat && (
        <div className="populated-notice">
          ✅ Form populated from chat interaction data
        </div>
      )}

      {/* Messages */}
      <div className="chat-messages">
        {messages.length === 0 && (
          <div className="chat-placeholder">
            <div className="placeholder-icon">🤖</div>
            <p>
              Log interaction details here (e.g., <em>"Met Dr. Smith, discussed Product X efficacy,
              positive sentiment, shared brochure"</em>) or ask for help.
            </p>
            <div style={{ fontSize: '0.75rem', color: 'var(--muted)', marginTop: 8 }}>
              <div>💡 Try: "Get history for Dr. Shah"</div>
              <div>💡 Try: "Analyze this sentiment: very engaged, ordered samples"</div>
            </div>
          </div>
        )}

        {messages.map((msg) => (
          <div key={msg.id} className={`msg-row ${msg.role === 'user' ? 'user' : 'assistant'}`}>
            <div className="msg-bubble">{msg.content}</div>
            <div className="msg-meta">{formatTime(msg.timestamp)}</div>
          </div>
        ))}

        {loading && (
          <div className="msg-row assistant">
            <div className="msg-bubble" style={{ background: 'var(--border)' }}>
              <div className="typing-indicator">
                <span /><span /><span />
              </div>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input area */}
      <div className="chat-input-area">
        <textarea
          ref={textareaRef}
          id="chat-input"
          rows={2}
          placeholder="Type a message… (Ctrl+Enter to send)"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          style={{ maxHeight: 110 }}
        />
        <button
          id="chat-send-btn"
          className="chat-send-btn"
          onClick={handleSend}
          disabled={loading || !input.trim()}
          title="Send (Ctrl+Enter)"
        >
          ✨
        </button>
      </div>
      <div className="kbd-hint" style={{ padding: '0 16px 8px', textAlign: 'right' }}>
        Ctrl+Enter to send
      </div>
    </>
  )
}

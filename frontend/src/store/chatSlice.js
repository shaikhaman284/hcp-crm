import { createSlice } from '@reduxjs/toolkit'
import { v4 as uuidv4 } from 'uuid'

const chatSlice = createSlice({
  name: 'chat',
  initialState: {
    messages: [],
    sessionId: uuidv4(),
    loading: false,
    populatedFromChat: false,
  },
  reducers: {
    addMessage(state, action) {
      state.messages.push({
        id: uuidv4(),
        role: action.payload.role,
        content: action.payload.content,
        timestamp: new Date().toISOString(),
      })
    },
    setLoading(state, action) {
      state.loading = action.payload
    },
    setPopulatedFromChat(state, action) {
      state.populatedFromChat = action.payload
    },
    clearSession(state) {
      state.messages = []
      state.sessionId = uuidv4()
      state.populatedFromChat = false
    },
  },
})

export const { addMessage, setLoading, setPopulatedFromChat, clearSession } = chatSlice.actions
export default chatSlice.reducer

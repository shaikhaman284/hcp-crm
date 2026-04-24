import { createSlice, createAsyncThunk } from '@reduxjs/toolkit'
import {
  getInteractions,
  createInteraction,
  updateInteraction,
  deleteInteraction,
  suggestFollowup,
} from '../api/client'

// ── Thunks ──────────────────────────────────────────────────────────────────

export const fetchInteractions = createAsyncThunk(
  'interactions/fetchAll',
  async (_, { rejectWithValue }) => {
    try {
      const { data } = await getInteractions()
      return data
    } catch (err) {
      return rejectWithValue(err.message)
    }
  }
)

export const logInteraction = createAsyncThunk(
  'interactions/create',
  async (interactionData, { rejectWithValue }) => {
    try {
      const { data } = await createInteraction(interactionData)
      return data
    } catch (err) {
      return rejectWithValue(err.message)
    }
  }
)

export const editInteraction = createAsyncThunk(
  'interactions/update',
  async ({ id, data }, { rejectWithValue }) => {
    try {
      const { data: updated } = await updateInteraction(id, data)
      return updated
    } catch (err) {
      return rejectWithValue(err.message)
    }
  }
)

export const removeInteraction = createAsyncThunk(
  'interactions/delete',
  async (id, { rejectWithValue }) => {
    try {
      await deleteInteraction(id)
      return id
    } catch (err) {
      return rejectWithValue(err.message)
    }
  }
)

export const fetchFollowups = createAsyncThunk(
  'interactions/followups',
  async (id, { rejectWithValue }) => {
    try {
      const { data } = await suggestFollowup(id)
      return data
    } catch (err) {
      return rejectWithValue(err.message)
    }
  }
)

// ── Slice ────────────────────────────────────────────────────────────────────

const EMPTY_FORM = {
  hcp_name: '',
  interaction_type: 'Meeting',
  interaction_date: '',
  interaction_time: '',
  attendees: [],
  topics_discussed: '',
  materials_shared: [],
  samples_distributed: [],
  sentiment: 'Neutral',
  outcomes: '',
  follow_up_actions: '',
  ai_summary: '',
}

const interactionSlice = createSlice({
  name: 'interactions',
  initialState: {
    list: [],
    current: null,
    loading: false,
    error: null,
    followUps: [],
    followUpsLoading: false,
    form: { data: { ...EMPTY_FORM }, isDirty: false },
  },
  reducers: {
    setFormField(state, action) {
      const { field, value } = action.payload
      state.form.data[field] = value
      state.form.isDirty = true
    },
    setFormDataFromChat(state, action) {
      const d = action.payload
      state.form.data = {
        hcp_name: d.hcp_name || '',
        interaction_type: d.interaction_type || 'Meeting',
        interaction_date: d.interaction_date || '',
        interaction_time: d.interaction_time || '',
        attendees: d.attendees || [],
        topics_discussed: d.topics_discussed || '',
        materials_shared: d.materials_shared || [],
        samples_distributed: d.samples_distributed || [],
        sentiment: d.sentiment || 'Neutral',
        outcomes: d.outcomes || '',
        follow_up_actions: d.follow_up_actions || '',
        ai_summary: d.ai_summary || '',
      }
      state.form.isDirty = true
    },
    resetForm(state) {
      state.form.data = { ...EMPTY_FORM }
      state.form.isDirty = false
      state.followUps = []
    },
    setCurrent(state, action) {
      state.current = action.payload
    },
    clearError(state) {
      state.error = null
    },
    clearFollowUps(state) {
      state.followUps = []
    },
  },
  extraReducers: (builder) => {
    // fetch all
    builder
      .addCase(fetchInteractions.pending, (s) => { s.loading = true; s.error = null })
      .addCase(fetchInteractions.fulfilled, (s, a) => { s.loading = false; s.list = a.payload })
      .addCase(fetchInteractions.rejected, (s, a) => { s.loading = false; s.error = a.payload })

    // create
      .addCase(logInteraction.pending, (s) => { s.loading = true; s.error = null })
      .addCase(logInteraction.fulfilled, (s, a) => {
        s.loading = false
        s.list.unshift(a.payload)
        s.current = a.payload
      })
      .addCase(logInteraction.rejected, (s, a) => { s.loading = false; s.error = a.payload })

    // update
      .addCase(editInteraction.pending, (s) => { s.loading = true })
      .addCase(editInteraction.fulfilled, (s, a) => {
        s.loading = false
        const idx = s.list.findIndex((i) => i.id === a.payload.id)
        if (idx !== -1) s.list[idx] = a.payload
        s.current = a.payload
      })
      .addCase(editInteraction.rejected, (s, a) => { s.loading = false; s.error = a.payload })

    // delete
      .addCase(removeInteraction.pending, (s) => { s.loading = true })
      .addCase(removeInteraction.fulfilled, (s, a) => {
        s.loading = false
        s.list = s.list.filter((i) => i.id !== a.payload)
        if (s.current?.id === a.payload) s.current = null
      })
      .addCase(removeInteraction.rejected, (s, a) => { s.loading = false; s.error = a.payload })

    // follow ups
      .addCase(fetchFollowups.pending, (s) => { s.followUpsLoading = true })
      .addCase(fetchFollowups.fulfilled, (s, a) => {
        s.followUpsLoading = false
        s.followUps = a.payload.follow_ups || []
      })
      .addCase(fetchFollowups.rejected, (s) => { s.followUpsLoading = false })
  },
})

export const {
  setFormField,
  setFormDataFromChat,
  resetForm,
  setCurrent,
  clearError,
  clearFollowUps,
} = interactionSlice.actions

export default interactionSlice.reducer

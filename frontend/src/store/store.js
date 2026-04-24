import { configureStore } from '@reduxjs/toolkit'
import interactionReducer from './interactionSlice'
import chatReducer from './chatSlice'

export const store = configureStore({
  reducer: {
    interactions: interactionReducer,
    chat: chatReducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        ignoredActions: ['interactions/fetchAll/fulfilled'],
      },
    }),
})

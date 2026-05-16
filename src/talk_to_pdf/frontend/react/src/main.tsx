import React from 'react'
import ReactDOM from 'react-dom/client'
import 'katex/dist/katex.min.css'

import { AppRouter } from '@/app/router'
import '@/index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <AppRouter />
  </React.StrictMode>,
)

import { Navigate, Outlet, RouterProvider, createBrowserRouter } from 'react-router-dom'

import { AuthProvider, useAuth } from '@/app/auth'
import { AppLayout } from '@/app/shell'
import { Spinner } from '@/components/ui/Spinner'
import { DashboardPage } from '@/pages/DashboardPage'
import { LoginPage } from '@/pages/LoginPage'
import { NotFoundPage } from '@/pages/NotFoundPage'
import { ProjectWorkspacePage } from '@/pages/ProjectWorkspacePage'
import { ProjectsPage } from '@/pages/ProjectsPage'
import { RegisterPage } from '@/pages/RegisterPage'

function FullScreenLoader() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-950 text-slate-300">
      <div className="flex items-center gap-3 rounded-2xl border border-slate-800 bg-slate-900/80 px-5 py-4">
        <Spinner className="h-5 w-5" />
        <span className="text-sm">Loading TalkToPDF…</span>
      </div>
    </div>
  )
}

function RequireAuth() {
  const { status } = useAuth()

  if (status === 'loading') {
    return <FullScreenLoader />
  }

  if (status === 'guest') {
    return <Navigate to="/login" replace />
  }

  return <Outlet />
}

function RedirectAuthenticated() {
  const { status } = useAuth()

  if (status === 'loading') {
    return <FullScreenLoader />
  }

  if (status === 'authenticated') {
    return <Navigate to="/dashboard" replace />
  }

  return <Outlet />
}

const router = createBrowserRouter([
  {
    path: '/',
    element: <Navigate to="/dashboard" replace />,
  },
  {
    element: <RedirectAuthenticated />,
    children: [
      {
        path: '/login',
        element: <LoginPage />,
      },
      {
        path: '/register',
        element: <RegisterPage />,
      },
    ],
  },
  {
    element: <RequireAuth />,
    children: [
      {
        element: <AppLayout />,
        children: [
          {
            path: '/dashboard',
            element: <DashboardPage />,
          },
          {
            path: '/projects',
            element: <ProjectsPage />,
          },
          {
            path: '/projects/:projectId',
            element: <ProjectWorkspacePage />,
          },
          {
            path: '/projects/:projectId/chats/:chatId',
            element: <ProjectWorkspacePage />,
          },
        ],
      },
    ],
  },
  {
    path: '*',
    element: <NotFoundPage />,
  },
])

export function AppRouter() {
  return (
    <AuthProvider>
      <RouterProvider router={router} />
    </AuthProvider>
  )
}

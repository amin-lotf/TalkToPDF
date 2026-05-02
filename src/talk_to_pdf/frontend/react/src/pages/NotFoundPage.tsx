import { Link } from 'react-router-dom'

export function NotFoundPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-950 px-6 text-slate-100">
      <div className="max-w-md rounded-[2rem] border border-slate-800 bg-slate-900/80 p-8 text-center shadow-panel">
        <p className="text-sm uppercase tracking-[0.28em] text-slate-500">404</p>
        <h1 className="mt-4 text-3xl font-semibold text-white">Page not found</h1>
        <p className="mt-3 text-sm leading-6 text-slate-400">
          The requested route does not exist in the current TalkToPDF React frontend.
        </p>
        <Link
          to="/dashboard"
          className="mt-8 inline-flex h-11 items-center justify-center rounded-xl bg-sky-500 px-4 text-sm font-medium text-slate-950 transition hover:bg-sky-400"
        >
          Back to dashboard
        </Link>
      </div>
    </div>
  )
}

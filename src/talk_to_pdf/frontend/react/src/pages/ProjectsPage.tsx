import { FolderPlus } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

import { useApiClient } from '@/app/auth'
import { useAppShell } from '@/app/shell'
import { ProjectCard } from '@/components/projects/ProjectCard'
import { EmptyState } from '@/components/ui/EmptyState'
import { Panel } from '@/components/ui/Panel'
import { Spinner } from '@/components/ui/Spinner'

export function ProjectsPage() {
  const api = useApiClient()
  const navigate = useNavigate()
  const {
    activeProjectId,
    currentProject,
    projectError,
    refreshProject,
    refreshProjects,
    projects,
    projectsError,
    projectsLoading,
  } = useAppShell()

  return (
    <div className="space-y-6">
      <Panel
        title="Projects"
        description="Open, rename, or delete a PDF-backed workspace."
        action={
          <div className="rounded-2xl border border-slate-800 bg-slate-950/60 px-4 py-3 text-right">
            <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Total</p>
            <p className="mt-1 text-lg font-semibold text-slate-100">{projectsLoading ? '…' : projects.length}</p>
          </div>
        }
      >
        {projectsError ? (
          <div className="rounded-3xl border border-rose-500/20 bg-rose-500/10 px-5 py-4 text-sm text-rose-100">
            {projectsError}
          </div>
        ) : projectsLoading ? (
          <div className="flex items-center gap-3 rounded-2xl border border-slate-800 bg-slate-950/60 px-4 py-3 text-sm text-slate-400">
            <Spinner />
            Loading projects…
          </div>
        ) : projects.length ? (
          <div className="grid gap-4 xl:grid-cols-2">
            {projects.map((project) => (
              <ProjectCard
                key={project.id}
                project={project}
                onOpen={(projectId) => navigate(`/projects/${projectId}`)}
                onRename={async (projectId, newName) => {
                  await api.renameProject(projectId, newName)
                  await refreshProjects()
                  if (activeProjectId === projectId && currentProject) {
                    await refreshProject()
                  }
                }}
                onDelete={async (projectId) => {
                  await api.deleteProject(projectId)
                  await refreshProjects()
                  if (activeProjectId === projectId) {
                    navigate('/projects')
                  }
                }}
              />
            ))}
          </div>
        ) : (
          <EmptyState
            icon={<FolderPlus className="h-6 w-6" />}
            title="Create the first project"
            description="Upload a PDF to start a new workspace."
          />
        )}
      </Panel>

      {projectError && activeProjectId ? (
        <div className="rounded-3xl border border-amber-500/20 bg-amber-500/10 px-5 py-4 text-sm text-amber-100">
          Active project refresh failed: {projectError}
        </div>
      ) : null}
    </div>
  )
}

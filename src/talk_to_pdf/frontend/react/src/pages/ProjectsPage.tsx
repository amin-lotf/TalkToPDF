import { FolderPlus, Sparkles } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

import { useApiClient } from '@/app/auth'
import { useAppShell } from '@/app/shell'
import { CreateProjectPanel } from '@/components/projects/CreateProjectPanel'
import { ProjectCard } from '@/components/projects/ProjectCard'
import { Button } from '@/components/ui/Button'
import { EmptyState } from '@/components/ui/EmptyState'
import { Panel } from '@/components/ui/Panel'

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
    <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
      <div className="space-y-6">
        <Panel
          title="Projects"
          description="Upload a PDF into a new project, then index it and open persistent chats."
          action={
            <Button variant="secondary" size="sm" onClick={() => navigate('/dashboard')}>
              Dashboard
            </Button>
          }
        >
          <div className="grid gap-4 md:grid-cols-3">
            <div className="rounded-2xl border border-slate-800 bg-slate-950/60 px-4 py-4">
              <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Total</p>
              <p className="mt-3 text-3xl font-semibold text-white">{projectsLoading ? '…' : projects.length}</p>
            </div>
            <div className="rounded-2xl border border-slate-800 bg-slate-950/60 px-4 py-4">
              <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Backend flow</p>
              <p className="mt-3 text-sm leading-6 text-slate-300">
                Project creation is the current PDF ingest path exposed by the backend.
              </p>
            </div>
            <div className="rounded-2xl border border-slate-800 bg-slate-950/60 px-4 py-4">
              <p className="flex items-center gap-2 text-xs uppercase tracking-[0.2em] text-slate-500">
                <Sparkles className="h-3.5 w-3.5" />
                Streamlit parity
              </p>
              <p className="mt-3 text-sm leading-6 text-slate-300">
                New projects automatically kick off indexing after upload, matching the existing frontend behavior.
              </p>
            </div>
          </div>
        </Panel>

        {projectsError ? (
          <div className="rounded-3xl border border-rose-500/20 bg-rose-500/10 px-5 py-4 text-sm text-rose-100">
            {projectsError}
          </div>
        ) : null}

        {projects.length ? (
          <div className="grid gap-4 lg:grid-cols-2">
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
            description="Upload a PDF into a new project and the app will take you straight into indexing and chat."
          />
        )}

        {projectError && activeProjectId ? (
          <div className="rounded-3xl border border-amber-500/20 bg-amber-500/10 px-5 py-4 text-sm text-amber-100">
            Active project refresh failed: {projectError}
          </div>
        ) : null}
      </div>

      <aside>
        <CreateProjectPanel
          onCreate={async ({ file, name }) => {
            const created = await api.createProject({ name, file })
            let startIndexingError: string | null = null

            try {
              await api.startIndexing(created.id, created.primary_document.id)
            } catch (error) {
              startIndexingError = error instanceof Error ? error.message : 'Indexing did not start automatically.'
            }

            await refreshProjects()
            navigate(`/projects/${created.id}`, {
              state: startIndexingError ? { startIndexingError } : undefined,
            })
          }}
        />
      </aside>
    </div>
  )
}

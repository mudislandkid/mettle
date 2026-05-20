"""Git statistics API routes."""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlmodel import Session

from ..database.connection import get_session
from ..database.models import Project
from ..schemas.git import GitCommitStats, GitErrorResponse, GitStatsResponse, TimePatterns
from ..services.git_analyzer_service import GitAnalyzerService

router = APIRouter()


@router.get("/{project_id}/git/stats", response_model=GitStatsResponse)
async def get_project_git_stats(
    project_id: int,
    session: Session = Depends(get_session),
):
    """
    Get Git commit history and statistics for a project.

    Returns comprehensive Git statistics including:
    - Commit timeline with line changes
    - Monthly and weekly aggregations
    - Heatmap data for visualization
    - Repository metadata

    **On-demand analysis**: Git history is analyzed when this endpoint is called.
    Results are cached for 5 minutes to improve performance.
    """
    # Fetch project from database
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check if it's a Git repository
    if not GitAnalyzerService.is_git_repository(project.path):
        return JSONResponse(
            status_code=200,
            content=GitErrorResponse(
                error="Not a Git repository",
                is_git_repo=False,
                project_id=project.id,
                project_name=project.name,
            ).model_dump(),
        )

    # Get commit history
    try:
        git_data = GitAnalyzerService.get_commit_history(project.path)

        if git_data is None:
            return JSONResponse(
                status_code=200,
                content=GitErrorResponse(
                    error="Failed to analyze Git repository",
                    is_git_repo=True,
                    project_id=project.id,
                    project_name=project.name,
                ).model_dump(),
            )

        # Convert commits to schema format
        commits_schema = [GitCommitStats(**commit_data) for commit_data in git_data["commits"]]

        # Build response
        response = GitStatsResponse(
            project_id=project.id,
            project_name=project.name,
            is_git_repo=git_data["is_git_repo"],
            total_commits=git_data["total_commits"],
            first_commit_date=git_data["first_commit_date"],
            last_commit_date=git_data["last_commit_date"],
            unique_authors=git_data["unique_authors"],
            commits=commits_schema,
            monthly_commits=git_data["monthly_commits"],
            weekly_commits=git_data["weekly_commits"],
            heatmap_data=git_data["heatmap_data"],
            time_patterns=TimePatterns(**git_data["time_patterns"]),
        )

        return response

    except Exception as e:
        # Log error and return graceful response
        print(f"Error analyzing Git repository {project.path}: {str(e)}")
        return JSONResponse(
            status_code=500,
            content=GitErrorResponse(
                error=f"Error analyzing repository: {str(e)}",
                is_git_repo=True,
                project_id=project.id,
                project_name=project.name,
            ).model_dump(),
        )

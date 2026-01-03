"""GitHub Issues connector for fetching issues from GitHub repositories."""

from typing import AsyncIterator

import httpx

from runbook_query.config import get_settings
from runbook_query.ingestion.connectors.base import BaseConnector
from runbook_query.models.document import RawDocument


class GitHubIssuesConnector(BaseConnector):
    """
    Connector for GitHub Issues.

    Fetches issues from a GitHub repository, including title, body,
    and top comments.
    """

    GITHUB_API_BASE = "https://api.github.com"

    def __init__(
        self,
        source_id: str,
        project: str,
        repo: str,
        labels: list[str] | None = None,
        state: str = "all",
        max_issues: int = 100,
        max_comments_per_issue: int = 5,
    ):
        """
        Initialize the GitHub Issues connector.

        Args:
            source_id: Unique identifier for this source
            project: Project name
            repo: GitHub repo in "owner/repo" format
            labels: Filter by issue labels
            state: Issue state filter ("open", "closed", "all")
            max_issues: Maximum number of issues to fetch
            max_comments_per_issue: Maximum comments to include per issue
        """
        super().__init__(source_id, project)
        self.repo = repo
        self.labels = labels or []
        self.state = state
        self.max_issues = max_issues
        self.max_comments_per_issue = max_comments_per_issue

    @property
    def source_type(self) -> str:
        return "issues"

    @property
    def source_name(self) -> str:
        return f"{self.repo} Issues"

    def _get_headers(self) -> dict:
        """Get HTTP headers for GitHub API."""
        settings = get_settings()
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "RunbookQuery/0.1.0",
        }
        if settings.github_token:
            headers["Authorization"] = f"token {settings.github_token}"
        return headers

    async def fetch_documents(self) -> AsyncIterator[RawDocument]:
        """Fetch issues from the GitHub repository."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            issues_fetched = 0
            page = 1

            while issues_fetched < self.max_issues:
                # Fetch a page of issues
                url = f"{self.GITHUB_API_BASE}/repos/{self.repo}/issues"
                params = {
                    "state": self.state,
                    "per_page": min(100, self.max_issues - issues_fetched),
                    "page": page,
                    "sort": "updated",
                    "direction": "desc",
                }
                if self.labels:
                    params["labels"] = ",".join(self.labels)

                response = await client.get(url, headers=self._get_headers(), params=params)

                if response.status_code == 403:
                    # Rate limited
                    raise RuntimeError(
                        "GitHub API rate limit exceeded. Set RUNBOOK_GITHUB_TOKEN."
                    )
                response.raise_for_status()

                issues = response.json()
                if not issues:
                    break

                for issue in issues:
                    # Skip pull requests (they appear in issues API)
                    if "pull_request" in issue:
                        continue

                    # Fetch comments if needed
                    comments_text = ""
                    if self.max_comments_per_issue > 0 and issue.get("comments", 0) > 0:
                        comments_text = await self._fetch_comments(
                            client, issue["comments_url"]
                        )

                    # Format issue content
                    content = self._format_issue(issue, comments_text)

                    yield RawDocument(
                        source_id=self.source_id,
                        external_id=f"github:{self.repo}#{issue['number']}",
                        title=issue["title"],
                        content=content,
                        url=issue["html_url"],
                        metadata={
                            "number": issue["number"],
                            "state": issue["state"],
                            "labels": [label["name"] for label in issue.get("labels", [])],
                            "created_at": issue["created_at"],
                            "updated_at": issue["updated_at"],
                            "author": issue.get("user", {}).get("login"),
                            "comments_count": issue.get("comments", 0),
                        },
                    )

                    issues_fetched += 1
                    if issues_fetched >= self.max_issues:
                        break

                page += 1

    async def _fetch_comments(self, client: httpx.AsyncClient, comments_url: str) -> str:
        """Fetch top comments for an issue."""
        response = await client.get(
            comments_url,
            headers=self._get_headers(),
            params={"per_page": self.max_comments_per_issue},
        )
        if response.status_code != 200:
            return ""

        comments = response.json()
        formatted_comments = []
        for comment in comments[: self.max_comments_per_issue]:
            author = comment.get("user", {}).get("login", "unknown")
            body = comment.get("body", "").strip()
            if body:
                formatted_comments.append(f"**Comment by @{author}:**\n{body}")

        return "\n\n---\n\n".join(formatted_comments)

    def _format_issue(self, issue: dict, comments_text: str) -> str:
        """Format issue data into a single text document."""
        parts = []

        # Title
        parts.append(f"# {issue['title']}")

        # Metadata
        labels = [label["name"] for label in issue.get("labels", [])]
        if labels:
            parts.append(f"**Labels:** {', '.join(labels)}")

        parts.append(f"**State:** {issue['state']}")
        parts.append(f"**Author:** @{issue.get('user', {}).get('login', 'unknown')}")

        # Body
        body = issue.get("body") or ""
        if body.strip():
            parts.append(f"\n## Description\n\n{body.strip()}")

        # Comments
        if comments_text:
            parts.append(f"\n## Comments\n\n{comments_text}")

        return "\n\n".join(parts)

# core/integrations/github.py

import os
from pathlib import Path
from github import Github, GithubException
from core.audit.audit_logger import AuditLogger
from core.audit.audit_event import AuditEvent


def _get_token() -> str:
    # Try .env file first
    env_file = Path(".env")
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.startswith("GITHUB_TOKEN="):
                return line.split("=", 1)[1].strip()
    # Try environment variable
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        raise ValueError("GITHUB_TOKEN not found. Add it to .env file.")
    return token


class GitHubCapability:
    """
    GitHub integration — repos, issues, PRs, commits.
    Uses Personal Access Token.
    """

    def __init__(self):
        self.audit = AuditLogger()
        self._client = None

    def _get_client(self) -> Github:
        if self._client:
            return self._client
        token = _get_token()
        self._client = Github(token)
        return self._client

    def execute(self, *, action: str, query: str = "", repo: str = "",
                title: str = "", body: str = "", number: int = 0) -> str:
        try:
            client = self._get_client()

            if action == "list_repos":
                return self._list_repos(client)
            elif action == "list_issues":
                return self._list_issues(client, repo)
            elif action == "list_prs":
                return self._list_prs(client, repo)
            elif action == "create_issue":
                return self._create_issue(client, repo, title, body)
            elif action == "search_repos":
                return self._search_repos(client, query)
            elif action == "repo_info":
                return self._repo_info(client, repo)
            elif action == "list_commits":
                return self._list_commits(client, repo)
            else:
                raise ValueError(f"Unknown GitHub action: {action}")

        except GithubException as e:
            self.audit.log(AuditEvent(
                phase="github", action=action, tool_name="github",
                decision="blocked", metadata={"reason": str(e)}
            ))
            return f"[BLOCKED] GitHub error: {e.data.get('message', str(e))}"
        except Exception as e:
            return f"[ERROR] {str(e)}"

    def _list_repos(self, client: Github) -> str:
        user = client.get_user()
        repos = list(user.get_repos())[:10]
        if not repos:
            return "No repositories found."

        output = []
        for r in repos:
            output.append(
                f"Repo: {r.full_name}\n"
                f"Description: {r.description or 'no description'}\n"
                f"Stars: {r.stargazers_count} | Language: {r.language or 'unknown'}\n"
                f"URL: {r.html_url}"
            )

        self.audit.log(AuditEvent(
            phase="github", action="list_repos",
            tool_name="github", decision="allowed"
        ))
        return "\n---\n".join(output)

    def _repo_info(self, client: Github, repo_name: str) -> str:
        if not repo_name:
            user = client.get_user()
            repo_name = f"{user.login}/{repo_name}"

        r = client.get_repo(repo_name)
        self.audit.log(AuditEvent(
            phase="github", action="repo_info",
            tool_name="github", decision="allowed",
            metadata={"repo": repo_name}
        ))
        return (
            f"Repo: {r.full_name}\n"
            f"Description: {r.description or 'none'}\n"
            f"Stars: {r.stargazers_count}\n"
            f"Forks: {r.forks_count}\n"
            f"Language: {r.language or 'unknown'}\n"
            f"Open Issues: {r.open_issues_count}\n"
            f"URL: {r.html_url}"
        )

    def _list_issues(self, client: Github, repo_name: str) -> str:
        if not repo_name:
            return "[ERROR] Repository name required. Format: owner/repo"

        r = client.get_repo(repo_name)
        issues = list(r.get_issues(state="open"))[:10]

        if not issues:
            return f"No open issues in {repo_name}."

        output = []
        for issue in issues:
            output.append(
                f"#{issue.number} — {issue.title}\n"
                f"By: {issue.user.login} | Created: {str(issue.created_at)[:10]}\n"
                f"URL: {issue.html_url}"
            )

        self.audit.log(AuditEvent(
            phase="github", action="list_issues",
            tool_name="github", decision="allowed",
            metadata={"repo": repo_name}
        ))
        return "\n---\n".join(output)

    def _list_prs(self, client: Github, repo_name: str) -> str:
        if not repo_name:
            return "[ERROR] Repository name required. Format: owner/repo"

        r = client.get_repo(repo_name)
        prs = list(r.get_pulls(state="open"))[:10]

        if not prs:
            return f"No open PRs in {repo_name}."

        output = []
        for pr in prs:
            output.append(
                f"#{pr.number} — {pr.title}\n"
                f"By: {pr.user.login} | Branch: {pr.head.ref} → {pr.base.ref}\n"
                f"URL: {pr.html_url}"
            )

        self.audit.log(AuditEvent(
            phase="github", action="list_prs",
            tool_name="github", decision="allowed",
            metadata={"repo": repo_name}
        ))
        return "\n---\n".join(output)

    def _list_commits(self, client: Github, repo_name: str) -> str:
        if not repo_name:
            return "[ERROR] Repository name required."

        r = client.get_repo(repo_name)
        commits = list(r.get_commits())[:5]

        output = []
        for c in commits:
            output.append(
                f"{c.sha[:7]} — {c.commit.message.splitlines()[0]}\n"
                f"By: {c.commit.author.name} | {str(c.commit.author.date)[:10]}"
            )

        self.audit.log(AuditEvent(
            phase="github", action="list_commits",
            tool_name="github", decision="allowed",
            metadata={"repo": repo_name}
        ))
        return "\n---\n".join(output)

    def _create_issue(self, client: Github, repo_name: str, title: str, body: str) -> str:
        if not repo_name or not title:
            return "[ERROR] Repository and title required."

        r = client.get_repo(repo_name)
        issue = r.create_issue(title=title, body=body or "")

        self.audit.log(AuditEvent(
            phase="github", action="create_issue",
            tool_name="github", decision="allowed",
            metadata={"repo": repo_name, "title": title}
        ))
        return f"Issue created: #{issue.number} — {issue.title}\nURL: {issue.html_url}"

    def _search_repos(self, client: Github, query: str) -> str:
        if not query:
            return "[ERROR] Search query required."

        repos = list(client.search_repositories(query=query))[:5]
        if not repos:
            return f"No repos found for '{query}'."

        output = []
        for r in repos:
            output.append(
                f"Repo: {r.full_name}\n"
                f"Stars: {r.stargazers_count} | Language: {r.language or 'unknown'}\n"
                f"Description: {r.description or 'none'}\n"
                f"URL: {r.html_url}"
            )
        return "\n---\n".join(output)
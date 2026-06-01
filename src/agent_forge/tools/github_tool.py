import httpx
import os
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

base_url = os.getenv("GITHUB_BASE_URL", "https://api.github.com")
github_token = os.getenv("GITHUB_TOKEN", "")


class GithubPRListArgs(BaseModel):
    owner_name: str
    repo_name: str


class GithubFileContentsArgs(BaseModel):
    owner_name: str
    repo_name: str
    file_path: str


class GithubTool:
    async def list_open_prs(self, args: dict) -> list:
        payload = GithubPRListArgs(**args)
        url = f"{base_url}/repos/{payload.owner_name}/{payload.repo_name}/pulls"
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if github_token:
            headers["Authorization"] = f"Bearer {github_token}"

        params = {"state": "open", "per_page": 30}
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, params=params)
            if response.status_code == 404:
                raise ValueError(f"Repository '{payload.owner_name}/{payload.repo_name}' not found on GitHub.")
            response.raise_for_status()
            prs = response.json()
            filtered = []
            for pr in prs:
                filtered.append({
                    "number": pr.get("number"),
                    "title": pr.get("title"),
                    "state": pr.get("state"),
                    "user": {"login": pr.get("user", {}).get("login")} if pr.get("user") else None,
                    "html_url": pr.get("html_url")
                })
            return filtered

    async def get_file_contents(self, args: dict) -> dict:
        payload = GithubFileContentsArgs(**args)
        url = f"{base_url}/repos/{payload.owner_name}/{payload.repo_name}/contents/{payload.file_path}"
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if github_token:
            headers["Authorization"] = f"Bearer {github_token}"

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            if response.status_code == 404:
                raise ValueError(f"File '{payload.file_path}' not found in repository '{payload.owner_name}/{payload.repo_name}'.")
            response.raise_for_status()
            res_data = response.json()
            if isinstance(res_data, dict) and res_data.get("encoding") == "base64" and "content" in res_data:
                import base64
                try:
                    b64_str = "".join(res_data["content"].split())
                    res_data["content"] = base64.b64decode(b64_str).decode("utf-8", errors="replace")
                    res_data["encoding"] = "utf-8"
                except Exception as ex:
                    print(f"Failed to decode base64 content: {ex}")
            return res_data


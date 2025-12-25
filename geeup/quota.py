"""
Quota discovery logic for geeup (Python 3.10+)
"""

from typing import Any
import ee

from .auth import get_authenticated_session


def fetch_quota_data(project: str | None = None) -> dict[str, dict[str, Any]]:
    """
    Return quota information keyed by project path.
    No printing, no Rich, no CLI behavior.

    Args:
        project: Optional specific project path (e.g., 'projects/my-project' or 'users/username')
                If None, discovers all available projects.

    Returns:
        Dictionary mapping project paths to their quota information.
    """
    session, sa_project = get_authenticated_session()
    results: dict[str, dict[str, Any]] = {}

    def get_cloud_project_quota(project_id: str) -> dict[str, Any] | None:
        """Get quota for a cloud project using direct API."""
        url = f"https://earthengine.googleapis.com/v1/projects/{project_id}/assets"
        r = session.get(url)
        return r.json() if r.status_code == 200 else None

    def get_legacy_roots() -> list[str]:
        """Get all legacy root assets using direct API."""
        url = "https://earthengine.googleapis.com/v1/projects/earthengine-legacy:listAssets"
        r = session.get(url)
        return (
            [a["id"] for a in r.json().get("assets", [])]
            if r.status_code == 200
            else []
        )

    def get_legacy_project_quota(path: str) -> dict[str, Any] | None:
        """Get quota for a legacy project using direct API."""
        if path.startswith("users/"):
            api_path = f"projects/earthengine-legacy/assets/{path}"
        else:
            api_path = f"projects/earthengine-legacy/assets/{path}"

        r = session.get(f"https://earthengine.googleapis.com/v1/{api_path}")
        return r.json() if r.status_code == 200 else None

    def get_cloud_project_from_credentials() -> str | None:
        """Extract cloud project ID from credentials."""
        try:
            creds = ee.data.get_persistent_credentials()

            # Check for service account credentials
            if hasattr(creds, 'service_account_email'):
                email = creds.service_account_email
                project_id = email.split('@')[1].split('.')[0]
                return project_id

            # Check for default credentials (user credentials)
            if hasattr(creds, 'project_id') and creds.project_id:
                return creds.project_id

            # Try to get from quota_project_id
            if hasattr(creds, 'quota_project_id') and creds.quota_project_id:
                return creds.quota_project_id

            # Try getting project from ee.data
            try:
                project_val = ee.data.getProject()
                if project_val:
                    if project_val.startswith('projects/'):
                        return project_val.split('projects/')[1]
                    return project_val
            except Exception:
                pass

        except Exception:
            pass
        return None

    def try_get_quota(path: str, legacy: bool) -> dict[str, Any] | None:
        """Try multiple methods to get quota for a given path."""
        # Try the direct API approach first if it's a legacy project
        if legacy:
            q = get_legacy_project_quota(path)
            if q:
                return q

        # Try standard EE API methods
        try:
            info = ee.data.getInfo(path)
            if info and ("quota" in info or "sizeBytes" in info):
                return info
        except Exception:
            pass

        # Try legacy quota method
        if legacy:
            try:
                quota_info = ee.data.getAssetRootQuota(path)
                if quota_info:
                    return quota_info
            except Exception:
                pass

        # For cloud projects, try with /assets suffix
        if path.startswith("projects/") and "/assets" not in path:
            for suffix in ["/assets", "/assets/"]:
                try:
                    asset_info = ee.data.getAsset(path + suffix)
                    if asset_info and ("quota" in asset_info or "sizeBytes" in asset_info):
                        return asset_info
                except Exception:
                    pass

        return None

    # ---- no project specified: discover everything ----
    if project is None:
        displayed_projects = set()

        # Try to get cloud project from credentials
        cloud_project_id = get_cloud_project_from_credentials()
        if cloud_project_id:
            q = get_cloud_project_quota(cloud_project_id)
            if q:
                project_path = f"projects/{cloud_project_id}"
                results[project_path] = q
                displayed_projects.add(project_path)

        # Try using getAssetRoots (may not work for service accounts)
        try:
            roots = ee.data.getAssetRoots()
            for root in roots:
                root_path = root["id"]
                parent_project = root_path.split("/assets/")[0] if "/assets/" in root_path else root_path

                if parent_project in displayed_projects:
                    continue

                is_legacy = parent_project.startswith("users/")
                quota_info = try_get_quota(parent_project, is_legacy=is_legacy)

                if quota_info:
                    results[parent_project] = quota_info
                    displayed_projects.add(parent_project)
        except Exception:
            # getAssetRoots may fail for service accounts, continue with legacy approach
            pass

        # Get legacy projects using direct API
        legacy_roots = get_legacy_roots()
        for legacy_path in legacy_roots:
            if legacy_path in displayed_projects:
                continue

            q = get_legacy_project_quota(legacy_path)
            if q:
                results[legacy_path] = q
                displayed_projects.add(legacy_path)

        return results

    # ---- specific project ----
    normalized = project

    # Normalize the project path
    if not project.startswith(("projects/", "users/")):
        # Could be just the project ID or username
        # Try cloud project first
        cloud_quota = get_cloud_project_quota(project)
        if cloud_quota:
            normalized = f"projects/{project}"
            results[normalized] = cloud_quota
            return results
        else:
            # Try as legacy user
            normalized = f"users/{project}"

    # Determine if it's a legacy project
    legacy = normalized.startswith("users/")

    # For projects that start with "projects/" but might be legacy
    if normalized.startswith("projects/") and not normalized.startswith("projects/earthengine-"):
        # Check if this project is in legacy roots
        legacy_roots = get_legacy_roots()
        if normalized in legacy_roots:
            legacy = True

    q = try_get_quota(normalized, legacy)

    if q:
        results[normalized] = q

    return results

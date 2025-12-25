"""
Earth Engine authentication and session utilities for geeup.
Python 3.10+
"""

import json
from pathlib import Path
from typing import Optional

import ee
from google.auth.transport.requests import AuthorizedSession


def get_sa_credentials_path() -> tuple[Path, Path]:
    """
    Return the service account directory and credentials file path.

    Default:
        ~/.config/sa_earthengine/sa_credentials.json
    """
    home = Path.home()
    sa_dir = home / ".config" / "sa_earthengine"
    sa_file = sa_dir / "sa_credentials.json"
    return sa_dir, sa_file


def initialize_ee() -> None:
    """
    Initialize Earth Engine.

    Order of preference:
    1. Service account credentials
    2. Default user authentication

    Safe to call multiple times.
    """
    _, sa_file = get_sa_credentials_path()

    if sa_file.exists():
        try:
            with sa_file.open() as f:
                sa_data = json.load(f)

            email = sa_data.get("client_email")
            if email:
                creds = ee.ServiceAccountCredentials(email, str(sa_file))
                ee.Initialize(
                    creds,
                    opt_url="https://earthengine-highvolume.googleapis.com",
                )
                return
        except Exception:
            pass

    ee.Initialize(opt_url="https://earthengine-highvolume.googleapis.com")


def get_authenticated_session() -> tuple[AuthorizedSession, Optional[str]]:
    """
    Return an AuthorizedSession and inferred project name if available.
    """
    _, sa_file = get_sa_credentials_path()

    if sa_file.exists():
        try:
            with sa_file.open() as f:
                sa_data = json.load(f)

            email = sa_data.get("client_email")
            if email:
                creds = ee.ServiceAccountCredentials(email, str(sa_file))
                session = AuthorizedSession(creds)
                project = email.split("@")[1].split(".")[0]
                return session, project
        except Exception:
            pass

    creds = ee.data.get_persistent_credentials()
    return AuthorizedSession(creds), None

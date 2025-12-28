"""
Pytest configuration for geeup tests.
"""

import os
import sys
from unittest.mock import MagicMock, Mock, patch

import pytest

# Import fake_ee from the same directory
from . import fake_ee

# Mock ee module before geeup imports
sys.modules['ee'] = fake_ee

# Mock other dependencies that might not be installed
mock_box = MagicMock()
mock_box.Box = dict
sys.modules['box'] = mock_box


@pytest.fixture(scope='session', autouse=True)
def setup_environment():
    """Set up test environment."""
    # Ensure ee is mocked
    if 'ee' not in sys.modules:
        sys.modules['ee'] = fake_ee

    yield

    # Cleanup
    pass


@pytest.fixture
def mock_ee_initialize():
    """Mock Earth Engine initialization."""
    with patch.object(fake_ee, 'Initialize') as mock:
        yield mock


@pytest.fixture
def mock_google_credentials():
    """Mock Google credentials with proper methods."""
    mock_creds = MagicMock()
    mock_creds.before_request = MagicMock()
    mock_creds.refresh = MagicMock()
    mock_creds.expired = False
    mock_creds.valid = True
    mock_creds.service_account_email = "test@test-project.iam.gserviceaccount.com"
    return mock_creds


@pytest.fixture
def mock_gdal():
    """Mock GDAL module for testing."""
    mock_gdal_module = MagicMock()
    mock_gdal_module.UseExceptions = MagicMock()
    mock_gdal_module.PushErrorHandler = MagicMock()
    mock_gdal_module.PopErrorHandler = MagicMock()
    mock_gdal_module.GetDataTypeName = MagicMock(return_value='Byte')
    mock_gdal_module.GetColorInterpretationName = MagicMock(return_value='Gray')

    # Mock dataset
    mock_dataset = MagicMock()
    mock_dataset.RasterXSize = 100
    mock_dataset.RasterYSize = 100
    mock_dataset.RasterCount = 1

    # Mock band
    mock_band = MagicMock()
    mock_band.DataType = 1  # GDT_Byte
    mock_band.GetColorInterpretation = MagicMock(return_value=1)
    mock_band.GetColorTable = MagicMock(return_value=None)
    mock_dataset.GetRasterBand = MagicMock(return_value=mock_band)

    mock_gdal_module.Open = MagicMock(return_value=mock_dataset)

    with patch.dict('sys.modules', {'osgeo': MagicMock(), 'osgeo.gdal': mock_gdal_module}):
        yield mock_gdal_module


@pytest.fixture
def sample_task_list():
    """Sample task list for testing."""
    return [
        {
            'id': 'TASK001',
            'state': 'RUNNING',
            'description': 'Export Image Task',
            'task_type': 'EXPORT_IMAGE',
            'attempt': 1,
            'start_timestamp_ms': 1609459200000,
            'update_timestamp_ms': 1609462800000,
            'destination_uris': ['https://code.earthengine.google.com/?asset=projects/test/image'],
            'batch_eecu_usage_seconds': 120.5
        },
        {
            'id': 'TASK002',
            'state': 'READY',
            'description': 'Export Table Task',
            'task_type': 'EXPORT_TABLE',
            'attempt': 1,
            'start_timestamp_ms': 1609459200000,
            'update_timestamp_ms': 1609459300000,
        },
    ]


@pytest.fixture
def sample_quota_data():
    """Sample quota data for testing."""
    return {
        'users/testuser': {
            'quota': {
                'sizeBytes': '5000000000',
                'maxSizeBytes': '10000000000',
                'assetCount': '50',
                'maxAssets': '1000'
            }
        },
        'projects/test-project': {
            'quota': {
                'sizeBytes': '8000000000',
                'maxSizeBytes': '20000000000',
                'assetCount': '150',
                'maxAssets': '5000'
            }
        }
    }


@pytest.fixture
def mock_service_account_creds(tmp_path):
    """Mock service account credentials file."""
    import json

    sa_dir = tmp_path / ".config" / "earthengine"
    sa_dir.mkdir(parents=True, exist_ok=True)

    sa_file = sa_dir / "service_account_credentials.json"
    sa_data = {
        "type": "service_account",
        "project_id": "test-project",
        "private_key_id": "key123",
        "private_key": "-----BEGIN PRIVATE KEY-----\ntest\n-----END PRIVATE KEY-----\n",
        "client_email": "test@test-project.iam.gserviceaccount.com",
        "client_id": "123456789",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    }

    sa_file.write_text(json.dumps(sa_data))

    return sa_dir, sa_file


@pytest.fixture
def mock_subprocess_run():
    """Mock subprocess.run for external command calls."""
    with patch('subprocess.run') as mock:
        mock.return_value = MagicMock(
            returncode=0,
            stdout='',
            stderr=''
        )
        yield mock


@pytest.fixture
def mock_requests_get():
    """Mock requests.get for API calls."""
    with patch('requests.get') as mock:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"info": {"version": "1.0.0"}}
        mock_response.raise_for_status.return_value = None
        mock.return_value = mock_response
        yield mock

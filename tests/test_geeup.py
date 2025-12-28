"""
Test suite for geeup CLI tool using the fake ee module.
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch, mock_open

import pytest
from click.testing import CliRunner

# Import fake_ee from conftest (already mocked in sys.modules)
from . import fake_ee

# Now import geeup components
from geeup.geeup import (
    cli,
    humansize,
    compare_version,
    get_latest_version,
    get_installed_version,
)


@pytest.fixture
def runner():
    """Create a CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_ee_initialize():
    """Mock Earth Engine initialization."""
    with patch.object(fake_ee, 'Initialize') as mock:
        yield mock


@pytest.fixture
def temp_dir(tmp_path):
    """Create a temporary directory for testing."""
    return tmp_path


class TestUtilityFunctions:
    """Test utility functions."""

    def test_humansize_bytes(self):
        assert humansize(500) == "500 B"

    def test_humansize_kilobytes(self):
        assert humansize(2048) == "2 KB"

    def test_humansize_megabytes(self):
        assert humansize(5242880) == "5 MB"

    def test_humansize_gigabytes(self):
        assert humansize(3221225472) == "3 GB"

    def test_humansize_terabytes(self):
        assert humansize(1099511627776) == "1 TB"

    def test_compare_version_greater(self):
        assert compare_version("2.0.0", "1.0.0") == 1

    def test_compare_version_less(self):
        assert compare_version("1.0.0", "2.0.0") == -1

    def test_compare_version_equal(self):
        assert compare_version("1.0.0", "1.0.0") == 0

    @patch('requests.get')
    def test_get_latest_version_success(self, mock_get):
        mock_response = Mock()
        mock_response.json.return_value = {"info": {"version": "1.2.3"}}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        version = get_latest_version("test-package")
        assert version == "1.2.3"

    @patch('requests.get')
    def test_get_latest_version_failure(self, mock_get):
        mock_get.side_effect = Exception("Network error")
        version = get_latest_version("test-package")
        assert version is None

    @patch('importlib.metadata.version')
    def test_get_installed_version_success(self, mock_version):
        mock_version.return_value = "1.0.0"
        version = get_installed_version("test-package")
        assert version == "1.0.0"

    @patch('importlib.metadata.version')
    def test_get_installed_version_not_found(self, mock_version):
        import importlib.metadata
        mock_version.side_effect = importlib.metadata.PackageNotFoundError()
        version = get_installed_version("test-package")
        assert version is None


class TestReadmeCommand:
    """Test the readme command."""

    def test_readme_command(self, runner, mock_ee_initialize):
        """Test opening documentation."""
        with patch('webbrowser.open', return_value=True) as mock_browser:
            result = runner.invoke(cli, ['readme'])
            assert result.exit_code == 0
            mock_browser.assert_called_once_with(
                "https://geeup.geetools.xyz/", new=2
            )

    def test_readme_command_no_browser(self, runner, mock_ee_initialize):
        """Test readme when browser fails to open."""
        with patch('webbrowser.open', return_value=False):
            result = runner.invoke(cli, ['readme'])
            assert result.exit_code == 0
            assert 'does not have a monitor' in result.output or 'Visit:' in result.output


class TestAuthCommand:
    """Test authentication commands."""

    def test_auth_status_configured(self, runner, mock_ee_initialize, temp_dir):
        """Test auth status when service account is configured."""
        sa_file = temp_dir / "service_account.json"
        sa_data = {"client_email": "test@project.iam.gserviceaccount.com"}
        sa_file.write_text(json.dumps(sa_data))

        with patch('geeup.auth.get_sa_credentials_path', return_value=(temp_dir, sa_file)):
            result = runner.invoke(cli, ['auth', '--status'])
            assert result.exit_code == 0
            assert 'Service account configured' in result.output or 'test@project' in result.output

    def test_auth_status_not_configured(self, runner, mock_ee_initialize, temp_dir):
        """Test auth status when no service account is configured."""
        sa_file = temp_dir / "service_account.json"

        with patch('geeup.auth.get_sa_credentials_path', return_value=(temp_dir, sa_file)):
            result = runner.invoke(cli, ['auth', '--status'])
            assert result.exit_code == 0
            assert 'No service account' in result.output or 'default' in result.output

    def test_auth_remove_success(self, runner, mock_ee_initialize, temp_dir):
        """Test removing service account credentials."""
        sa_file = temp_dir / "service_account.json"
        sa_file.write_text('{"client_email": "test@example.com"}')

        with patch('geeup.auth.get_sa_credentials_path', return_value=(temp_dir, sa_file)):
            result = runner.invoke(cli, ['auth', '--remove'])
            assert result.exit_code == 0
            assert not sa_file.exists()

    def test_auth_store_credentials(self, runner, mock_ee_initialize, temp_dir):
        """Test storing service account credentials."""
        cred_file = temp_dir / "creds.json"
        sa_file = temp_dir / "service_account.json"
        sa_data = {
            "client_email": "test@project.iam.gserviceaccount.com",
            "private_key": "-----BEGIN PRIVATE KEY-----\ntest\n-----END PRIVATE KEY-----\n"
        }
        cred_file.write_text(json.dumps(sa_data))

        with patch('geeup.auth.get_sa_credentials_path', return_value=(temp_dir, sa_file)):
            result = runner.invoke(cli, ['auth', '--cred', str(cred_file)])
            assert result.exit_code == 0
            assert sa_file.exists()


class TestRenameCommand:
    """Test file renaming command."""

    def test_rename_no_files_need_renaming(self, runner, mock_ee_initialize, temp_dir):
        """Test rename when no files need renaming."""
        (temp_dir / "valid_file.tif").touch()

        result = runner.invoke(cli, ['rename', '--input', str(temp_dir)])
        assert result.exit_code == 0
        assert 'No files need renaming' in result.output

    def test_rename_with_invalid_characters(self, runner, mock_ee_initialize, temp_dir):
        """Test renaming files with invalid characters."""
        (temp_dir / "file with spaces.tif").touch()
        (temp_dir / "file@#$.tif").touch()

        result = runner.invoke(cli, ['rename', '--input', str(temp_dir), '--batch'])
        assert result.exit_code == 0
        assert (temp_dir / "file_with_spaces.tif").exists()

    def test_rename_batch_mode(self, runner, mock_ee_initialize, temp_dir):
        """Test batch renaming without confirmation."""
        (temp_dir / "bad file!.tif").touch()

        result = runner.invoke(cli, ['rename', '--input', str(temp_dir), '--batch'])
        assert result.exit_code == 0
        assert 'Renamed' in result.output


class TestQuotaCommand:
    """Test quota command."""

    def test_quota_no_project(self, runner, mock_ee_initialize):
        """Test quota display without specific project."""
        with patch('geeup.quota.fetch_quota_data') as mock_fetch:
            mock_fetch.return_value = {
                'users/test': {
                    'quota': {
                        'sizeBytes': '1000000',
                        'maxSizeBytes': '10000000',
                        'assetCount': '10',
                        'maxAssets': '100'
                    }
                }
            }
            result = runner.invoke(cli, ['quota'])
            assert result.exit_code == 0
            assert 'Quota' in result.output or 'Storage' in result.output

    def test_quota_specific_project(self, runner, mock_ee_initialize):
        """Test quota for specific project."""
        with patch('geeup.quota.fetch_quota_data') as mock_fetch:
            mock_fetch.return_value = {
                'projects/test': {
                    'quota': {
                        'sizeBytes': '5000000000',
                        'maxSizeBytes': '10000000000',
                        'assetCount': '50',
                        'maxAssets': '1000'
                    }
                }
            }
            result = runner.invoke(cli, ['quota', '--project', 'projects/test'])
            assert result.exit_code == 0


class TestZipshapeCommand:
    """Test zipshape command."""

    def test_zipshape_success(self, runner, mock_ee_initialize, temp_dir):
        """Test zipping shapefiles."""
        input_dir = temp_dir / "input"
        output_dir = temp_dir / "output"
        input_dir.mkdir()
        output_dir.mkdir()

        # Create dummy shapefile components
        (input_dir / "test.shp").touch()
        (input_dir / "test.shx").touch()
        (input_dir / "test.dbf").touch()

        with patch('geeup.zip_shape.zip_shapefiles') as mock_zip:
            mock_zip.return_value = {'created': 1, 'skipped': 0, 'failed': 0}
            result = runner.invoke(cli, [
                'zipshape',
                '--input', str(input_dir),
                '--output', str(output_dir)
            ])
            assert result.exit_code == 0
            assert 'Created 1 ZIP' in result.output


class TestGetmetaCommand:
    """Test getmeta command."""

    def test_getmeta_no_gdal(self, runner, mock_ee_initialize, temp_dir):
        """Test getmeta when GDAL is not available."""
        input_dir = temp_dir / "input"
        input_dir.mkdir()
        metadata_file = temp_dir / "metadata.csv"

        with patch.dict('sys.modules', {'osgeo': None}):
            result = runner.invoke(cli, [
                'getmeta',
                '--input', str(input_dir),
                '--metadata', str(metadata_file)
            ])
            # Should fail or show error about GDAL
            assert 'GDAL' in result.output or result.exit_code != 0


class TestTasksCommand:
    """Test task management commands."""

    def test_tasks_summary(self, runner, mock_ee_initialize):
        """Test displaying task summary."""
        with patch('geeup.tasks.summarize_tasks') as mock_summarize:
            mock_summarize.return_value = {
                'RUNNING': 2,
                'READY': 1,
                'COMPLETED': 10,
                'FAILED': 0,
                'CANCELLED': 0
            }
            result = runner.invoke(cli, ['tasks'])
            assert result.exit_code == 0
            assert 'Task Summary' in result.output or 'Running' in result.output

    def test_tasks_by_state(self, runner, mock_ee_initialize):
        """Test filtering tasks by state."""
        with patch('geeup.tasks.fetch_tasks') as mock_fetch:
            mock_fetch.return_value = [
                {
                    'id': 'task-1',
                    'state': 'COMPLETED',
                    'description': 'Test task'
                }
            ]
            result = runner.invoke(cli, ['tasks', '--state', 'COMPLETED'])
            assert result.exit_code == 0

    def test_tasks_by_id(self, runner, mock_ee_initialize):
        """Test querying specific task by ID."""
        with patch('geeup.tasks.fetch_tasks') as mock_fetch:
            mock_fetch.return_value = [
                {
                    'id': 'task-123',
                    'state': 'RUNNING',
                    'description': 'Test task'
                }
            ]
            result = runner.invoke(cli, ['tasks', '--id', 'task-123'])
            assert result.exit_code == 0


class TestCancelCommand:
    """Test task cancellation commands."""

    def test_cancel_all_tasks(self, runner, mock_ee_initialize):
        """Test cancelling all tasks."""
        with patch.object(fake_ee.data, 'getTaskList') as mock_list:
            with patch.object(fake_ee.data, 'cancelTask') as mock_cancel:
                mock_list.return_value = [
                    {'id': 'task-1', 'state': 'RUNNING'},
                    {'id': 'task-2', 'state': 'READY'}
                ]
                result = runner.invoke(cli, ['cancel', '--tasks', 'all'])
                assert result.exit_code == 0
                assert mock_cancel.call_count == 2

    def test_cancel_running_tasks(self, runner, mock_ee_initialize):
        """Test cancelling only running tasks."""
        with patch.object(fake_ee.data, 'getTaskList') as mock_list:
            with patch.object(fake_ee.data, 'cancelTask') as mock_cancel:
                mock_list.return_value = [
                    {'id': 'task-1', 'state': 'RUNNING'},
                    {'id': 'task-2', 'state': 'READY'},
                    {'id': 'task-3', 'state': 'COMPLETED'}
                ]
                result = runner.invoke(cli, ['cancel', '--tasks', 'running'])
                assert result.exit_code == 0
                assert mock_cancel.call_count == 1

    def test_cancel_pending_tasks(self, runner, mock_ee_initialize):
        """Test cancelling only pending tasks."""
        with patch.object(fake_ee.data, 'getTaskList') as mock_list:
            with patch.object(fake_ee.data, 'cancelTask') as mock_cancel:
                mock_list.return_value = [
                    {'id': 'task-1', 'state': 'READY'},
                    {'id': 'task-2', 'state': 'RUNNING'}
                ]
                result = runner.invoke(cli, ['cancel', '--tasks', 'pending'])
                assert result.exit_code == 0
                assert mock_cancel.call_count == 1

    def test_cancel_specific_task(self, runner, mock_ee_initialize):
        """Test cancelling specific task by ID."""
        with patch.object(fake_ee.data, 'getTaskStatus') as mock_status:
            with patch.object(fake_ee.data, 'cancelTask') as mock_cancel:
                mock_status.return_value = [{'state': 'RUNNING', 'id': 'task-123'}]
                result = runner.invoke(cli, ['cancel', '--tasks', 'task-123'])
                assert result.exit_code == 0
                mock_cancel.assert_called_once_with('task-123')


class TestDeleteCommand:
    """Test asset deletion command."""

    def test_delete_asset(self, runner, mock_ee_initialize):
        """Test deleting an asset."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout='', stderr='')
            result = runner.invoke(cli, ['delete', '--id', 'users/test/asset'])
            assert result.exit_code == 0
            assert 'Deleted' in result.output or 'users/test/asset' in result.output

    def test_delete_asset_failure(self, runner, mock_ee_initialize):
        """Test failed asset deletion."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(
                returncode=1,
                stdout='',
                stderr='Asset not found'
            )
            result = runner.invoke(cli, ['delete', '--id', 'users/test/nonexistent'])
            assert result.exit_code == 0
            assert 'Failed' in result.output or 'Error' in result.output


class TestUploadCommand:
    """Test upload commands."""

    def test_upload_basic(self, runner, mock_ee_initialize, temp_dir):
        """Test basic image upload."""
        source_dir = temp_dir / "source"
        source_dir.mkdir()
        metadata_file = temp_dir / "metadata.csv"
        metadata_file.write_text("system:index\ntest_image")

        with patch('geeup.batch_uploader.upload') as mock_upload:
            result = runner.invoke(cli, [
                'upload',
                '--source', str(source_dir),
                '--dest', 'users/test/collection',
                '--metadata', str(metadata_file),
                '--user', 'test@example.com'
            ])
            assert result.exit_code == 0
            mock_upload.assert_called_once()

    def test_upload_with_options(self, runner, mock_ee_initialize, temp_dir):
        """Test upload with additional options."""
        source_dir = temp_dir / "source"
        source_dir.mkdir()
        metadata_file = temp_dir / "metadata.csv"
        metadata_file.write_text("system:index\ntest_image")

        with patch('geeup.batch_uploader.upload') as mock_upload:
            result = runner.invoke(cli, [
                'upload',
                '--source', str(source_dir),
                '--dest', 'users/test/collection',
                '--metadata', str(metadata_file),
                '--user', 'test@example.com',
                '--nodata', '0',
                '--pyramids', 'MEAN',
                '--workers', '2',
                '--dry-run'
            ])
            assert result.exit_code == 0
            mock_upload.assert_called_once()


class TestTabupCommand:
    """Test table upload commands."""

    def test_tabup_basic(self, runner, mock_ee_initialize, temp_dir):
        """Test basic table upload."""
        source_dir = temp_dir / "source"
        source_dir.mkdir()

        with patch('geeup.tuploader.tabup') as mock_tabup:
            result = runner.invoke(cli, [
                'tabup',
                '--source', str(source_dir),
                '--dest', 'users/test/folder',
                '--user', 'test@example.com'
            ])
            assert result.exit_code == 0
            mock_tabup.assert_called_once()

    def test_tabup_with_coordinates(self, runner, mock_ee_initialize, temp_dir):
        """Test table upload with coordinate columns."""
        source_dir = temp_dir / "source"
        source_dir.mkdir()

        with patch('geeup.tuploader.tabup') as mock_tabup:
            result = runner.invoke(cli, [
                'tabup',
                '--source', str(source_dir),
                '--dest', 'users/test/folder',
                '--user', 'test@example.com',
                '--x', 'longitude',
                '--y', 'latitude'
            ])
            assert result.exit_code == 0
            mock_tabup.assert_called_once()


class TestIntegration:
    """Integration tests using fake ee module."""

    def test_full_workflow_with_fake_ee(self, runner, mock_ee_initialize):
        """Test a complete workflow using the fake ee module."""
        # Test that Image operations work
        img = fake_ee.Image.constant(0)
        bands = img.bandNames()
        assert bands.getInfo() == ["B1", "B2"]

        # Test Geometry operations
        geom = fake_ee.Geometry.Point([0, 0])
        assert geom.type().value == "Point"

    def test_error_handling(self, runner, mock_ee_initialize):
        """Test error handling in commands."""
        # Test missing required options
        result = runner.invoke(cli, ['upload'])
        assert result.exit_code != 0

        # Test invalid directory
        result = runner.invoke(cli, [
            'rename',
            '--input', '/nonexistent/directory'
        ])
        assert result.exit_code == 0  # Should handle gracefully
        assert 'not found' in result.output.lower() or 'Error' in result.output


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

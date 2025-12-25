"""
Modern metadata loader for Google Earth Engine with Pydantic validation.

Licensed under the Apache License, Version 2.0
"""

import csv
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

from pydantic import BaseModel, Field, field_validator, model_validator

logger = logging.getLogger(__name__)


# GEE system properties that are allowed
GEE_SYSTEM_PROPERTIES = {
    "system:index",
    "system:description",
    "system:provider_url",
    "system:tags",
    "system:time_end",
    "system:time_start",
    "system:title",
}


class PropertyValidationError(Exception):
    """Raised when property validation fails."""

    pass


class MetadataEntry(BaseModel):
    """Single metadata entry with validation."""

    # The asset identifier (filename without extension)
    asset_id: str = Field(..., min_length=1)

    # All other properties
    properties: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("asset_id")
    @classmethod
    def validate_asset_id(cls, v: str) -> str:
        """Ensure asset_id contains only valid characters."""
        import re

        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError(
                f"Asset ID '{v}' contains invalid characters. "
                "Only letters, numbers, hyphens, and underscores allowed."
            )
        return v

    @field_validator("properties")
    @classmethod
    def validate_properties(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate property keys and values."""
        for key, value in v.items():
            # Validate property key
            if not _is_valid_property_key(key):
                raise ValueError(
                    f"Invalid property key '{key}'. Must be a system property "
                    f"or contain only letters, numbers, and underscores."
                )

            # Validate property value
            if not _is_valid_property_value(value):
                raise ValueError(f"Invalid value for property '{key}': {value}")

        return v

    @model_validator(mode="after")
    def validate_time_properties(self) -> "MetadataEntry":
        """Validate time-related properties."""
        props = self.properties

        # Check time_start and time_end are valid timestamps
        for time_prop in ["system:time_start", "system:time_end"]:
            if time_prop in props:
                try:
                    value = props[time_prop]
                    if isinstance(value, str):
                        # Try to parse as ISO format or timestamp
                        try:
                            # ISO format
                            datetime.fromisoformat(value.replace("Z", "+00:00"))
                        except ValueError:
                            # Try as milliseconds timestamp
                            int(value)
                except (ValueError, TypeError) as e:
                    raise ValueError(
                        f"{time_prop} must be a valid ISO date string or "
                        f"milliseconds since epoch: {e}"
                    )

        # Ensure time_start <= time_end if both present
        if "system:time_start" in props and "system:time_end" in props:
            start = _normalize_timestamp(props["system:time_start"])
            end = _normalize_timestamp(props["system:time_end"])
            if start and end and start > end:
                raise ValueError(
                    "system:time_start must be before or equal to system:time_end"
                )

        return self

    def to_gee_properties(self) -> Dict[str, Any]:
        """Convert to GEE-compatible properties dict."""
        gee_props = self.properties.copy()

        # Ensure system:index is set
        if "system:index" not in gee_props:
            gee_props["system:index"] = self.asset_id

        # Convert datetime strings to milliseconds if needed
        for time_prop in ["system:time_start", "system:time_end"]:
            if time_prop in gee_props:
                gee_props[time_prop] = _normalize_timestamp(gee_props[time_prop])

        # Convert lists to JSON strings for system:tags
        if "system:tags" in gee_props and isinstance(gee_props["system:tags"], list):
            gee_props["system:tags"] = gee_props["system:tags"]

        return gee_props


class MetadataCollection(BaseModel):
    """Collection of metadata entries with validation."""

    entries: Dict[str, MetadataEntry] = Field(default_factory=dict)

    def get(self, asset_id: str) -> Optional[Dict[str, Any]]:
        """Get GEE properties for an asset."""
        entry = self.entries.get(asset_id)
        return entry.to_gee_properties() if entry else None

    def has_metadata(self, asset_id: str) -> bool:
        """Check if metadata exists for an asset."""
        return asset_id in self.entries

    def validate_all_assets_present(self, asset_ids: Set[str]) -> List[str]:
        """Check which assets are missing metadata."""
        return [aid for aid in asset_ids if aid not in self.entries]

    @classmethod
    def from_csv(cls, path: Path, id_column: str = None) -> "MetadataCollection":
        """
        Load metadata from CSV file.

        CSV Format:
        - First column: asset identifier (filename without extension)
        - Remaining columns: properties

        Example:
        ```
        asset_id,system:index,class,category,binomial,system:time_start
        file_1,my_file_1,GASTROPODA,EN,Aaadonta constricta,2024-01-01
        file_2,my_file_2,GASTROPODA,CR,Aaadonta irregularis,2024-01-15
        ```

        Args:
            path: Path to CSV file
            id_column: Name of the ID column (if None, uses first column)

        Returns:
            MetadataCollection
        """
        if not path.exists():
            raise FileNotFoundError(f"Metadata file not found: {path}")

        entries = {}

        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            if not reader.fieldnames:
                raise ValueError("CSV file is empty or has no header")

            # Determine ID column
            if id_column is None:
                id_column = reader.fieldnames[0]

            if id_column not in reader.fieldnames:
                raise ValueError(
                    f"ID column '{id_column}' not found in CSV. "
                    f"Available columns: {reader.fieldnames}"
                )

            # Validate header
            for col in reader.fieldnames:
                if col != id_column and not _is_valid_property_key(col):
                    raise PropertyValidationError(
                        f"Invalid column name '{col}'. Must be a system property "
                        f"or contain only letters, numbers, and underscores."
                    )

            # Load entries
            for row_num, row in enumerate(reader, start=2):
                try:
                    asset_id = row[id_column]
                    if not asset_id:
                        logger.warning(f"Skipping row {row_num}: empty asset ID")
                        continue

                    # Build properties dict
                    properties = {}
                    for col, value in row.items():
                        if col == id_column:
                            continue

                        # Skip empty values
                        if value is None or value == "":
                            continue

                        # Try to parse value
                        parsed_value = _parse_value(value)
                        properties[col] = parsed_value

                    # Create and validate entry
                    entry = MetadataEntry(asset_id=asset_id, properties=properties)

                    entries[asset_id] = entry

                except Exception as e:
                    logger.error(f"Error processing row {row_num}: {e}")
                    raise PropertyValidationError(
                        f"Row {row_num} validation failed: {e}"
                    ) from e

        logger.info(f"Loaded metadata for {len(entries)} assets from {path}")
        return cls(entries=entries)


def _is_valid_property_key(key: str) -> bool:
    """Check if property key is valid for GEE."""
    import re

    return key in GEE_SYSTEM_PROPERTIES or bool(re.match(r"^[A-Za-z0-9_]+$", key))


def _is_valid_property_value(value: Any) -> bool:
    """Check if property value is valid."""
    if value is None or value == "":
        return False

    # GEE supports: strings, numbers, booleans, lists, dicts
    if isinstance(value, (str, int, float, bool)):
        return True

    if isinstance(value, list):
        return all(_is_valid_property_value(v) for v in value)

    if isinstance(value, dict):
        return all(
            isinstance(k, str) and _is_valid_property_value(v) for k, v in value.items()
        )

    return False


def _parse_value(value: str) -> Any:
    """Parse string value into appropriate Python type."""
    import ast

    # Try to evaluate as Python literal
    try:
        parsed = ast.literal_eval(value)
        # Only accept safe types
        if isinstance(parsed, (int, float, bool, list, dict, tuple)):
            return list(parsed) if isinstance(parsed, tuple) else parsed
    except (ValueError, SyntaxError):
        pass

    # Try to parse as ISO datetime
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        # Convert to milliseconds since epoch
        return int(dt.timestamp() * 1000)
    except (ValueError, AttributeError):
        pass

    # Return as string
    return value


def _normalize_timestamp(value: Any) -> Optional[int]:
    """Convert timestamp to milliseconds since epoch."""
    if value is None:
        return None

    if isinstance(value, int):
        # Assume milliseconds
        return value

    if isinstance(value, str):
        try:
            # Try ISO format
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return int(dt.timestamp() * 1000)
        except ValueError:
            # Try as integer string
            try:
                return int(value)
            except ValueError:
                pass

    return None


# Backward compatibility with old API
def validate_metadata_from_csv(path: Union[str, Path]) -> tuple:
    """
    Legacy function for backward compatibility.
    Returns (success, keys) tuple.
    """
    try:
        collection = MetadataCollection.from_csv(Path(path))
        keys = list(collection.entries.keys())
        return (True, keys)
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        return (False, [])


def load_metadata_from_csv(path: Union[str, Path]) -> Dict[str, Dict[str, Any]]:
    """
    Legacy function for backward compatibility.
    Returns dict of dicts.
    """
    collection = MetadataCollection.from_csv(Path(path))
    return {
        asset_id: entry.to_gee_properties()
        for asset_id, entry in collection.entries.items()
    }

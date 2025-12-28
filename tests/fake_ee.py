"""Enhanced fake ee module for comprehensive testing."""

import box


class Image:
    def __init__(self, *_, **__):
        pass

    @classmethod
    def constant(cls, *_, **__):
        return Image()

    def getMapId(self, *_, **__):
        return box.Box({"tile_fetcher": {"url_format": "url-format"}})

    def updateMask(self, *_, **__):
        return self

    def blend(self, *_, **__):
        return self

    def bandNames(self, *_, **__):
        return List(["B1", "B2"])

    def reduceRegion(self, *_, **__):
        return Dictionary({"B1": 42, "B2": 3.14})

    def getInfo(self):
        return {
            "type": "Image",
            "bands": [
                {
                    "id": "band-1",
                    "data_type": {
                        "type": "PixelType",
                        "precision": "int",
                        "min": -2,
                        "max": 2,
                    },
                    "dimensions": [4, 2],
                    "crs": "EPSG:4326",
                    "crs_transform": [1, 0, -180, 0, -1, 84],
                },
            ],
            "version": 42,
            "id": "some/image/id",
            "properties": {
                "type_name": "Image",
                "keywords": ["keyword-1", "keyword-2"],
                "thumb": "https://some-thumbnail.png",
                "system:asset_size": 1000000,
            },
        }


class List:
    def __init__(self, items, *_, **__):
        self.items = items

    def getInfo(self, *_, **__):
        return self.items


class Dictionary:
    def __init__(self, data):
        self.data = data

    def getInfo(self):
        return self.data


class ReduceRegionResult:
    def getInfo(self):
        return {}


class Geometry:
    geometry = None

    def __init__(self, *args, **kwargs):
        if len(args):
            self.geometry = args[0]
        if kwargs.get("type"):
            self.geom_type = kwargs.get("type")

    @classmethod
    def Point(cls, *_, **__):
        return Geometry(type=String("Point"))

    @classmethod
    def BBox(cls, *_, **__):
        return Geometry(type=String("BBox"))

    @classmethod
    def Polygon(cls, *_, **__):
        return Geometry(type=String("Polygon"))

    def transform(self, *_, **__):
        return Geometry(type=self.geom_type)

    def bounds(self, *_, **__):
        return Geometry.Polygon()

    def centroid(self, *_, **__):
        return Geometry.Point()

    def type(self, *_, **__):
        return self.geom_type

    def getInfo(self, *_, **__):
        if self.type().value == "Polygon":
            return {
                "geodesic": False,
                "type": "Polygon",
                "coordinates": [
                    [[-178, -76], [179, -76], [179, 80], [-178, 80], [-178, -76]]
                ],
            }
        if self.type().value == "Point":
            return {
                "geodesic": False,
                "type": "Point",
                "coordinates": [120, -70],
            }
        if self.type().value == "BBox":
            return {
                "geodesic": False,
                "type": "Polygon",
                "coordinates": [[0, 1], [1, 2], [0, 1]],
            }
        raise ValueError("Unexpected geometry type in test: ", self.type().value)

    def __eq__(self, other: object):
        return self.geometry == getattr(other, "geometry", None)


class String:
    def __init__(self, value):
        self.value = value

    def compareTo(self, other_str):
        return self.value == other_str.value

    def getInfo(self, *_, **__):
        return self.value


class FeatureCollection:
    features = []

    def __init__(self, *args, **_):
        if len(args):
            self.features = args[0]

    def style(self, *_, **__):
        return Image()

    def first(self, *_, **__):
        return Feature()

    def filterBounds(self, *_, **__):
        return FeatureCollection()

    def geometry(self, *_, **__):
        return Geometry.Polygon()

    def aggregate_array(self, *_, **__):
        return List(["aggregation-one", "aggregation-two"])
    
    def size(self):
        return MockNumber(len(self.features))
    
    def get(self, prop):
        return MockComputedObject(1000000)

    def __eq__(self, other: object):
        return self.features == getattr(other, "features", None)


class Feature:
    feature = None
    properties = None

    def __init__(self, *args, **_):
        if len(args) > 0:
            self.feature = args[0]
        if len(args) >= 2:
            self.properties = args[1]

    def geometry(self, *_, **__):
        return Geometry(type=String("Polygon"))

    def getInfo(self, *_, **__):
        return {
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": [[-67.1, 46.2], [-67.3, 46.4], [-67.5, 46.6]],
            },
            "id": "00000000000000000001",
            "properties": {
                "fullname": "some-full-name",
                "linearid": "110469267091",
                "mtfcc": "S1400",
                "rttyp": "some-rttyp",
            },
        }

    def __eq__(self, other: object):
        featuresEqual = self.feature == getattr(other, "feature", None)
        propertiesEqual = self.properties == getattr(other, "properties", None)
        return featuresEqual and propertiesEqual

    def propertyNames(self, *_, **__):
        return List(["prop-1", "prop-2"])


class MockNumber:
    """Mock for ee.Number-like objects."""
    def __init__(self, value):
        self._value = value
    
    def getInfo(self):
        return self._value


class MockComputedObject:
    """Mock for computed objects."""
    def __init__(self, value):
        self._value = value
    
    def getInfo(self):
        return self._value


class ImageCollection:
    def __init__(self, images=None, *_, **__):
        if images is None:
            images = []
        self.images = images if isinstance(images, list) else [images]

    @classmethod
    def fromImages(cls, images):
        return ImageCollection(images)

    def mosaic(self, *_, **__):
        return Image()
    
    def aggregate_array(self, prop):
        """Mock aggregate_array to return asset sizes."""
        if prop == "system:asset_size":
            return List([1000000, 2000000, 500000])
        return List([])
    
    def size(self):
        return MockNumber(len(self.images))

    def getInfo(self):
        return {
            "type": "ImageCollection",
            "bands": [],
            "features": [f.getInfo() if hasattr(f, 'getInfo') else {} for f in self.images],
        }


class Reducer:
    @classmethod
    def first(cls, *_, **__):
        return Reducer()


class Algorithms:
    @classmethod
    def If(cls, *_, **__):
        return Algorithms()


class EEException(Exception):
    """Mock Earth Engine exception."""
    pass


class DataModule:
    """Mock ee.data module."""
    
    @staticmethod
    def get_persistent_credentials():
        """Mock credentials."""
        class MockCredentials:
            pass
        return MockCredentials()
    
    @staticmethod
    def getTaskList():
        """Mock task list."""
        return [
            {
                'id': 'task-1',
                'state': 'RUNNING',
                'description': 'Test export',
                'task_type': 'EXPORT_IMAGE',
                'attempt': 1,
                'start_timestamp_ms': 1609459200000,
                'update_timestamp_ms': 1609462800000,
            }
        ]
    
    @staticmethod
    def getTaskStatus(task_ids):
        """Mock task status."""
        return [{'state': 'RUNNING', 'id': task_ids[0]}]
    
    @staticmethod
    def cancelTask(task_id):
        """Mock cancel task."""
        pass
    
    @staticmethod
    def getAsset(asset_path):
        """Mock get asset."""
        if 'image' in asset_path.lower():
            return {'type': 'IMAGE'}
        elif 'collection' in asset_path.lower():
            return {'type': 'IMAGE_COLLECTION'}
        elif 'folder' in asset_path.lower():
            return {'type': 'FOLDER'}
        elif 'table' in asset_path.lower():
            return {'type': 'TABLE', 'sizeBytes': '1000000', 'featureCount': 100}
        return {'type': 'IMAGE'}
    
    @staticmethod
    def getInfo(path):
        """Mock get info."""
        return {
            'quota': {
                'sizeBytes': '5000000000',
                'maxSizeBytes': '10000000000',
                'assetCount': '50',
                'maxAssets': '1000'
            }
        }
    
    @staticmethod
    def getAssetRoots():
        """Mock get asset roots."""
        return [
            {'id': 'projects/test-project/assets'},
            {'id': 'users/testuser/assets'}
        ]
    
    @staticmethod
    def getAssetRootQuota(root_path):
        """Mock get asset root quota."""
        return {
            'asset_size': {
                'usage': 5000000000,
                'limit': 10000000000
            },
            'asset_count': {
                'usage': 50,
                'limit': 1000
            }
        }


# Module-level data object
data = DataModule()


def Initialize(*_, **__):
    """Mock Earth Engine initialization."""
    pass

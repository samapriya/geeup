# Delete Assets tool

The Delete Assets tool in geeup is a powerful utility designed to facilitate asset management within Google Earth Engine (GEE). This tool empowers users to perform recursive deletions of Earth Engine assets, including folders, collections, images, and their child assets. However, it is important to exercise caution while using this tool, as it permanently removes assets and their associated data.

#### Key Features

- **Comprehensive Asset Deletion**: The Delete Assets tool allows users to perform recursive deletions of assets, ensuring that entire hierarchies of assets can be removed with a single command.

- **Use with Caution**: Due to the recursive nature of this tool, it will delete not only the specified asset but also all its child assets, including images, collections, and folders. Therefore, it is essential to use this tool with caution to avoid unintentional data loss.

#### Usage

Using the Delete Assets tool is straightforward, requiring only the specification of the target Earth Engine asset for deletion.

```bash
geeup delete --id "asset_path_to_delete"
```

- `--id`: The full path to the asset you want to delete. This tool will recursively remove all child assets, including images, collections, and folders associated with the specified asset.

#### Example

Here's an example demonstrating how to use the Delete Assets tool to remove an Earth Engine asset and all its child assets:

```bash
geeup delete --id "users/your_username/your_collection"
```

![geeup_delete](https://user-images.githubusercontent.com/6677629/114294621-880f2380-9a65-11eb-9180-7d9ea2108dac.gif)

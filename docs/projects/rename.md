# Rename tool

geeup's `rename` command is a straightforward tool designed to help you conform to Google Earth Engine's path naming rules. It ensures that filenames adhere to GEE guidelines, which include allowing only hyphens, underscores, letters, and numbers, with no spaces. This tool performs in-place renaming, meaning it updates the filenames at their existing locations, so use it with caution.

## Key Features

- **Path Renaming**: Easily rename filenames to comply with Google Earth Engine's path naming requirements.

- **GEE Rules Compliance**: Ensure that your filenames contain only hyphens, underscores, letters, and numbers, following GEE's naming conventions.

- **In-Place Renaming**: geeup's `rename` command updates filenames directly at their current locations, reducing the need for additional file management steps.

#### Usage

```bash
geeup rename -h

usage: geeup rename [-h] --input INPUT

optional arguments:
  -h, --help             show this help message and exit

Required named arguments:
  --input INPUT          Path to the input directory with all files to be uploaded
```

#### Example

Here's an example of how to use the `rename` command with geeup:

![geeup Rename Example](https://user-images.githubusercontent.com/6677629/169738141-b032f14b-7b26-441a-96bd-a4eadeaeba7a.gif)

Simply provide the path to the directory containing the files you want to rename, and geeup will take care of the rest. It ensures that your filenames are in compliance with Google Earth Engine's naming conventions, facilitating a smoother workflow when working with GEE.

# Delete Assets

The delete is recursive, meaning it will delete also all children assets: images, collections and folders. Use with caution! This tool is merely added to serve as a call to the earthengine function ```earthengine rm -r "path to collection"```.

![geeup_delete](https://user-images.githubusercontent.com/6677629/114294621-880f2380-9a65-11eb-9180-7d9ea2108dac.gif)

```
> geeup delete -h
usage: geeup delete [-h] --id ID

optional arguments:
  -h, --help  show this help message and exit

Required named arguments.:
  --id ID     Full path to asset for deletion. Recursively removes all
              folders, collections and images.
```

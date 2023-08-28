# oci-pull-n-rootfs
This is was a hobby project to better understand the nitty-gritty of OCI image spec. It pulls from a OCI image repo and after untaring layers it creates the root filesystem needed for the OCI compatibale runtime to actually run the image.
It also creates a `manifest.json` file so that docker import could work on it.
The config needed to run the image using runc needs further translation from the current `config.json` to the actual one.

To compile a devicetree binary from source

  dtc -I dts -O dtb -o output.dtbo input.dts

To decompile a devictree binary to a source

  dtc -I dtb -O dts -o output.dts input.dtbo

Copy the resulting binary file to /boot/overlays 
Update /boot/config.txt (or modify local config.txt and copy over)
Reboot

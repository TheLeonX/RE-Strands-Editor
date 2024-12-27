###### BETA RELEASE, MIGHT HAVE BUGS
![logo](https://github.com/user-attachments/assets/61bf6246-9d20-46e0-83ba-8454bbf5468b)

This addon allows for importing and exporting of Resident evil 4 Remake hair strands files natively in Blender.
## [Download RE Strands Editor](https://github.com/user-attachments/files/18262070/RE-Strands-Editor.zip)

![1](https://github.com/user-attachments/assets/3ced8d0c-bff3-41e0-aaf4-2540465d4246)

## Features
- Allows for importing and exporting of RE4R hair strands files.

## Supported Games
- Resident Evil 4 Remake

## Requirements
- [Blender v4.2 or higher](https://www.blender.org/download/)
- [RE Mesh Editor](https://github.com/NSACloud/RE-Mesh-Editor)
> RE Mesh Editor is required for loading surface/scalp meshes for modifying hair strands.

## Installation
Download the addon from the "Download RE Strands Editor" link at the top or click Code > Download Zip.

In Blender, go to Edit > Preferences > Addons, then click "Install" in the top right.

NOTE: If you are on Blender 4.2 or above, the install button is found by clicking the arrow in the top right of the addon menu.
![3](https://github.com/user-attachments/assets/cc3d238c-ed34-497c-8634-bba55ba2ed9e)
Navigate to the downloaded zip file for this addon and click "Install Addon". The addon should then be usable.

## FAQ / Troubleshooting
- Hair strands doesn't get attached to head.
  
This issue coming from .sbd.7 file, if you are creating hair strands from scratch, its highly recommend to check "Create .sbd file" flag on export. This is still experimental addon and will require fixes in future. At this moment .sbd files generating using surface UV map and using one of the values which worked great in game.


- Hair disappear when I trying to make hair strands for fully new character model.

  
This issue coming from blend shapes which RE Mesh Editor doesn't support yet. Blend Shapes get erased on export.


- I enabled physics but my long hair strands still looks static.

  
This hair strands were used mostly for short hair and itsnt recommended to use for long hair. For long hair we would need to create new surface/scalp with rigged hair, but we can't do this at this moment, cuz RE Mesh Editor doesn't support blend shapes.


- I tried to change beard for Luis but it looks static and changed colors.


At this moment we can't make rigged meshes cuz of unsupposed blend shapes, so if you want to modify beard - do not edit Luis face, uncheck "Create .sbd file" flag and modify only existing hair (brush them, make them longer and etc). This will save color, rigging and your nerves on trying to fix that issue. As soon as it will be figured out, I will drop an update for it!


For additional help, go here:

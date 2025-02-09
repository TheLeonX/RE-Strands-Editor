###### BETA RELEASE, MIGHT HAVE BUGS
![logo](https://github.com/user-attachments/assets/aa453e20-4519-40c2-8847-607dba3da598)

This addon allows for importing and exporting of Resident evil 4 Remake hair strands files natively in Blender.
## [Download RE Strands Editor](https://github.com/TheLeonX/RE-Strands-Editor/releases/latest)

![1](https://github.com/user-attachments/assets/3ced8d0c-bff3-41e0-aaf4-2540465d4246)

## Features
- Allows for importing and exporting of RE4R hair strands files.

## Supported Games
- Resident Evil 4 Remake

## Requirements
- [Blender v4.2 or higher](https://www.blender.org/download/)
- [RE Mesh Editor (with blend Shapes)](https://github.com/user-attachments/files/18723656/RE-Mesh-Editor-main.zip)
> RE Mesh Editor is required for loading surface/scalp meshes for modifying hair strands. This version will let you save blend shapes for scalp meshes so your hair strands can get attached properly. This is still experimental and blend shapes can work incorrect for regular meshes, but can work good with hair strands.
- [RszTool](https://github.com/czastack/RszTool)
> RszTool is required for editing .pfb.17 hair strands files which contain a lot of settings such as collision, shader settings and physics.

## Credits
- [NSA Cloud](https://github.com/NSACloud) - RE Mesh Editor
- [czastack](https://github.com/czastack) - RszTool
## Installation
Download the addon from the "Download RE Strands Editor" link at the top or click Code > Download Zip.

In Blender, go to Edit > Preferences > Addons, then click "Install" in the top right.

NOTE: If you are on Blender 4.2 or above, the install button is found by clicking the arrow in the top right of the addon menu.
![3](https://github.com/user-attachments/assets/cc3d238c-ed34-497c-8634-bba55ba2ed9e)

Navigate to the downloaded zip file for this addon and click "Install Addon". The addon should then be usable.

## FAQ / Troubleshooting
- Hair strands doesn't get attached to head.
  
That issue coming from .sbd.7 file, if you are creating hair strands from scratch, its highly recommend to check "Create .sbd file" flag on export.

- Hair disappear when I trying to make hair strands for fully new character model.

  
That issue coming from blend shapes which RE Mesh Editor doesn't support yet. Blend Shapes get erased on export.
I made experimental build which can create blend shapes for hair strands. Addon is made originally by [NSA Cloud](https://github.com/NSACloud/RE-Mesh-Editor)

Experimental Build -> [RE-Mesh-Editor-main.zip](https://github.com/user-attachments/files/18723656/RE-Mesh-Editor-main.zip)

- My hair looks different, doesn't have proper color or looks scaled if I enable physics for it.

That issue can be fixed by editing .pfb.17 files for hair strands. You will need for that [RszTool](https://github.com/czastack/RszTool).
This file contain a lot of settings, such as collisions, physics and some other settings.


For additional info, check this [Wiki](https://github.com/TheLeonX/RE-Strands-Editor/wiki) 
If you want to support me, here is my **[Boosty](https://boosty.to/theleonx/donate)**.

# Blender Quake MDL2 Import / Export

(Works with blender 2.93)

This script is an importer and exporter for the Kingpin (and Quake) Model md2 and mdx.

The frames are named <frameName><N> with :<br>

- <N> the frame number<br>
- <frameName> the name choosen at the last marker
  (or 'frame' if the last marker has no name or if there is no last marker)

Skins are set using image textures in materials, if it is longer than 63 characters it is truncated.

Thanks to:

- DarkRain
- Bob Holcomb. for MD2_NORMALS taken from his exporter.
- David Henry. for the documentation about the MD2 file format.
- Bob Holcomb
- Sebastian Lieberknecht
- Dao Nguyen
- Bernd Meyer
- Damien Thebault
- Erwan Mathieu
- Takehiko Nawata

# hypov8 log

v1.1.1 (blender 2.79)

- fix teture bug
- added importing of GL commands. for enhanced uv pricision
- added skin search path for texcture not im nodel folder
- added multi part player model bbox fix. all parts must be visable in sceen
- fixed texture issue in glCommands. not checking for uv match, just vertex id

v1.2.0 (blender 2.80) jan 2020

- updated to work with new blender
- merged md2/mdx into 1 script
- loading/saving allows selection of both file types
- option for imported models to set timeline range if animated
- multi model selection support for exports
- hitbox will be created for each selected object

v1.2.1 (blender 2.80) nov 2020

- fixed a texture missing bug
- fixed texture string formatting
- export no longer fails if a skin was not found
- fixed skin string issue being null
- added matrix for non shape key exports

notes:

- setup model textures by adding using node and add an image for diffuse->color

todo:

- import. split model into mdx groups

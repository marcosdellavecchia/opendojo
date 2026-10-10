// Shaders for the open_dojo map and the map compiler.

textures/common/caulk
{
	surfaceparm nodraw
	surfaceparm nomarks
	surfaceparm nolightmap
}

textures/common/clip
{
	surfaceparm nodraw
	surfaceparm nolightmap
	surfaceparm nonsolid
	surfaceparm trans
	surfaceparm nomarks
	surfaceparm noimpact
	surfaceparm playerclip
}

textures/open/light
{
	qer_editorimage textures/open/light.jpg
	q3map_surfacelight 1200
	q3map_lightsubdivide 64
	surfaceparm nomarks
	{
		map $lightmap
	}
	{
		map textures/open/light.jpg
		blendFunc GL_DST_COLOR GL_ZERO
	}
	{
		map textures/open/light.jpg
		blendFunc GL_ONE GL_ONE
	}
}

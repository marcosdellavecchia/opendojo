// Shaders the engine and the game code ask for by name, written for the
// open pack.

white
{
	{
		map $whiteimage
		blendfunc GL_SRC_ALPHA GL_ONE_MINUS_SRC_ALPHA
		rgbgen vertex
		alphagen vertex
	}
}

console
{
	nopicmip
	nomipmaps
	{
		map gfx/open/console.tga
		blendfunc GL_SRC_ALPHA GL_ONE_MINUS_SRC_ALPHA
	}
}

ui/open/cursor
{
	nopicmip
	nomipmaps
	{
		map ui/open/cursor.tga
		blendfunc GL_SRC_ALPHA GL_ONE_MINUS_SRC_ALPHA
		rgbgen vertex
	}
}

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

// JK2MV draws the console with the font r_consoleFont picks (1, its
// default: code_new_roman; 2: mplus_1m_bold) in place of charsgrid_med:
// all three are the pack's one console font.
gfx/2d/code_new_roman
{
	nopicmip
	nomipmaps
	{
		clampmap gfx/2d/charsgrid_med.tga
		blendfunc GL_SRC_ALPHA GL_ONE_MINUS_SRC_ALPHA
		rgbgen vertex
		alphagen vertex
	}
}

gfx/2d/mplus_1m_bold
{
	nopicmip
	nomipmaps
	{
		clampmap gfx/2d/charsgrid_med.tga
		blendfunc GL_SRC_ALPHA GL_ONE_MINUS_SRC_ALPHA
		rgbgen vertex
		alphagen vertex
	}
}

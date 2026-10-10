// Console for the browser build: engine output goes to the browser's
// developer console, one line at a time, without Q3 colour codes.
// There is no terminal input; use the in-game console.

#include <emscripten/console.h>

#include "../qcommon/q_shared.h"
#include "../qcommon/qcommon.h"
#include "../sys/con_local.h"

static char	conLine[4096];
static int	conLineLength;

void CON_Init( void ) {
}

void CON_Shutdown( void ) {
	if ( conLineLength ) {
		CON_Print( "\n", false );
	}
}

void CON_CreateConsoleWindow() {}
void CON_DeleteConsoleWindow() {}

char *CON_Input( void ) {
	return NULL;
}

void CON_Print( const char *msg, bool extendedColors ) {
	for ( const char *c = msg; *c; c++ ) {
		if ( Q_IsColorString( c ) || ( extendedColors && Q_IsColorString_Extended( c ) ) ) {
			c++;
			continue;
		}

		if ( *c == '\n' || conLineLength == sizeof(conLine) - 1 ) {
			conLine[conLineLength] = '\0';
			emscripten_out( conLine );
			conLineLength = 0;
			if ( *c == '\n' ) {
				continue;
			}
		}

		conLine[conLineLength++] = *c;
	}
}

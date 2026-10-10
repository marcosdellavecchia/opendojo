// Networking for the browser build.
//
// Browsers can't send UDP packets, so every packet goes through a WebSocket
// to a relay (web/server.mjs) that forwards it to the real UDP address and
// sends the replies back. Servers see a normal UDP client.
//
// The WebSocket itself is opened by the page (Module.jk2net in web/main.js);
// this file only frames and unframes packets. Every WebSocket message is
//
//   [type:1][ip:4][port:2 big endian][body]
//
//   type 0 (both ways): a UDP packet; ip/port are the destination when
//                       sending and the source when receiving
//   type 1 (to relay):  body is a host name the relay must resolve; packets
//                       sent to ip (an alias in 240.0.0.0/8) go to that host
//
// Name aliases keep Sys_StringToAdr synchronous, since browsers can't resolve
// DNS: the relay resolves the name and rewrites the source of the replies
// back to the alias.

#include <emscripten.h>
#include <arpa/inet.h>

#include "../qcommon/qcommon.h"

static cvar_t	*net_enabled;
static cvar_t	*net_forcenonlocal;
static cvar_t	*net_ip;
static cvar_t	*net_port;
static cvar_t	*net_dropsim;

static qboolean	networkingEnabled = qfalse;

#define NETWEB_PACKET	0
#define NETWEB_ALIAS	1
#define NETWEB_HEADER	7

#define ALIAS_NET		240
#define MAX_ALIASES		256
static char		aliasNames[MAX_ALIASES][MAX_STRING_CHARS];
static int		numAliases;

EM_JS(void, NETWeb_Send, (const void *buf, int len), {
	var net = Module['jk2net'];
	if (net) net.send(HEAPU8.slice(buf, buf + len));
});

// Copies the next received message into buf and returns its length, or -1
// if there is none. Messages larger than maxlen are dropped (returns 0).
EM_JS(int, NETWeb_Recv, (void *buf, int maxlen), {
	var net = Module['jk2net'];
	if (!net || !net.queue.length) return -1;
	var msg = net.queue.shift();
	if (msg.length > maxlen) return 0;
	HEAPU8.set(msg, buf);
	return msg.length;
});

static void NETWeb_SendFrame( int type, const byte *ip, unsigned short port, const void *body, int len ) {
	static byte frame[NETWEB_HEADER + MAX_MSGLEN + MAX_STRING_CHARS];

	if ( len < 0 || len > (int)sizeof(frame) - NETWEB_HEADER ) {
		return;
	}

	frame[0] = (byte)type;
	memcpy( &frame[1], ip, 4 );
	memcpy( &frame[5], &port, 2 );	// netadr_t ports are already big endian
	memcpy( &frame[NETWEB_HEADER], body, len );
	NETWeb_Send( frame, NETWEB_HEADER + len );
}

static void NETWeb_AliasToIP( int alias, byte *ip ) {
	ip[0] = ALIAS_NET;
	ip[1] = 0;
	ip[2] = (byte)(alias >> 8);
	ip[3] = (byte)alias;
}

/*
=============
Sys_StringToAdr
=============
*/
qboolean Sys_StringToAdr( const char *s, netadr_t *a ) {
	struct in_addr	addr;
	int				i;

	Com_Memset( a, 0, sizeof(*a) );
	a->type = NA_IP;

	if ( inet_pton( AF_INET, s, &addr ) == 1 ) {
		memcpy( a->ip, &addr, 4 );
		return qtrue;
	}

	// a host name: hand it to the relay under an alias address
	for ( i = 0; i < numAliases; i++ ) {
		if ( !Q_stricmp( aliasNames[i], s ) ) {
			break;
		}
	}

	if ( i == numAliases ) {
		if ( numAliases == MAX_ALIASES ) {
			return qfalse;
		}
		Q_strncpyz( aliasNames[i], s, sizeof(aliasNames[i]) );
		numAliases++;
	}

	NETWeb_AliasToIP( i, a->ip );
	NETWeb_SendFrame( NETWEB_ALIAS, a->ip, 0, aliasNames[i], strlen(aliasNames[i]) );
	return qtrue;
}

/*
==================
Sys_SendPacket
==================
*/
void Sys_SendPacket( int length, const void *data, netadr_t to ) {
	if ( to.type != NA_BROADCAST && to.type != NA_IP ) {
		Com_Error( ERR_FATAL, "Sys_SendPacket: bad address type" );
		return;
	}

	// there is no LAN to broadcast to from a browser
	if ( to.type == NA_BROADCAST || !networkingEnabled ) {
		return;
	}

	NETWeb_SendFrame( NETWEB_PACKET, to.ip, to.port, data, length );
}

/*
==================
Sys_IsLANAddress

LAN clients will have their rate var ignored
==================
*/
qboolean Sys_IsLANAddress( netadr_t adr ) {
	if ( net_forcenonlocal && net_forcenonlocal->integer )
		return qfalse;

	if ( adr.type == NA_LOOPBACK )
		return qtrue;

	if ( adr.type != NA_IP )
		return qfalse;

	// RFC1918
	if ( adr.ip[0] == 10 )
		return qtrue;
	if ( adr.ip[0] == 172 && (adr.ip[1]&0xf0) == 16 )
		return qtrue;
	if ( adr.ip[0] == 192 && adr.ip[1] == 168 )
		return qtrue;
	if ( adr.ip[0] == 127 )
		return qtrue;

	return qfalse;
}

/*
==================
Sys_ShowIP
==================
*/
void Sys_ShowIP( void ) {
	Com_Printf( "Packets go through the WebSocket relay; there is no local IP.\n" );
}

/*
====================
NET_GetCvars
====================
*/
static qboolean NET_GetCvars( void ) {
	int	modified;

	net_enabled = Cvar_Get( "net_enabled", "1", CVAR_LATCH | CVAR_ARCHIVE | CVAR_GLOBAL );
	modified = net_enabled->modified;
	net_enabled->modified = qfalse;

	net_forcenonlocal = Cvar_Get( "net_forcenonlocal", "0", CVAR_LATCH | CVAR_ARCHIVE | CVAR_GLOBAL );
	modified += net_forcenonlocal->modified;
	net_forcenonlocal->modified = qfalse;

	// unused, kept so scripts that set them don't fail
	net_ip = Cvar_Get( "net_ip", "localhost", CVAR_LATCH );
	net_port = Cvar_Get( "net_port", XSTRING( PORT_SERVER ), CVAR_LATCH );

	net_dropsim = Cvar_Get( "net_dropsim", "", CVAR_TEMP | CVAR_CHEAT );

	return modified ? qtrue : qfalse;
}

/*
====================
NET_Config
====================
*/
void NET_Config( qboolean enableNetworking ) {
	NET_GetCvars();

	if ( !net_enabled->integer )
		enableNetworking = qfalse;

	networkingEnabled = enableNetworking;
}

/*
====================
NET_Init
====================
*/
void NET_Init( void ) {
	NET_Config( qtrue );

	Cmd_AddCommand( "net_restart", NET_Restart_f );
}

/*
====================
NET_Shutdown
====================
*/
void NET_Shutdown( void ) {
	if ( !networkingEnabled ) {
		return;
	}

	NET_Config( qfalse );
}

/*
====================
NET_Sleep

Can't block in a browser: delivers the packets the WebSocket has received
since the last call and returns.
====================
*/
void NET_Sleep( int msec ) {
	static byte	bufData[NETWEB_HEADER + MAX_MSGLEN + 1];
	netadr_t	from;
	msg_t		netmsg;
	int			len;

	while ( ( len = NETWeb_Recv( bufData, sizeof(bufData) ) ) >= 0 ) {
		if ( len < NETWEB_HEADER || bufData[0] != NETWEB_PACKET || !networkingEnabled ) {
			continue;
		}

		Com_Memset( &from, 0, sizeof(from) );
		from.type = NA_IP;
		memcpy( from.ip, &bufData[1], 4 );
		memcpy( &from.port, &bufData[5], 2 );

		if ( len - NETWEB_HEADER > MAX_MSGLEN ) {
			Com_Printf( "Oversize packet from %s\n", NET_AdrToString( from ) );
			continue;
		}

		if ( net_dropsim->value > 0.0f && net_dropsim->value <= 100.0f ) {
			// net_dropsim->value percent of incoming packets get dropped.
			if ( rand() < (int)(((double)RAND_MAX) / 100.0 * (double)net_dropsim->value) )
				continue;
		}

		MSG_Init( &netmsg, &bufData[NETWEB_HEADER], MAX_MSGLEN + 1 );
		netmsg.cursize = len - NETWEB_HEADER;
		netmsg.readcount = 0;

		if ( com_sv_running->integer )
			Com_RunAndTimeServerPacket( &from, &netmsg );
		else
			CL_PacketEvent( from, &netmsg );
	}
}

/*
====================
NET_Restart_f
====================
*/
void NET_Restart_f( void ) {
	NET_Config( qtrue );
}

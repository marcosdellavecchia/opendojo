// HTTP server and downloads for the browser build: not supported yet.
// A browser can't host the server's HTTP downloads, and the client falls
// back to downloading over UDP (see CL_BeginDownload).

#include "../qcommon/qcommon.h"

void NET_HTTP_Init() {
}

void NET_HTTP_Shutdown() {
}

void NET_HTTP_ProcessEvents() {
}

void NET_HTTP_AllowClient(int clientNum, netadr_t addr) {
}

void NET_HTTP_DenyClient(int clientNum) {
}

int NET_HTTP_StartServer(int port) {
	return 0;
}

void NET_HTTP_StopServer() {
}

dlHandle_t NET_HTTP_StartDownload(const char *url, const char *toPath, dl_ended_callback ended_callback, dl_status_callback status_callback) {
	ended_callback(0, qfalse, "HTTP downloads are not supported in the browser");
	return 0;
}

void NET_HTTP_StopDownload(dlHandle_t handle) {
}

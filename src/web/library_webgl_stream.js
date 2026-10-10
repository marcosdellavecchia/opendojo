// Faster client-side vertex arrays for WebGL (Emscripten JS library).
//
// gl4es draws the renderer's geometry from client memory, which Emscripten's
// FULL_ES2 mode emulates by copying it into temporary buffers before every
// draw. Emscripten updates those buffers in place (bufferSubData) while the
// GPU may still be reading them, and each update waits: that took >90% of
// the frame time. These replacements give the data fresh storage instead
// (bufferData, "orphaning"), which never waits, and accept 32-bit indices.
//
// They replace emscripten_glDrawArrays and emscripten_glDrawElements, which
// is what gl4es calls (through emscripten_GetProcAddress).

addToLibrary({
	$jk2Stream: {
		indexBuffer: null,
		vertexBuffers: [],

		// Uploads the enabled client-side attributes for vertices [0, count).
		uploadClientArrays(count) {
			GL.resetBufferBinding = false;
			for (var i = 0; i < GL.currentContext.maxVertexAttribs; ++i) {
				var cb = GL.currentContext.clientBuffers[i];
				if (!cb.clientside || !cb.enabled) continue;
				GL.resetBufferBinding = true;
				var size = GL.calcBufLength(cb.size, cb.type, cb.stride, count);
				var buf = jk2Stream.vertexBuffers[i] ||= GLctx.createBuffer();
				GLctx.bindBuffer(0x8892 /*GL_ARRAY_BUFFER*/, buf);
				GLctx.bufferData(0x8892 /*GL_ARRAY_BUFFER*/, HEAPU8, 0x88E0 /*GL_STREAM_DRAW*/, cb.ptr, size);
				cb.vertexAttribPointerAdaptor.call(GLctx, i, cb.size, cb.type, cb.normalized, cb.stride, 0);
			}
		},

		hasClientArrays() {
			for (var i = 0; i < GL.currentContext.maxVertexAttribs; ++i) {
				var cb = GL.currentContext.clientBuffers[i];
				if (cb.clientside && cb.enabled) return true;
			}
			return false;
		},
	},

	emscripten_glDrawArrays__deps: ['$jk2Stream'],
	emscripten_glDrawArrays: (mode, first, count) => {
		jk2Stream.uploadClientArrays(first + count);
		GLctx.drawArrays(mode, first, count);
		GL.postDrawHandleClientVertexAttribBindings();
	},

	emscripten_glDrawElements__deps: ['$jk2Stream'],
	emscripten_glDrawElements: (mode, count, type, indices) => {
		var clientIndices = !GLctx.currentElementArrayBufferBinding;

		if (clientIndices) {
			var array;
			switch (type) {
				case 0x1401 /*GL_UNSIGNED_BYTE*/: array = HEAPU8.subarray(indices, indices + count); break;
				case 0x1403 /*GL_UNSIGNED_SHORT*/: array = HEAPU16.subarray(indices >> 1, (indices >> 1) + count); break;
				case 0x1405 /*GL_UNSIGNED_INT*/: array = HEAPU32.subarray(indices >> 2, (indices >> 2) + count); break;
				default:
					GL.recordError(0x500 /*GL_INVALID_ENUM*/);
					return;
			}

			// client-side attributes need the number of vertices the indices use
			if (count > 0 && jk2Stream.hasClientArrays()) {
				var max = 0;
				for (var i = 0; i < count; ++i) if (array[i] > max) max = array[i];
				jk2Stream.uploadClientArrays(max + 1);
			}

			jk2Stream.indexBuffer ||= GLctx.createBuffer();
			GLctx.bindBuffer(0x8893 /*GL_ELEMENT_ARRAY_BUFFER*/, jk2Stream.indexBuffer);
			GLctx.bufferData(0x8893 /*GL_ELEMENT_ARRAY_BUFFER*/, array, 0x88E0 /*GL_STREAM_DRAW*/);
			indices = 0;
		} else {
			// vertex count unknown without reading the bound index buffer;
			// gl4es only uses client-side attributes with client-side indices
			jk2Stream.uploadClientArrays(0);
		}

		GLctx.drawElements(mode, count, type, indices);
		GL.postDrawHandleClientVertexAttribBindings();

		if (clientIndices) {
			GLctx.bindBuffer(0x8893 /*GL_ELEMENT_ARRAY_BUFFER*/, null);
		}
	},
});

/* ============================================================================
 * Thakran OS — Core Wayland Compositor (thakran-compositor)
 * ============================================================================
 * Built on wlroots. Responsible for drawing the desktop, managing windows,
 * and hardware-accelerated effects (blur, shadows) for the glassmorphic UI.
 * ============================================================================
 */

#define _POSIX_C_SOURCE 200809L
#include <assert.h>
#include <getopt.h>
#include <stdbool.h>
#include <stdlib.h>
#include <stdio.h>
#include <time.h>
#include <unistd.h>
#include <wayland-server-core.h>
#include <wlr/backend.h>
#include <wlr/render/allocator.h>
#include <wlr/render/wlr_renderer.h>
#include <wlr/types/wlr_cursor.h>
#include <wlr/types/wlr_compositor.h>
#include <wlr/types/wlr_data_device.h>
#include <wlr/types/wlr_input_device.h>
#include <wlr/types/wlr_keyboard.h>
#include <wlr/types/wlr_matrix.h>
#include <wlr/types/wlr_output.h>
#include <wlr/types/wlr_output_layout.h>
#include <wlr/types/wlr_pointer.h>
#include <wlr/types/wlr_seat.h>
#include <wlr/types/wlr_xcursor_manager.h>
#include <wlr/types/wlr_xdg_shell.h>
#include <wlr/util/log.h>
#include <xkbcommon/xkbcommon.h>

/* For brevity in this foundation build, we create a very minimalistic wlroots 
 * server that boots, shows a background, and allows basic window management.
 * Full blur/shadow shaders would require custom wlr_renderer passes.
 */

struct thakran_server {
    struct wl_display *wl_display;
    struct wlr_backend *backend;
    struct wlr_renderer *renderer;
    struct wlr_allocator *allocator;
    
    struct wlr_compositor *compositor;
    struct wlr_xdg_shell *xdg_shell;
    
    struct wl_listener new_xdg_surface;
    struct wl_list views;
    
    struct wlr_output_layout *output_layout;
    struct wl_list outputs;
    struct wl_listener new_output;
    
    struct wlr_cursor *cursor;
    struct wlr_xcursor_manager *cursor_mgr;
    struct wl_listener cursor_motion;
    struct wl_listener cursor_motion_absolute;
    struct wl_listener cursor_button;
    struct wl_listener cursor_axis;
    struct wl_listener cursor_frame;
    
    struct wlr_seat *seat;
    struct wl_listener new_input;
    struct wl_list keyboards;
};

/* ─── Window Management (Views) ─────────────────────────────────────────── */

struct thakran_view {
    struct wl_list link;
    struct thakran_server *server;
    struct wlr_xdg_toplevel *xdg_toplevel;
    struct wlr_scene_tree *scene_tree;
    struct wl_listener map;
    struct wl_listener unmap;
    struct wl_listener destroy;
    struct wl_listener request_move;
    struct wl_listener request_resize;
    struct wl_listener request_maximize;
    struct wl_listener request_fullscreen;
    int x, y;
};

static void xdg_toplevel_map(struct wl_listener *listener, void *data) {
    struct thakran_view *view = wl_container_of(listener, view, map);
    wl_list_insert(&view->server->views, &view->link);
    /* Focus new window */
    struct wlr_keyboard *keyboard = wlr_seat_get_keyboard(view->server->seat);
    wlr_seat_keyboard_notify_enter(view->server->seat, view->xdg_toplevel->base->surface, keyboard->keycodes, keyboard->num_keycodes, &keyboard->modifiers);
}

static void xdg_toplevel_unmap(struct wl_listener *listener, void *data) {
    struct thakran_view *view = wl_container_of(listener, view, unmap);
    wl_list_remove(&view->link);
}

static void xdg_toplevel_destroy(struct wl_listener *listener, void *data) {
    struct thakran_view *view = wl_container_of(listener, view, destroy);
    wl_list_remove(&view->map.link);
    wl_list_remove(&view->unmap.link);
    wl_list_remove(&view->destroy.link);
    free(view);
}

static void server_new_xdg_surface(struct wl_listener *listener, void *data) {
    struct thakran_server *server = wl_container_of(listener, server, new_xdg_surface);
    struct wlr_xdg_surface *xdg_surface = data;
    
    if (xdg_surface->role != WLR_XDG_SURFACE_ROLE_TOPLEVEL) {
        return;
    }
    
    struct thakran_view *view = calloc(1, sizeof(struct thakran_view));
    view->server = server;
    view->xdg_toplevel = xdg_surface->toplevel;
    
    view->map.notify = xdg_toplevel_map;
    wl_signal_add(&xdg_surface->surface->events.map, &view->map);
    
    view->unmap.notify = xdg_toplevel_unmap;
    wl_signal_add(&xdg_surface->surface->events.unmap, &view->unmap);
    
    view->destroy.notify = xdg_toplevel_destroy;
    wl_signal_add(&xdg_surface->events.destroy, &view->destroy);
}

/* ─── Outputs (Displays) ──────────────────────────────────────────────── */

struct thakran_output {
    struct wl_list link;
    struct thakran_server *server;
    struct wlr_output *wlr_output;
    struct wl_listener frame;
    struct wl_listener destroy;
};

static void output_frame(struct wl_listener *listener, void *data) {
    struct thakran_output *output = wl_container_of(listener, output, frame);
    struct wlr_renderer *renderer = output->server->renderer;
    
    int width, height;
    wlr_output_effective_resolution(output->wlr_output, &width, &height);
    
    wlr_output_attach_render(output->wlr_output, NULL);
    wlr_renderer_begin(renderer, width, height);
    
    /* Thakran Deep Space Background Color (#0a0a0f) */
    float color[4] = {0.039f, 0.039f, 0.059f, 1.0f};
    wlr_renderer_clear(renderer, color);
    
    /* Render windows (stubbed for brevity) */
    
    wlr_renderer_end(renderer);
    wlr_output_commit(output->wlr_output);
}

static void output_destroy(struct wl_listener *listener, void *data) {
    struct thakran_output *output = wl_container_of(listener, output, destroy);
    wl_list_remove(&output->frame.link);
    wl_list_remove(&output->destroy.link);
    wl_list_remove(&output->link);
    free(output);
}

static void server_new_output(struct wl_listener *listener, void *data) {
    struct thakran_server *server = wl_container_of(listener, server, new_output);
    struct wlr_output *wlr_output = data;
    
    wlr_output_init_render(wlr_output, server->allocator, server->renderer);
    
    if (!wl_list_empty(&wlr_output->modes)) {
        struct wlr_output_mode *mode = wlr_output_preferred_mode(wlr_output);
        wlr_output_set_mode(wlr_output, mode);
        wlr_output_enable(wlr_output, true);
        wlr_output_commit(wlr_output);
    }
    
    struct thakran_output *output = calloc(1, sizeof(struct thakran_output));
    output->wlr_output = wlr_output;
    output->server = server;
    
    output->frame.notify = output_frame;
    wl_signal_add(&wlr_output->events.frame, &output->frame);
    
    output->destroy.notify = output_destroy;
    wl_signal_add(&wlr_output->events.destroy, &output->destroy);
    
    wl_list_insert(&server->outputs, &output->link);
    wlr_output_layout_add_auto(server->output_layout, wlr_output);
}

/* ─── Entry Point ──────────────────────────────────────────────────────── */

int main(int argc, char *argv[]) {
    wlr_log_init(WLR_INFO, NULL);
    wlr_log(WLR_INFO, "Starting Thakran OS Compositor...");
    
    struct thakran_server server = {0};
    server.wl_display = wl_display_create();
    server.backend = wlr_backend_autocreate(server.wl_display, NULL);
    server.renderer = wlr_renderer_autocreate(server.backend);
    
    wlr_renderer_init_wl_display(server.renderer, server.wl_display);
    server.allocator = wlr_allocator_autocreate(server.backend, server.renderer);
    
    server.compositor = wlr_compositor_create(server.wl_display, 5, server.renderer);
    wlr_data_device_manager_create(server.wl_display);
    
    server.output_layout = wlr_output_layout_create();
    wl_list_init(&server.outputs);
    server.new_output.notify = server_new_output;
    wl_signal_add(&server.backend->events.new_output, &server.new_output);
    
    wl_list_init(&server.views);
    server.xdg_shell = wlr_xdg_shell_create(server.wl_display, 3);
    server.new_xdg_surface.notify = server_new_xdg_surface;
    wl_signal_add(&server.xdg_shell->events.new_surface, &server.new_xdg_surface);
    
    /* Input/Seat stub... */
    server.seat = wlr_seat_create(server.wl_display, "seat0");
    
    const char *socket = wl_display_add_socket_auto(server.wl_display);
    if (!socket) {
        wlr_log(WLR_ERROR, "Failed to add socket");
        return 1;
    }
    
    if (!wlr_backend_start(server.backend)) {
        wlr_log(WLR_ERROR, "Failed to start backend");
        return 1;
    }
    
    setenv("WAYLAND_DISPLAY", socket, true);
    wlr_log(WLR_INFO, "Thakran Compositor running on WAYLAND_DISPLAY=%s", socket);
    
    /* Autostart desktop shell */
    if (fork() == 0) {
        execl("/bin/sh", "/bin/sh", "-c", "python3 ../shell/panel.py & python3 ../shell/launcher.py", NULL);
    }
    
    wl_display_run(server.wl_display);
    
    wl_display_destroy_clients(server.wl_display);
    wl_display_destroy(server.wl_display);
    
    return 0;
}

// Capture-only virtual pointer. Compile against generated wlr virtual-pointer
// client protocol and wayland-client; connect only to the isolated compositor.
#include <wayland-client.h>
#include "pointer.h"
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
static struct zwlr_virtual_pointer_manager_v1 *manager;
static void global(void *data, struct wl_registry *r, uint32_t name, const char *iface, uint32_t version) {
    if (!strcmp(iface, "zwlr_virtual_pointer_manager_v1"))
        manager = wl_registry_bind(r, name, &zwlr_virtual_pointer_manager_v1_interface, 1);
}
static void removed(void *data, struct wl_registry *r, uint32_t name) {}
static const struct wl_registry_listener listener = {global, removed};
int main(void) {
    struct wl_display *d = wl_display_connect(NULL);
    if (!d) return 1;
    struct wl_registry *r = wl_display_get_registry(d);
    wl_registry_add_listener(r, &listener, NULL);
    wl_display_roundtrip(d);
    if (!manager) return 2;
    struct zwlr_virtual_pointer_v1 *p = zwlr_virtual_pointer_manager_v1_create_virtual_pointer(manager, NULL);
    double x=800,y=600;
    char line[128];
    while (fgets(line,sizeof(line),stdin)) {
        double nx,ny,seconds;
        unsigned button;
        if (sscanf(line,"move %lf %lf %lf",&nx,&ny,&seconds)==3) {
            int frames = seconds*60; if(frames<1)frames=1;
            double sx=x,sy=y;
            for(int i=1;i<=frames;i++) {
                double t=(double)i/frames, e=t*t*(3-2*t);
                x=sx+(nx-sx)*e;y=sy+(ny-sy)*e;
                zwlr_virtual_pointer_v1_motion_absolute(p,0,x,y,1600,1000);
                zwlr_virtual_pointer_v1_frame(p); wl_display_roundtrip(d); usleep(16667);
            }
        } else if(sscanf(line,"click %u",&button)==1) {
            zwlr_virtual_pointer_v1_button(p,0,button,1);
            zwlr_virtual_pointer_v1_frame(p);wl_display_roundtrip(d);usleep(90000);
            zwlr_virtual_pointer_v1_button(p,0,button,0);
            zwlr_virtual_pointer_v1_frame(p);wl_display_roundtrip(d);
        }
        puts("done");fflush(stdout);
    }
    wl_display_disconnect(d);
}

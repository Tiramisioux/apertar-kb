// planes.c: list every DRM plane of /dev/dri/card1 with type, zpos, CRTC mask, current fb and YU12/NV12/AR24 support.
// Read-only (no master needed). Build on the Pi: gcc -O1 planes.c -o planes $(pkg-config --cflags --libs libdrm)
// Used 2026-11-01 to find the HDMI CRTC's primary plane (zpos immutable 0) and the overlay planes (zpos 1-17), and to
// watch the camera framebuffers cycle on the primary plane in APERTAR_PREVIEW_PLANE mode.
#include <string.h>
#include <stdio.h>
#include <fcntl.h>
#include <xf86drm.h>
#include <xf86drmMode.h>

int main(void)
{
    int fd = open("/dev/dri/card1", O_RDWR | O_CLOEXEC);
    if (fd < 0) {
        perror("open");
        return 1;
    }
    drmSetClientCap(fd, DRM_CLIENT_CAP_UNIVERSAL_PLANES, 1);
    drmSetClientCap(fd, DRM_CLIENT_CAP_ATOMIC, 1);
    drmModePlaneRes *r = drmModeGetPlaneResources(fd);
    printf("planes=%u\n", r->count_planes);
    for (unsigned i = 0; i < r->count_planes; i++) {
        drmModePlane *p = drmModeGetPlane(fd, r->planes[i]);
        drmModeObjectProperties *pr = drmModeObjectGetProperties(fd, p->plane_id, DRM_MODE_OBJECT_PLANE);
        long type = -1, zpos = -1;
        int zimm = 0;
        unsigned long zmin = 0, zmax = 0;
        for (unsigned j = 0; j < pr->count_props; j++) {
            drmModePropertyRes *q = drmModeGetProperty(fd, pr->props[j]);
            if (!strcmp(q->name, "type"))
                type = pr->prop_values[j];
            if (!strcmp(q->name, "zpos")) {
                zpos = pr->prop_values[j];
                zimm = !!(q->flags & DRM_MODE_PROP_IMMUTABLE);
                if (q->count_values >= 2) {
                    zmin = q->values[0];
                    zmax = q->values[1];
                }
            }
            drmModeFreeProperty(q);
        }
        int nv12 = 0, yu12 = 0, ar24 = 0;
        for (unsigned k = 0; k < p->count_formats; k++) {
            unsigned f = p->formats[k];
            if (f == 0x3231564e) nv12 = 1;
            if (f == 0x32315559) yu12 = 1;
            if (f == 0x34325241) ar24 = 1;
        }
        printf("plane %u type=%ld zpos=%ld [%lu-%lu]%s crtcs=0x%x fb=%u YU12=%d NV12=%d AR24=%d\n", p->plane_id, type, zpos,
               zmin, zmax, zimm ? " immutable" : "", p->possible_crtcs, p->fb_id, yu12, nv12, ar24);
        drmModeFreeObjectProperties(pr);
        drmModeFreePlane(p);
    }
    return 0;
}

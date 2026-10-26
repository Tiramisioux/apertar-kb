// Host test for apertar-core's src/util/MediaFault.hpp and src/util/MediaProbe.hpp.
// Build: g++ -std=c++20 -Wall -Wextra -I<apertar-core>/src media_probe_test.cpp -o media_probe_test
#include "util/MediaFault.hpp"
#include "util/MediaProbe.hpp"

#include <cstdio>
#include <sstream>

static int failures = 0;
static void check(bool ok, const char *what)
{
    std::printf("  [%s] %s\n", ok ? "ok" : "FAIL", what);
    if (!ok) ++failures;
}

int main()
{
    using namespace apertar;
    std::printf("1. errno classes\n");
    check(classifyMediaErrno(EIO) == MediaFault::Removed, "EIO is removal");
    check(classifyMediaErrno(ENODEV) == MediaFault::Removed, "ENODEV is removal");
    check(classifyMediaErrno(ENOENT) == MediaFault::Removed, "ENOENT (our own clip folder gone) is removal");
    check(classifyMediaErrno(ENOSPC) == MediaFault::Full, "ENOSPC is full");
    check(classifyMediaErrno(EROFS) == MediaFault::ReadOnly, "EROFS is read-only");
    check(classifyMediaErrno(EACCES) == MediaFault::Permission, "EACCES is permission");
    check(classifyMediaErrno(EINVAL) == MediaFault::Other, "EINVAL is other");
    check(classifyMediaErrno(0) == MediaFault::None, "0 is none");

    std::printf("2. exceptions\n");
    const std::system_error se(ENOSPC, std::generic_category(), "Failed to write DNG: /media/RAW/x.dng");
    check(errnoFromException(se) == ENOSPC, "system_error carries its errno");
    check(classifyMediaException(se) == MediaFault::Full, "system_error classifies");
    const std::runtime_error re("failed to write MLV frame");
    check(classifyMediaException(re) == MediaFault::Other, "runtime_error is other");
    check(mediaFaultMessage(MediaFault::Removed, "x") == "Media removed during recording. (x)", "message keeps the detail");
    check(mediaFaultMessage(MediaFault::Other, "") == "Recording write failed.", "other without detail has a default");
    check(std::string(mediaFaultName(MediaFault::Full)) == "media_full", "fault name");
    check(mediaFaultMeansGone(MediaFault::Removed) && !mediaFaultMeansGone(MediaFault::Full), "only removal means gone");

    std::printf("3. mount table\n");
    const char *table =
        "/dev/mmcblk0p2 / ext4 rw,noatime 0 0\n"
        "/dev/nvme0n1p1 /media/RAW1 exfat rw,nosuid,uid=1000 0 0\n"
        "/dev/sda1 /media/RAW exfat rw,noatime,uid=1000,gid=1000 0 0\n"
        "/dev/sdb1 /media/My\\040Disk vfat rw 0 0\n";
    {
        std::istringstream in(table);
        const auto e = findMountEntry(in, "/media/RAW");
        check(e.found && e.device == "/dev/sda1" && e.fstype == "exfat", "exact match picks /media/RAW, not /media/RAW1");
    }
    {
        std::istringstream in(table);
        const auto e = findMountEntry(in, "/media/RAW/");
        check(e.found && e.device == "/dev/sda1", "trailing slash is normalised");
    }
    {
        std::istringstream in(table);
        const auto e = findMountEntry(in, "/media/My Disk");
        check(e.found && e.device == "/dev/sdb1", "octal escapes in /proc/mounts are decoded");
    }
    {
        std::istringstream in(table);
        const auto e = findMountEntry(in, "/media/CARD");
        check(!e.found, "absent path is not found");
    }
    {
        std::istringstream in("/dev/sda1 /media/RAW exfat rw 0 0\n/dev/sdb1 /media/RAW ext4 rw 0 0\n");
        const auto e = findMountEntry(in, "/media/RAW");
        check(e.found && e.device == "/dev/sdb1" && e.fstype == "ext4", "the last (topmost) mount wins");
    }

    std::printf("4. decision\n");
    MountTableEntry mounted{true, "/dev/sda1", "exfat", "rw"};
    auto s = evaluateMediaProbe(mounted, 0, 1000, 5000);
    check(s.state == MediaSnapshot::State::Mounted && s.freeBytes == 1000 && s.totalBytes == 5000, "mounted + statvfs ok");
    s = evaluateMediaProbe(mounted, EIO, 0, 0);
    check(s.state == MediaSnapshot::State::Removed && s.device == "/dev/sda1", "mounted + EIO on the root = removed");
    s = evaluateMediaProbe(mounted, ENODEV, 0, 0);
    check(s.state == MediaSnapshot::State::Removed, "mounted + ENODEV = removed");
    s = evaluateMediaProbe(mounted, EACCES, 0, 0);
    check(s.state == MediaSnapshot::State::Error, "mounted + EACCES = error, not removal");
    s = evaluateMediaProbe(MountTableEntry{}, 0, 0, 0);
    check(s.state == MediaSnapshot::State::None && std::string(s.stateName()) == "none", "not mounted = none");
    MediaSnapshot a = evaluateMediaProbe(mounted, 0, 1, 2), b = evaluateMediaProbe(mounted, 0, 3, 4);
    check(a.sameMedium(b), "free-space change is not a medium change");
    MountTableEntry other{true, "/dev/sdb1", "exfat", "rw"};
    check(!a.sameMedium(evaluateMediaProbe(other, 0, 1, 2)), "a different device is a medium change");

    std::printf("4b. device-level facts beat a statvfs that still answers (critic Y1)\n");
    s = evaluateMediaProbe(mounted, 0, 1000, 5000, /*deviceNodePresent=*/false, "");
    check(s.state == MediaSnapshot::State::Removed, "block device node gone -> removed even with statvfs ok");
    s = evaluateMediaProbe(mounted, 0, 1000, 5000, true, "dead");
    check(s.state == MediaSnapshot::State::Removed, "nvme controller state dead -> removed");
    s = evaluateMediaProbe(mounted, 0, 1000, 5000, true, "live");
    check(s.state == MediaSnapshot::State::Mounted, "nvme state live -> mounted");
    check(rootDiskForDevice("/dev/nvme0n1p1") == "nvme0n1" && rootDiskForDevice("/dev/sda1") == "sda" &&
          rootDiskForDevice("/dev/mmcblk0p2") == "mmcblk0", "root disk names");
    check(!cachedMediaSnapshot().has_value(), "no cached snapshot before the watcher ran");
    updateCachedMediaSnapshot(evaluateMediaProbe(mounted, 0, 7, 8));
    check(cachedMediaSnapshot() && cachedMediaSnapshot()->freeBytes == 7, "cached snapshot round-trips");
    check(cachedMediaSnapshotOrProbe("/nowhere").freeBytes == 7, "cachedMediaSnapshotOrProbe prefers the cache");

    std::printf("5. live probe on this host\n");
    const auto root = probeMediaRoot("/");
    check(root.state == MediaSnapshot::State::Mounted && root.totalBytes > 0, "/ probes as mounted with a size");
    const auto nowhere = probeMediaRoot("/definitely/not/a/mount");
    check(nowhere.state == MediaSnapshot::State::None, "an unmounted path probes as none");

    std::printf("%s (%d failure%s)\n", failures ? "FAILED" : "ALL CHECKS PASSED", failures, failures == 1 ? "" : "s");
    return failures ? 1 : 0;
}

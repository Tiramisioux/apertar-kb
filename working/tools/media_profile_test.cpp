// Host test for apertar-core's src/util/MediaProfile.hpp (pure parts).
// Build: g++ -std=c++20 -Wall -Wextra -I<apertar-core>/src media_profile_test.cpp -o media_profile_test
#include "util/MediaProfile.hpp"
#include <cstdio>

static int failures = 0;
static void check(bool ok, const char *what) { std::printf("  [%s] %s\n", ok ? "ok" : "FAIL", what); if (!ok) ++failures; }

int main()
{
    using namespace apertar;
    std::printf("1. root disk\n");
    check(rootDiskForDevice("/dev/nvme0n1p1") == "nvme0n1", "nvme partition");
    check(rootDiskForDevice("/dev/nvme0n1") == "nvme0n1", "nvme whole disk");
    check(rootDiskForDevice("/dev/mmcblk0p2") == "mmcblk0", "sd partition");
    check(rootDiskForDevice("/dev/sda1") == "sda", "usb partition");
    check(rootDiskForDevice("/dev/sdaa12") == "sdaa", "two-letter disk");
    check(rootDiskForDevice("/dev/sda") == "sda", "usb whole disk");
    check(rootDiskForDevice("") == "", "empty");

    std::printf("2. filesystem\n");
    check(classifyFilesystem("ext4") == MediaFilesystem::Ext4, "ext4");
    check(classifyFilesystem("exfat") == MediaFilesystem::Exfat, "exfat");
    check(classifyFilesystem("vfat") == MediaFilesystem::Vfat, "vfat is FAT32, not exFAT (Cinemate 0142c5b)");
    check(classifyFilesystem("ntfs3") == MediaFilesystem::Ntfs, "ntfs3 kernel driver");
    check(classifyFilesystem("fuseblk") == MediaFilesystem::NtfsFuse, "fuseblk is ntfs-3g");
    check(classifyFilesystem("") == MediaFilesystem::None, "empty is none");
    check(classifyFilesystem("btrfs") == MediaFilesystem::Other, "unknown is other");

    std::printf("3. class\n");
    check(classifyMediaClass("mmcblk0", "/sys/devices/platform/axi/1000120000.pcie/1f00100000.mmc/mmc_host/mmc0/mmc0:0001", "") == MediaClass::SdCard, "mmcblk is sd");
    check(classifyMediaClass("sda", "/sys/devices/platform/axi/1000120000.pcie/1f00300000.usb/xhci-hcd.1/usb4/4-1/4-1:1.0/host0/target0:0:0/0:0:0:0", "DRIVER=uas\nTYPE=0\n") == MediaClass::UsbUas, "usb + uas");
    check(classifyMediaClass("sdb", "/sys/devices/.../usb3/3-1/3-1:1.0/host1/target1:0:0/1:0:0:0", "DRIVER=sd\n") == MediaClass::UsbStorage, "usb without uas");
    check(classifyMediaClass("nvme0n1", "/sys/devices/platform/axi/1000120000.pcie/1000110000.pcie/pci0000:00/0000:00:00.0/0000:01:00.0/nvme/nvme0", "DRIVER=nvme\n") == MediaClass::PiNvme, "nvme on the Pi PCIe");
    check(classifyMediaClass("nvme1n1", "/sys/devices/.../usb2/2-1/2-1:1.0/host2/target2:0:0/2:0:0:0", "DRIVER=uas\n") == MediaClass::UsbUas, "an NVMe behind a USB bridge is USB, not PCIe");
    check(classifyMediaClass("", "", "") == MediaClass::Unknown, "nothing known stays unknown");
    check(classifyMediaClass("sdc", "", "") == MediaClass::Other, "no sysfs answer is other, never a guess");

    std::printf("4. writer table\n");
    auto ext4 = writerSettingsFor(MediaFilesystem::Ext4, MediaClass::PiNvme);
    auto exfat = writerSettingsFor(MediaFilesystem::Exfat, MediaClass::UsbUas);
    auto fuse = writerSettingsFor(MediaFilesystem::NtfsFuse, MediaClass::PiNvme);
    check(ext4.workers == 4 && ext4.extraRawBuffers == 0 && ext4.directIo, "ext4: 4 workers, no extra buffers, direct");
    check(exfat.workers == 4 && exfat.extraRawBuffers == 0 && exfat.queueFrames == 12, "exfat: Core's pre-profile 4 workers, queue 12 (measured C0101/C0106)");
    check(!fuse.directIo, "ntfs-3g: no direct I/O");
    check(!writerSettingsFor(MediaFilesystem::None, MediaClass::Unknown).directIo, "unknown: conservative");

    std::printf("5. profile\n");
    const MediaProfile p = deriveMediaProfile(MediaClass::UsbUas, "/dev/sda1", "exfat");
    check(p.known() && p.rootDisk == "sda" && p.summary() == "class=usb-uas fs=exfat workers=4 queue=12 raw_buffers=+0", "summary string");
    MediaSnapshot unmounted;
    check(!detectMediaProfile(unmounted).known(), "unmounted snapshot gives no profile");
    MountTableEntry e{true, "/dev/sda1", "exfat", "rw"};
    const MediaProfile live = detectMediaProfile(evaluateMediaProbe(e, 0, 1, 2));
    check(live.filesystem == MediaFilesystem::Exfat && live.rootDisk == "sda", "profile from a probe snapshot (class from this host's sysfs, unchecked)");

    std::printf("%s (%d failure%s)\n", failures ? "FAILED" : "ALL CHECKS PASSED", failures, failures == 1 ? "" : "s");
    return failures ? 1 : 0;
}

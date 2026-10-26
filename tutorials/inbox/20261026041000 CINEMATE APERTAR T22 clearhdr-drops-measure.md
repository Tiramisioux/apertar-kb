---
datum: 2026-10-26 04:10:00
kontext: CINEMATE
projekt: "#APERTAR"
fritext: T22 clearhdr-drops-measure
typ: digital anteckning
---

# T22. Find out where Clear HDR frames are lost: CSI-2 counters, writeback, link

Status: written 2026-10-26 (cloud session, from source; nothing run on this Pi yet). First of the series T22-T26 that comes out of `working/clearhdr-compare-answer.md`.

**You will learn**
- The three ways the rp1-cfe driver loses a frame, and which hardware counter tells them apart.
- Why a buffered disk write disturbs the camera while a direct write does not, and how Core's own writer behaves like the buffered `dd`.
- A measurement routine you will reuse after every fix in T23-T26.

**Risk:** one token added to `/boot/firmware/cmdline.txt` and a reboot (undo: delete the token, reboot). Temporary `sysctl` and block-queue writes with `sudo`; they vanish at the next reboot. No code. **Time:** 1.5-2 h including the reboot.

> [!note] Rule for this whole series
> Measure before and after every change. A fix that is not measured is a guess (`cinemate-handbook/lessons/hardware-log.md:3204-3209`: Cinemate shipped a frame-drop fix built on a plausible story; the suspected pass then measured 0.38 ms/frame).

## 1. The problem

16-bit Clear HDR at 25 fps, 10 s takes (`working/clearhdr-design.md`, 2026-10-26):

```
C0040  246/246   clean
C0038  209/245   single-frame gaps every 7-10 frames, IPA sees 21.5-22.4 fps
C0041  218/244   same pattern
```

With Core **idle** (not recording), a disk write alone reproduces it:

```
dd if=/dev/zero of=/media/RAW/x bs=1M count=3400 conv=fdatasync   561 MB/s   21.71 fps into libcamera, 19 gaps
dd if=/dev/zero of=/media/RAW/x bs=1M count=3400 oflag=direct     759 MB/s   25.00 fps, 0 gaps
```

Expected: 25.00 fps whatever the disk does. Eight raw buffers instead of four changed nothing (T23 explains why that test was not what it looked like).

## 2. How this part works

```
 sensor ──CSI-2 1782 Mbps/lane──> RP1 CSI-2 receiver ──FIFO──> CFE DMA ──> RAM (4 buffers: image, stats, FE config, embedded)
                                      │                                      ▲
                                      │ overflow? discard?                   │ writeback DMA + CPU memcpy
                                      ▼                                      │
                                 csi2_errors (debugfs)              NVMe <── page cache <── Core write() + fadvise(DONTNEED)
```

Three places a frame can go missing, all visible from the Pi:

| Where | Mechanism | How you see it |
| --- | --- | --- |
| No buffer queued | `cfe_check_job_ready()` refuses the next job when **any** of the four CFE nodes has an empty queue (`kernel rp1_cfe/cfe.c:615-631`). A late requeue by libcamera or Core. | `verbose_debug=1` + dynamic debug: "has no buffer, unable to schedule job" in `dmesg` |
| CSI-2 FIFO overflow | the receiver could not write to RAM fast enough (memory contention) | `csi2_errors`: `Overflows N`, discards column `OVLF` (`kernel rp1_cfe/csi2.c:175-258`) |
| Link errors | our 1782 Mbps/lane is above the D-PHY table's 1500 Mbps top; the kernel programs the 1500 bin and warns `DPHY: Datarate 1782 Mbps out of range` (`kernel rp1_cfe/dphy.c:119-129`) | `csi2_errors` columns `LEN`, `UNMATCHED` |

Why Core behaves like the buffered `dd`: after every DNG Core calls `posix_fadvise(fd, 0, 0, POSIX_FADV_DONTNEED)` (`Core/src/cdng/CdngEncoder.cpp:1779` at `f60e301`). In the kernel that call **starts asynchronous writeback of the dirty pages** before dropping them (`mm/fadvise.c:113-115`). So a take is a 16.6 MB writeback burst 25-30 times a second: exactly the kernel-driven page-cache writeback the `dd` test produces. Cinemate's writer has had no DONTNEED since 2026-03-06 and writes one `write()` per DNG; it never saw this symptom but also never measured it.

Reading assignments (10 min): `Core/src/cdng/CdngEncoder.cpp:1748-1786` (open, write, fadvise, close) and `Core/src/camera/CameraController.cpp:7265-7290` (the copy on the completion thread; T25).

## 3. Find it yourself

**3.1 What filesystem is `/media/RAW`?** (Pi)

```bash
findmnt -no FSTYPE,OPTIONS /media/RAW        # decides O_DIRECT support (T24) and whether Cinemate's "ext4 drops less" applies
```

Prediction: the KB says "ext4?"; Core's `format_media` defaults to exFAT (`App:10647`). Which is it?

> [!tip]- Answer
> Both support direct I/O (`fs/exfat/inode.c:492-506` routes to `blockdev_direct_IO`). Only FUSE/ntfs-3g would not. Write the answer into `lessons/hardware-log.md` whatever it is; the whole series assumes it.

**3.2 Dirty-page thresholds.** (Pi)

```bash
sysctl vm.dirty_ratio vm.dirty_background_ratio vm.dirty_writeback_centisecs vm.dirty_expire_centisecs vm.dirty_bytes vm.dirty_background_bytes
```

Prediction: kernel defaults 20 / 10 / 500 / 3000 / 0 / 0 (`mm/page-writeback.c:74,91,102,109`). 10 % of ~3.5 GB available is ~350 MB: at 561 MB/s background writeback starts ~0.6 s into the `dd`. When did the gaps start in the KB table?

> [!tip]- Answer
> "Gaps start 0.6-1 s into the write." The gaps begin when writeback begins, not when the copy begins. That is the first clue that it is the writeback, not the memcpy.

**3.3 Block queue.** (Pi)

```bash
cat /sys/block/nvme0n1/queue/scheduler /sys/block/nvme0n1/queue/nr_requests /sys/block/nvme0n1/queue/rq_affinity
```

Prediction: `[none]`, 1023 or 1024, 1. Cinemate sets `none`, 512, 2 for an NVMe HAT (`cinemate/services/storage-automount/storage-automount.py:140-148`).

**3.4 Is the CFE debugfs there, and are the error counters?** (Pi, root)

```bash
sudo ls /sys/kernel/debug/ | grep rp1-cfe                 # the directory is "rp1-cfe:<device>"
sudo ls /sys/kernel/debug/rp1-cfe:*/                      # format regs csi2_regs pisp_regs ... csi2_errors?
```

Prediction: `csi2_errors` is **missing**. It is created only when the module loads with `track_csi2_errors=1` (`kernel rp1_cfe/csi2.c:19-21, 582`).

## 4. Make the change (the measurement setup)

**4.1 Turn the CSI-2 error counters on** (Pi, sudo, reboot)

Add one token to the single line of `/boot/firmware/cmdline.txt` (do not add a newline):

```
rp1_cfe.track_csi2_errors=1
```

```bash
sudo sed -i '1 s/$/ rp1_cfe.track_csi2_errors=1/' /boot/firmware/cmdline.txt   # appends to line 1
cat /boot/firmware/cmdline.txt                                                 # one line, token at the end
sudo reboot
```

**Check:** `grep -o 'rp1_cfe.track_csi2_errors=1' /proc/cmdline` prints the token, and `sudo ls /sys/kernel/debug/rp1-cfe:*/csi2_errors` exists.

**4.2 Learn the counter file** (Pi)

```bash
sudo cat /sys/kernel/debug/rp1-cfe:*/csi2_errors      # prints Overflows and a per-VC table; READING RESETS IT (csi2.c:189-192)
sudo cat /sys/kernel/debug/rp1-cfe:*/csi2_errors      # second read: everything 0
```

Columns: `OVLF` (FIFO overflow discards), `LEN` (length-limit), `UNMATCHED` (data type not matched), `INACTIVE`. Because reading resets, the routine is: read once to zero, run the test, read once to collect.

**4.3 The baseline pair, with counters** (Pi; Core running, idle, Clear HDR 16-bit, 25 fps, WebUI closed)

Terminal A:

```bash
python3 -I ~/apertar-kb/working/tools/writeback_watch.py 20 0.1 > /tmp/wb_buffered.txt &   # 100 ms samples of nr_dirty / nr_writeback
```

Terminal B:

```bash
sudo cat /sys/kernel/debug/rp1-cfe:*/csi2_errors > /dev/null              # zero
T1=$(date '+%F %T')
dd if=/dev/zero of=/media/RAW/ddtest bs=1M count=3400 conv=fdatasync status=progress
T2=$(date '+%F %T'); rm /media/RAW/ddtest
sudo cat /sys/kernel/debug/rp1-cfe:*/csi2_errors                          # collect
python3 -I ~/apertar-kb/working/tools/ipa_rate.py "$T1" "$T2"             # fps into libcamera, gaps and their times
```

Then the same with `oflag=direct` instead of `conv=fdatasync` (and `wb_direct.txt`).

Prediction before you run it: write down what `Overflows` will show for buffered and for direct.

> [!tip]- What the outcomes mean
> | buffered | direct | Reading |
> | --- | --- | --- |
> | Overflows/OVLF > 0, ≈ gap count | 0 | Memory-write starvation of the receiver: theory A confirmed at the hardware. T24 (direct I/O) is the fix. |
> | UNMATCHED or LEN > 0 in both | > 0 | Link errors (theory A2): the 1782 Mbps/lane link is marginal on this board. Test `link-frequency=720000000` in `config.txt` before anything else. |
> | all 0, gaps present | 0 | No receiver error: the frame was never captured because no buffer was queued. Go to 4.6. |

**Check:** `ipa_rate.py` for the direct run says `intervals>60ms=0` and the counters are 0 (otherwise the setup itself is noisy; stop and look).

**4.4 Writeback or memory traffic? The tmpfs test** (Pi)

```bash
sudo cat /sys/kernel/debug/rp1-cfe:*/csi2_errors > /dev/null
T1=$(date '+%F %T'); dd if=/dev/zero of=/dev/shm/ddtest bs=1M count=2000 status=progress; T2=$(date '+%F %T'); rm /dev/shm/ddtest
sudo cat /sys/kernel/debug/rp1-cfe:*/csi2_errors
python3 -I ~/apertar-kb/working/tools/ipa_rate.py "$T1" "$T2"
```

Same memcpy and page allocation as the buffered run, no NVMe, no writeback. Gaps here = the cause is on the memory/CPU side; none = it is the writeback/NVMe path.

**4.5 Cinemate's knobs, as a knob test** (Pi, sudo; reverts at reboot)

```bash
sudo sysctl -w vm.dirty_background_bytes=268435456 vm.dirty_bytes=1073741824 vm.dirty_ratio=0 vm.dirty_background_ratio=0 vm.dirty_writeback_centisecs=150
echo none | sudo tee /sys/block/nvme0n1/queue/scheduler; echo 2 | sudo tee /sys/block/nvme0n1/queue/rq_affinity; echo 512 | sudo tee /sys/block/nvme0n1/queue/nr_requests
```

Repeat 4.3 (buffered). Then five takes:

```bash
~/apertar-kb/working/tools/takes.sh 5 10         # 16-bit, 25 fps; look at "missing=" and "ipa rate="
```

**4.6 Was any frame simply not scheduled?** (Pi, sudo; the driver's own debug line)

```bash
echo 1 | sudo tee /sys/module/rp1_cfe/parameters/verbose_debug
echo 'module rp1_cfe +p' | sudo tee /sys/kernel/debug/dynamic_debug/control
sudo dmesg -C
~/apertar-kb/working/tools/take.sh                                  # one 10 s take
sudo dmesg | grep -c 'has no buffer, unable to schedule job'        # frames the CFE skipped for want of a queued buffer
sudo dmesg | grep 'has no buffer' | sed 's/.*\[\(.*\)\] has no.*/\1/' | sort | uniq -c   # WHICH node was late: image, stats, config, embedded
echo 0 | sudo tee /sys/module/rp1_cfe/parameters/verbose_debug; echo 'module rp1_cfe -p' | sudo tee /sys/kernel/debug/dynamic_debug/control
```

This is the number T23 and T25 have to drive to zero at 30 fps.

## 5. Record the result

Fill this table into `lessons/hardware-log.md` (one entry, dated):

| Run | fps into libcamera | gaps | Overflows | OVLF | LEN | UNMATCHED | first gap (s) | first nr_writeback>0 (s) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| idle, no load | | | | | | | | |
| dd buffered | | | | | | | | |
| dd direct | | | | | | | | |
| dd tmpfs | | | | | | | | |
| dd buffered + Cinemate knobs | | | | | | | | |
| 16-bit take, 25 fps | | | | | | | | |
| 16-bit take, 30 fps (+ "has no buffer" count) | | | | | | | | |

Success = you can say in one sentence which of the three rows in section 2 loses the frames, with the counter that proves it.

## 6. Commit

KB only, on the Pi: `git -C ~/apertar-kb add lessons/hardware-log.md working/tools/writeback_watch.py && git -C ~/apertar-kb commit -m "kb: Clear HDR drop measurements with CSI-2 counters (T22)"`. Nothing in Core changes in this tutorial.

## 7. If it went wrong

| You see | It means | Do |
| --- | --- | --- |
| no `csi2_errors` file after reboot | token not applied, or debugfs not mounted | `cat /proc/cmdline`; `sudo mount -t debugfs none /sys/kernel/debug` |
| `Permission denied` on debugfs | debugfs is root-only | prefix `sudo`; the tutorial checker cannot run these, they are yours |
| counters all 0 but `ipa_rate.py` shows gaps during buffered `dd` | the receiver did not complain: the frame had no buffer queued | run 4.6 during the `dd`; a late requeue with Core idle means libcamera's own thread stalled (memory contention on the swap/stats passes) |
| `dmesg` floods | verbose_debug left on | the last line of 4.6 turns it off; it also resets at reboot |
| the camera stops after the knob test | `nr_requests` write refused or scheduler not available | `cat /sys/block/nvme0n1/queue/scheduler` shows the choices; reboot resets everything |

Undo everything: remove the token from `cmdline.txt`, reboot.

## 8. What you learned, going further

- The CFE needs all four of its buffers queued per frame, not just the image one.
- Writeback, not raw bandwidth, is what the camera dislikes: 561 MB/s buffered hurt, 759 MB/s direct did not.
- Next: **T23** (requests follow buffers) is a one-evening Core change that also fixes the 8-buffer experiment; **T24** is the direct-I/O writer that removes the writeback; **T25** moves the copy off the completion thread for 30 fps; **T26** fixes the crop rectangles in the driver.
- Upstream: if `Overflows` counts the gaps, that is a Raspberry Pi kernel/libcamera-level finding worth a forum post with the table above.

## 9. Sources

- `working/clearhdr-compare-answer.md` (2026-10-26), sections 2 and 5.
- raspberrypi/linux `rpi-6.12.y` `drivers/media/platform/raspberrypi/rp1_cfe/{cfe.c,csi2.c,dphy.c,cfe_fmts.h}`, `mm/fadvise.c`, `mm/page-writeback.c` @ `5bd564a`.
- `Apertar-Core/src/cdng/CdngEncoder.cpp:1748-1786@f60e301`; `src/camera/CameraController.cpp:7265-7290@f60e301`.
- `cinemate/services/storage-automount/storage-automount.py:140-148, 285-336@d6cc93e`.
- `cinemate-handbook/lessons/hardware-log.md:741-748, 985, 3204-3209@c99ff77`.

%% tutor
ref core src/cdng/CdngEncoder.cpp 1779 ::posix_fadvise(fd, 0, 0, POSIX_FADV_DONTNEED);
ref core src/cdng/CdngEncoder.cpp 1748 int openFlags = O_WRONLY | O_CREAT | O_TRUNC;
ref core src/camera/CameraController.cpp 7268 std::vector<uint8_t> rawCopy = recorder_.acquireRawBuffer(rawSize);
check 3.1 | findmnt -no FSTYPE /media/RAW | ext4|exfat|vfat|ntfs
check 3.2 | sysctl -n vm.dirty_background_ratio | ^[0-9]+$
check 4.1 | grep -o 'rp1_cfe.track_csi2_errors=1' /proc/cmdline | rp1_cfe.track_csi2_errors=1
%%

#CINEMATE
#APERTAR

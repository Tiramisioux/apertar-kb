# Q2: can the PiSP pipeline overlap frames?

Reader: q2-pipelining (Claude Opus 5.5, cloud subagent). Trees: libcamera-apertar `6b0b49f` (branch `apertar`), libcamera-qbc
`7e9fef0`, libcamera (Cinemate) `bfe0b76`, libpisp `9ba67e6` (v1.3.0), kernel-rpi `5bd564a` (rpi-6.12.y, sparse; I added
`arch/arm64/configs include/trace/events drivers/media/v4l2-core drivers/media/common/videobuf2` to the checkout), apertar-kb
(brief `working/handoff-30fps-clearhdr16.md`, `lessons/hardware-log.md:51-233`, `working/tools/libcam_stages.py`). Date 2026-10-26.
Web: GitHub reachable through WebFetch; `datasheets.raspberrypi.com`, `lists.libcamera.org`, `patchwork.libcamera.org`,
`forums.raspberrypi.com`, `docs.kernel.org` blocked by the egress proxy or DNS. The PiSP specification PDF could not be read.

## Short answer

- **It is a software simplification, not a back-end constraint.** CONFIRMED in the code: the gate is `state_ != State::Idle` in
  `tryRunPipeline` (`libcamera-apertar/src/libcamera/pipeline/rpi/pisp/pisp.cpp:3115@6b0b49f`). `Idle` comes back only when the
  oldest request has all its buffers back after the BE finishes (`common/pipeline_base.cpp:1525-1542@6b0b49f`). The kernel driver
  keeps a software job list plus a two-slot hardware queue, one job running and one programmed and waiting
  (`kernel-rpi/drivers/media/platform/raspberrypi/pisp_be/pisp_be.c:239-244, 597-631, 651-701@5bd564a`).
- **Where the design comes from.** PROBABLE: it was inherited from the VC4 (Pi 4) handler. There the IPA's statistics came out
  of the ISP, so frame N's IPA work had to wait for frame N's ISP pass (`pipeline/rpi/vc4/vc4.cpp:884-906`). On PiSP the stats
  come from the front end and are processed inside `prepareIsp` (`ipa/rpi/common/ipa_base.cpp:500-501`,
  `controller.cpp:189 statsInline = true`), so no IPA step depends on the back end's output.
- **Upstream has not pipelined it and has not said why.** CONFIRMED from commit titles: the Raspberry Pi fork's `main` up to
  Oct 2026 has no commit in `pisp.cpp` or `pipeline_base.cpp` that does this. UNCONFIRMED whether the mailing list ever discussed
  it, because the archives could not be reached.
- **The most pipelining can recover** is the back end's idle time per frame. In the one window measured before L1 that is
  between **1.6 ms** (if all 34.6 ms "start->done" is hardware) and about 21 ms (if the hardware takes only the idle 13.4 ms)
  of the 36.2 ms cycle. The answer depends on one unmeasured number: the hardware BE time while recording.
- **If the BE takes at least 33.3 ms per frame, pipelining cannot give 30 fps.** One engine runs jobs in sequence. The best
  case is then 1000/34.6 = 28.9 fps. PROBABLE: L2 removed most of the thread latency and still delivered 26.3-28.2 fps, which
  points to a BE of about 34-36 ms while recording.
- **The "34.6 ms" is not a hardware time.** CONFIRMED: it is the gap between two log lines on the pipeline thread. It covers
  libpisp tiling, the QBUFs, the hardware, and the wait before the thread services the dequeue. The hardware done time is
  **already in the same debug log**: the `timestamp:` field of "Stream ISP Input buffer complete" is the BE interrupt's
  `ktime_get_ns()`. `libcam_stages.py` ignores it. An ftrace IRQ trace gives the exact start and done times (§6).

## 1. The state machine (CONFIRMED unless marked)

| Item | Where | What it does |
| --- | --- | --- |
| States | `common/pipeline_base.h:124@6b0b49f` | `enum class State { Stopped, Idle, Busy, IpaComplete, Error }`. A comment at `:119-123` says every function runs on one thread, so nothing takes a lock |
| `handleState()` | `common/pipeline_base.cpp:1502-1523` | Does nothing for `Stopped`, `Busy` and `Error`. `IpaComplete` runs `checkRequestCompleted()` and then falls through to `Idle`, which runs `tryRunPipeline()` |
| `checkRequestCompleted()` | `pipeline_base.cpp:1525-1554` | Looks only at `requestQueue_.front()`. It returns while that request has pending buffers or `state_ != IpaComplete`. Otherwise it calls `completeRequest` (`:1538`), pops the request and sets `state_ = Idle` (`:1542`) |
| Start | `pipeline_base.cpp:724` | `state_ = Idle` |
| `tryRunPipeline()` gate | `pisp/pisp.cpp:3112-3117@6b0b49f` (`7e9fef0`: `:2860-2863`) | Proceeds only if `state_ == Idle`, the request queue is not empty, and the front CFE job is complete (inline path) or complete with its CPU passes done (L2 worker path, `cfeJobReady`, `:1105-1112`) |
| Idle -> Busy | `pisp.cpp:3139` | Sets `state_ = Busy`, pairs the front request with the front CFE job, then `cfeJobQueue_.pop_front()` and `ipa_->prepareIsp(params)` (`:3222-3223`) |
| IPA thread | `utils/codegen/ipc/generators/libcamera_templates/module_ipa_proxy.cpp.tmpl:90,95,111` | `prepareIsp` is `[async]` (`include/libcamera/ipa/raspberrypi.mojom:201`) and is queued to the IPA proxy's own thread. The IPA runs in-process: `/proc/<pid>/maps` showed it loaded (hardware-log:208) |
| IPA work | `ipa/rpi/common/ipa_base.cpp:426-520` | `applyControls`. PiSP has `statsInline`, so `processStats` runs **inside** `prepareIsp` (`:500-501`) on the CFE stats. Then `controller_.prepare`, `platformPrepareIsp` (BE config into the shared libpisp `BackEnd`), `reportMetadata` (`:515-516`, which emits `metadataReady`) and the `prepareIspComplete` emit (`:519`) |
| Busy -> IpaComplete | `pisp.cpp:2363-2389` | `prepareIspComplete()` calls `prepareBe()` (`:2385`), which queues the BE job, and then sets `state_ = IpaComplete` (`:2387`). So "IpaComplete" means the IPA has finished and the BE is running. The pipeline does not wait for the IPA after this point |
| `prepareBe()` | `pisp.cpp:2750-2801` | Logs "Input re-queue to ISP" (`:2754`), queues Input (`:2757`), queues TDN in/out as a ping-pong of 2 buffers (`:2760-2764`) and stitch (`:2766-2771`), takes one of the **2** config buffers (`:2774`), runs `be_->Prepare()` (libpisp tiling, `:2779`) and queues config last (`:2800`). The kernel forms the job on that last QBUF |
| IpaComplete -> Idle | `pipeline_base.cpp:1525-1542` | Fires once the request's buffers have come back: the raw buffer in `beInputDequeue` (`pisp.cpp:2272-2284`) and the preview buffer in `beOutputDequeue` (`:2286-2338`, which may also run a SW downscale or a 24->32-bit conversion on this thread). Both run only after the **BE has finished** |
| Stats processed | `pisp.cpp:2340-2347` | `processStatsComplete` only gives the stats buffer back to the CFE and **does not change the state**. On PiSP, stats processing is part of the `prepareIsp` step |
| Request completion | `libcamera/pipeline_handler.cpp:584-603` | `completeRequest` emits `Camera::requestCompleted` synchronously on this thread, before `state_ = Idle`. Any work in Core's callback is therefore inside the serial loop. T25 made that callback short |

What calls `handleState()`: queueing a request (`pipeline_base.cpp:836-837`), every CFE buffer dequeue (`pisp.cpp:2269`), the end of
an L2 worker job (`:2162`), BE input and output dequeues (`:2283`, `:2337`) and `prepareIspComplete` (`:2388`). Only one of these
events can **start** the next frame: the dequeue that returns the last pending buffer of the front request, which in practice is
the BE's completion. All the others reach `tryRunPipeline()` and leave at the `Idle` check.

Other assumptions in the code that a single frame is in flight (CONFIRMED). They would have to change if frames overlap:
- `metadataReady` merges the IPA metadata into `requestQueue_.front()` (`pipeline_base.cpp:1286-1287`). With two frames in flight,
  frame N+1's metadata would land in request N.
- `tryRunPipeline` and `checkRequestCompleted` both use `requestQueue_.front()` (`pisp.cpp:3122`, `pipeline_base.cpp:1527`).
- `be_->Prepare()` runs with no lock (`pisp.cpp:2779`), while FE access is locked (`:2741`). That is safe only because the IPA and
  the pipeline thread take turns on the `BackEnd` object. With depth 2 they still take turns: `Prepare(N)` runs in
  `prepareIspComplete(N)` before `prepareIsp(N+1)` is sent (PROBABLE).

## 2. Per-frame timeline: what is serial with the BE

```
 CFE (RP1 DMA)    |== frame N written (33.3 ms) ==|== N+1 ==|== N+2 ==| ...  never waits for the BE
 L1: PH thread    [swap N 9.9][stats N 7.1]   ...   [swap N+1][stats N+1] ...   (L2: same work on the worker thread)
 PH thread                  (waits for Idle: request N-1 completes)
                   tryRunPipeline(N) -> prepareIsp(N) ---------+
 IPA thread                                [IPA N: stats+algos+BE cfg]   (~<1.6 ms incl. dispatch)
 PH thread                                          (wait if busy) [prepareIspComplete N: Prepare tiles + 6-7 QBUF]
 BE hardware                                                          [======== job N (t_HW) ========]
 PH thread                                                                       (wait if busy) [ISP dq x3 -> complete N
                                                                                   -> Core callback -> Idle -> tryRunPipeline(N+1)]
 serial cycle  =  t_lat(prepareIspComplete) + t_IPA + t_Prepare+QBUF + t_HW + t_lat(BE done) + t_complete
```

| Step | Thread | In the BE's serial loop today | Could overlap BE job N if pipelined |
| --- | --- | --- | --- |
| CFE DMA of later frames | RP1 hardware | no | (already overlaps) |
| 16-bit swap + SW stats of later frames | L1: PH thread; L2: worker | not as compute. In L1 they **block the PH thread**, which delays the `prepareIspComplete` and BE-done dispatch (the 78 % finding) | yes |
| IPA `prepareIsp(N+1)`, stats inline | IPA thread | **yes**: it waits for `Idle` | **yes**: it does not need BE N's output |
| `prepareBe(N+1)`: libpisp `Prepare` + QBUFs | PH thread | **yes** | **yes**. The kernel programs job N+1 into the waiting slot during job N |
| BE job N | BE hardware | - | no. **One engine**, jobs run one after another |
| BE done -> request complete -> Core callback | PH thread | **yes** | yes: with job N+1 already queued, this latency is off the BE's path |

## 3. The kernel pisp_be driver (CONFIRMED unless marked; `drivers/media/platform/raspberrypi/pisp_be/pisp_be.c@5bd564a`)

| Question | Answer | Lines |
| --- | --- | --- |
| How many jobs it accepts | No fixed limit. Each time a buffer is queued, `pispbe_prepare_job` takes the first ready buffer from each node and appends a job descriptor to `pispbe->job_queue` (a list). The real limit is the number of buffers user space queues: libcamera has 2 config, 2 TDN and 2 stitch buffers (`pisp.cpp:1305-1307`), so **2 jobs in flight** | 473-595 (list add 575), 874-893 |
| Hardware queue depth | **2**: `running_job` and `queued_job`. `hw_busy` means "a job is queued or is being started" (243). `pispbe_schedule` sends the next job only when `hw_busy` is clear (597-631). The ISR clears it on each **start** interrupt (`can_queue_another`, 678-690), so job N+1 is written to the hardware while job N runs | 239-244, 597-631, 651-701 |
| Start job N+1 while N runs? | It can be **queued** while N runs. `CONTROL = COPY_CONFIG | QUEUE_JOB` (319-321) after a `STATUS_QUEUED` safety check (270) implies shadowed config registers. The hardware then starts N+1 when N finishes; the ISR comment covers a queued job that "start[s] and finish[es] simultaneously" (672-676). The two jobs never **execute** at the same time: the counters model one running job (PROBABLE; the spec PDF that would confirm it was unreachable) | 260-322, 664-689 |
| Per-job register programming | 13 DMA address pairs (26 writes), 2 enable words, then every 32-bit word of `pisp_be_config` from `global.bayer_order` to the end. `sizeof(pisp_be_config)` = 6476 B and the offset is 120 (compiled on the host from `include/uapi/linux/media/raspberrypi/pisp_be_config.h`), so (6476-120)/4 = **1589 writes**. Then 26 read-backs, 2 tile-pointer writes and 1 control write: about 1620 MMIO writes per job. Tiles (`num_tiles` x 160 B, at most 64) are fetched by the BE from the config buffer. Cost UNCONFIRMED; at ~0.1 us per posted write that is ~0.16 ms, which is negligible next to 33 ms (PROBABLE) | 265-322, `N_HW_ADDRESSES` 61 |
| Where the programming runs | In the QBUF ioctl when the BE is idle (today's case, via `pispbe_node_buffer_queue -> pispbe_schedule`). In the start-interrupt ISR when a job is waiting | 874-893, 701 |
| Several contexts | `PISPBE_NUM_NODE_GROUPS 2`: "2 independent instances allowing 2 simultaneous users" that "share hardware". There is **one** `job_queue` and one running/queued pair for both, so they time-share one engine. Gives no extra throughput | 32-38, 239-244 |
| Interrupts | Start and done are both enabled (`INTERRUPT_EN = 3`, 1723). IRQ name `pispbe` (`PISPBE_NAME`, 40, 1758-1759). In one-at-a-time operation each job gives a start IRQ just after the QBUF and a done IRQ at the end | 1723, 1758 |
| Buffer timestamps | `pispbe_isr_jobdone` stamps **every** buffer of the job (input included) with `ktime_get_ns()` at the done interrupt; queues use `TIMESTAMP_MONOTONIC` | 633-649, 1454 |
| AXI | `PISP_BE_AXI_REG = 0x32703200` with comment "AXI QOS=0". Whether QoS 0 is low priority against the CPUs and PCIe on the BCM2712 fabric is UNCONFIRMED. It matters for Q3 if the BE is memory-bound | 1716-1720 |

History (web, CONFIRMED titles only): upstream Linux `pisp_be` commits include "media: pisp_be: Split jobs creation and scheduling"
(972eed0, Jul 2025, github.com/torvalds/linux/commits/master/drivers/media/platform/raspberrypi/pisp_be). A search summary of the
LKML v8 thread says job assembly was moved out of interrupt context into a job queue. I could not open the thread
(lkml.rescloud.iu.edu was blocked), so its wording is UNCONFIRMED. So the kernel has handled queued jobs since the 2024 driver,
and handles them better since 2025. libcamera has never used this.

## 4. Upstream history and precedent

| Finding | Label | Source |
| --- | --- | --- |
| The Raspberry Pi fork's `main` (to Oct 2026) has no pipelining commit in `pisp.cpp` (33 titles, newest c682979 2026-10-09) or `pipeline_base.cpp` (newest d48b72e 2026-09-29). Its current `handleState`/`checkRequestCompleted` match ours, and `metadataReady` still merges into `requestQueue_.front()` | CONFIRMED (titles and fetched source) | github.com/raspberrypi/libcamera/commits/main/... ; raw.githubusercontent.com/.../pipeline_base.cpp |
| libcamera v0.0.1 (VC4 `raspberrypi.cpp`) already had `enum class State { Stopped, Idle, Busy, IpaComplete, Error }`, the same gate in `tryRunPipeline` and the comment "Process all the user controls by the IPA. Once this is complete, we queue the ISP output buffer listed in the request to start the HW pipeline." None of it says why only one frame runs at a time | CONFIRMED (fetched file, read through the fetch tool's summary) | raw.githubusercontent.com/raspberrypi/libcamera/v0.0.1/src/libcamera/pipeline/raspberrypi/raspberrypi.cpp |
| The VC4 design needed it: stats come from the ISP (`Isp::Stats`), `processStats` is called after the ISP output (`vc4.cpp:884-888`), and `IpaComplete` is set only in `processStatsComplete` (`vc4.cpp:906`). PiSP keeps the states, but `IpaComplete` is reached **before** the BE runs (`pisp.cpp:2385-2387`) | CONFIRMED code; PROBABLE as the reason | libcamera-apertar@6b0b49f |
| The local libcamera clones are shallow (from 2023), so the 2020 origin cannot be read here. The 2020 patch "libcamera: pipeline: Raspberry Pi pipeline handler" (patchwork 3685) exists according to search results but could not be opened | UNCONFIRMED | `git rev-parse --is-shallow-repository` = true |
| No libcamera-devel, GitHub issue or forum discussion of pipelining RPi ISP/BE jobs was found in five searches. The archives themselves could not be fetched, so "never discussed" is UNCONFIRMED | UNCONFIRMED | WebSearch only |
| libpisp's own BE helper is synchronous: `BackendDevice::Run` queues every node and then dequeues with a 1000 ms timeout | CONFIRMED | `libpisp/src/helpers/backend_device.cpp:120-142@9ba67e6` |
| Other libcamera handlers overlap frames. IPU3 has no state gate (no `state_` in `ipu3.cpp`) and tracks each frame by id: `cio2BufferReady -> computeParams -> paramsComputed -> imgu_->input_->queueBuffer` (`ipu3.cpp:1219-1237, 1292-1326`). `PipelineHandler::completeRequest` completes requests in order from several in flight (`pipeline_handler.cpp:592-600`), so the framework is not the limit | CONFIRMED | libcamera-apertar@6b0b49f |
| Pipelining needs no new buffers at depth 2: TDN ping-pong (job N reads tdn[a] and writes tdn[b]; N+1 reads tdn[b], which the hardware has finished because jobs run in order), 2 config buffers, request-owned preview buffers. Depth 3 would need 3 TDN and 3 config buffers | PROBABLE (from `prepareBe` and the allocation loop) | `pisp.cpp:2760-2774, 1262-1308` |

## 5. How much pipelining could recover (arithmetic)

Measured before L1 while recording (hardware-log:182-193; brief §3). Back end start interval **36.2 ms**. Start->done 34.6 ms
**in log time**. So done->next start = 36.2 - 34.6 = **1.6 ms**: the IPA plus dispatch, with `prepareIsp` included. The sensor
period is 1000/30 = **33.33 ms**, so the cycle is 36.2 - 33.33 = 2.87 ms too long. Idle: start->done 13.4 ms, interval 33.3 ms.

One frame at a time, the cycle is the sum of every serial step (§2). Pipelined at depth 2, the cycle is
`max(t_HW, t_IPA, PH thread work per frame, 33.33 ms)`. The saving is therefore `36.2 - max(t_HW, 33.33)`.

| Hardware BE time while recording (unknown) | Pipelined cycle | fps | Recovered per frame | Verdict |
| --- | --- | --- | --- | --- |
| 34.6 ms (the whole log interval is hardware) | 34.6 | 28.9 | 1.6 ms | still about 11 lost per 10 s ((30-28.9) x 10). **Not enough** |
| 33.3 ms (break-even) | 33.3 | 30.0 | 2.9 ms | no margin at all. Drops on any jitter |
| 19.4 ms (idle 13.4 x 1.45, the CPU's IPC slowdown 1.87/1.30 = 1.44) | 33.3 (sensor-bound) | 30.0 | 2.9 ms (the BE then sits idle 13.9 ms per frame) | Enough. But a one-at-a-time loop would also reach 30 fps if its software latency stayed below 33.3 - 19.4 - 1.6 = 12.3 ms |
| 13.4 ms (no contention slowdown) | 33.3 | 30.0 | 2.9 ms | as above |

How to read the L2 result (PROBABLE, depends on the unmeasured L2 window):
- L2 moved the swap and stats off the PH thread. The thread dropped to 34 % busy, so most of the BE-done dispatch latency
  should be gone. L2 still delivered 26.3-28.2 fps: 1000/28.2 = 35.5 ms to 1000/26.3 = 38.0 ms per cycle. If the IPA/dispatch
  gap stayed at about 1.6 ms, then t_HW is about 35.5-1.6 = **33.9** to 38.0-1.6 = **36.4 ms** while recording. In that case
  pipelining alone gains at most about 1.6 ms (27.6 -> 28.9 fps).
- Caveat 1: L1 (7, 8, 20 missing) against L2 (27, 31, 14) is not a significant difference. Means 11.7 and 24.0, SDs 7.2 and
  8.9, pooled SD 8.1, SE = 8.1 x sqrt(2/3) = 6.6, t = 12.3/6.6 = 1.86, df = 4, p of about 0.14. PROBABLE: "L2 did not help"
  and "L2 made it worse" are both unproven.
- Caveat 2: with L2, the PH thread still spends 0.34 x ~37 ms = about 12.6 ms per frame on something. That work is not named
  (event handling, request requeue, possibly preview 24->32-bit conversion in `beOutputDequeue`) and can still delay the
  BE-done dispatch. UNCONFIRMED.
- Consistency check (PROBABLE): the gap pattern fits a constant deficit. Before L1 the takes delivered about 26.45 fps, so the
  cycle was 37.8 ms and the deficit 4.5 ms per frame. One frame is lost every 33.3/4.5 = 7.4 frames (observed every 5-9).
  The first loss comes after 27-47 frames, which implies 27..47 x 4.5/33.3 = **3.6-6.4 buffers of slack**: the 8 raw buffers
  minus those in the CFE, the BE and Core. Pipelining at depth 2 keeps one more raw buffer in the BE queue and removes one
  buffer of slack.

**If t_HW >= 33.3 ms, pipelining does not help** (PROBABLE, follows from the one-engine queue in §3). Only these would:
(a) less BE work per frame (Q1: TDN off, smaller BE input, earlier crop/downscale); (b) less memory contention for the BE
(Q3; note the AXI QoS 0 hypothesis in §3); (c) **BE decimation**, which does not run the BE on every frame (E5).

**Is 34.6 ms a hardware time? No** (CONFIRMED). `libcam_stages.py:15-16, 59` subtracts the log time of
`Input re-queue to ISP` (`pisp.cpp:2754`, logged **before** `be_->Prepare()` and the QBUFs) from the log time of
`Stream ISP Input buffer complete` (`pisp.cpp:2277`, logged when the PH thread gets round to the V4L2 dequeue). Both lines are
stamped with `steady_clock` at the moment the line runs (`libcamera/base/log.cpp:857`, `utils.h:82`). The done line also prints
`buffer->metadata().timestamp` (`pisp.cpp:2277-2279`). That value is the V4L2 timestamp (`v4l2_videodevice.cpp:1899`), which the
BE ISR set to `ktime_get_ns()` at job completion (`pisp_be.c:637-641`). CLOCK_MONOTONIC and libstdc++ `steady_clock` share a
time base (PROBABLE: libstdc++ implements `steady_clock::now()` with `clock_gettime(CLOCK_MONOTONIC)`; not opened here).
So for each frame:
- `hw_done_upper = ts_done - logtime(Input re-queue)` = Prepare + QBUF + hardware. This is an upper bound on t_HW.
- `done_latency = logtime(ISP Input complete) - ts_done` = how long the completion waited for the pipeline thread.
- The same holds for the CFE line: its `timestamp:` is the start-of-frame interrupt time (`rp1_cfe/cfe.c:692, 714`).

## 6. Read-only measurements that give the hardware BE time

**M1, from the libcamera debug log (no ftrace).** If the 20:50 journal window is still on the Pi, re-parse it. Otherwise Patrik
enables the existing `libcamera-debug.conf` drop-in (`LIBCAMERA_LOG_LEVELS=RPI:0,RPiStream:0`), restarts Core, records 10 s at
30 fps, and then:
```
journalctl -u apertar-core --since "-2min" -o cat > /tmp/rpi0.txt
python3 - /tmp/rpi0.txt <<'EOF'
import re,sys,statistics as S
T=re.compile(r'^\[(\d+):(\d+):(\d+\.\d+)\]'); st={}; up=[]; lat=[]
for l in open(sys.argv[1],errors='replace'):
    m=T.match(l)
    if not m: continue
    t=int(m[1])*3600+int(m[2])*60+float(m[3])
    a=re.search(r'Input re-queue to ISP, buffer id (\d+)',l)
    if a: st[a[1]]=t; continue
    b=re.search(r'Stream ISP Input buffer complete, buffer id (\d+), timestamp: (\d+)',l)
    if b and b[1] in st:
        d=int(b[2])/1e9; up.append((d-st.pop(b[1]))*1e3); lat.append((t-d)*1e3)
for n,v in (('BE hw upper (ms)',up),('done latency (ms)',lat)):
    v.sort(); print(n,len(v),'median %.1f p90 %.1f'%(S.median(v),v[int(.9*(len(v)-1))]))
EOF
```
(The unit name `apertar-core` is taken from the drop-in path `/etc/systemd/system/apertar-core.service.d/` in the brief §8.)

**M2, exact hardware start/done from interrupts (ftrace; no restart; run during a take).** First, read-only:
`grep -E 'pispbe|rp1-cfe' /proc/interrupts` (the names come from `pisp_be.c:40,1758` and `cfe.c:2301`) and
`ls /sys/kernel/tracing/events/irq/irq_handler_entry /sys/kernel/tracing/events/v4l2`. The tracer options are not set
explicitly in the defconfig; they come in through `CONFIG_SCHED_TRACER=y`/`CONFIG_STACK_TRACER=y` (`bcm2712_defconfig:1782-1784`).
PROBABLE they are present; to confirm, `grep -E 'CONFIG_(EVENT_TRACING|FTRACE)=' /boot/config-$(uname -r)`. Then Patrik runs:
```
sudo sh -c 'T=/sys/kernel/tracing; B=$(cat $T/buffer_size_kb)
echo 0 > $T/tracing_on; echo > $T/trace; echo 16384 > $T/buffer_size_kb
echo "name == \"pispbe\" || name == \"rp1-cfe\"" > $T/events/irq/irq_handler_entry/filter
echo 1 > $T/events/irq/irq_handler_entry/enable
echo 1 > $T/events/v4l2/v4l2_qbuf/enable; echo 1 > $T/events/v4l2/v4l2_dqbuf/enable
echo 1 > $T/tracing_on; sleep 5; echo 0 > $T/tracing_on
cat $T/trace > /tmp/be-trace.txt
echo 0 > $T/events/irq/irq_handler_entry/enable; echo 0 > $T/events/irq/irq_handler_entry/filter
echo 0 > $T/events/v4l2/v4l2_qbuf/enable; echo 0 > $T/events/v4l2/v4l2_dqbuf/enable
echo $B > $T/buffer_size_kb'
```
Analysis. Find the pispbe-config minor with
`for d in /sys/class/video4linux/video*; do echo "$d $(cat $d/name) $(cat $d/dev)"; done`. Today the BE is idle between jobs, so
each job gives `v4l2_qbuf: minor = <config minor>` (job submitted), then a pispbe IRQ (**start**), then a pispbe IRQ (**done**).
t_HW = done - start. The BE idle gap = next start - done. The IRQ deltas alternate between t_HW and the gap:
```
awk '/name=pispbe/{for(i=1;i<=NF;i++)if($i=="irq_handler_entry:"){t=$(i-1);sub(/:$/,"",t)} if(p)printf "%.2f\n",(t-p)*1e3; p=t}' /tmp/be-trace.txt | paste - - | head -40
```
`v4l2_qbuf`/`v4l2_dqbuf` fire at ioctl time (`v4l2-ioctl.c:3477-3479`) and carry the minor and the sequence. The rp1-cfe IRQs give
SOF/EOF on the same clock. (The `vb2_v4l2_*` events are defined in `include/trace/events/v4l2.h` but no caller exists in this
tree, so do not rely on them. `vb2:vb2_buf_done` fires in the ISR but has no minor.)

## Experiments this suggests

**E1. One RPI:0 window with L2 on, analysed with M1** (no code change; `QBC_RAW_CPU_WORKER=1`, `QBC_RAW_STATS_ROW_STEP=4`, 30 fps,
uncompressed, recording 10 s). Also one window with L1 only (worker off).
- Prediction if the BE is the limit (H-BE): L2 `BE hw upper` median **>= 33 ms**, `done latency` median **<= 2 ms**,
  start interval 35-38 ms. L1: `done latency` median several ms, 3 ms or more (because of the 78 % finding), `BE hw upper` about the same as L2.
- Rules H-BE out: `BE hw upper` median **<= 28 ms** while the interval is >= 35 ms. Then at least 7 ms per frame is software
  latency, and E4 (pipelining) or more PH-thread clean-up is the lever.

**E2. ftrace interrupt timing (M2), once in preview only and once recording, same build as E1.**
- Prediction: preview-only t_HW **<= 13 ms**. Recording t_HW **>= 33 ms** under H-BE. The start IRQ follows the config QBUF
  within about 0.1 ms.
- Rules H-BE out: recording t_HW **< 30 ms**. If the BE idle gap (done -> next start) is >= 4 ms, the loss is in the software loop.

**E3. BE-free ceiling: configure no ISP output stream** (raw only). Then `beEnabled_ = false` (`pisp.cpp:2033`) and
`prepareIspComplete` hands the raw buffer back at once without running the BE (`pisp.cpp:2377-2384`). This needs a Core test
switch "record without preview", or a libcamera `cam` run with only a raw stream (`cam -c1 -C300 -s role=raw,width=3840,height=2160`,
syntax to check with `cam --help` on the Pi). Not E3: a request that simply carries no preview buffer **still runs the BE** into an
internal buffer (`rpi_stream.cpp:131-145`, allocation `pisp.cpp:1305-1307`), so the brief's "no ISP output buffer in the request"
idea does not remove BE work (CONFIRMED code path).
- Measurement: delivered fps and `dropped_gap_estimate` (Core). With `cam`, the per-frame sequence numbers it prints.
- Prediction under H-BE: **30.00 fps, 0 gaps** while the copy and NVMe traffic still run.
- Rules H-BE out: still under 29.5 fps with no BE at all. Then the limit is CFE, CPU passes or memory, not the BE.
- Caveat: removing the BE also removes its own memory traffic, so a clean result does not separate "BE is slow" from "BE adds the
  contention". E2 separates them.

**E4. Pipelining prototype, depth 2** (libcamera `apertar` branch, only if E1/E2 give t_HW <= about 31 ms).
- Change: replace the `Idle` gate with an in-flight count of up to 2. Send `prepareIsp(N+1)` as soon as `prepareIspComplete(N)` has
  queued BE job N. Keep one IPA call outstanding at a time. Mark each request "IPA done" individually instead of using the global
  `IpaComplete`. Route `metadataReady` to the request whose `prepareIsp` is outstanding, not `front()`. Make
  `checkRequestCompleted` loop over completed front requests. Keep the 2 config and 2 TDN buffers (§4).
  PROBABLE size: 150-300 lines in `pisp.cpp` and `pipeline_base.cpp`.
- Measurement: E1 parse plus E2 trace. The BE idle gap should fall to about 0 (done(N) and start(N+1) in one IRQ).
- Prediction: cycle = max(t_HW, 33.3). If t_HW <= 31 ms, **30.00 fps and 0 gaps** over 3 x 10 s takes.
- Rules it out: under 0.5 fps gain over L2 with the gap near 0. Then the BE hardware is the limit.

**E5. BE decimation while recording** (only if t_HW >= 33 ms).
- Change: libcamera: when a request carries no ISP output buffer, skip `prepareBe`, return the raw buffer the way the
  `!beEnabled_` path does (`pisp.cpp:2377-2384`) and force a TDN reset for the next BE frame (`tdnReset_`, `ipa/rpi/pisp/pisp.cpp:826-856`).
  Core: attach the preview buffer only to every second request while recording.
- Measurement: delivered fps and `dropped_gap_estimate`, plus E2 (BE busy time per 66.7 ms).
- Prediction: BE load halves (about 17 ms per 33 ms). **30.00 fps**, preview at 15 fps, AGC/AWB unchanged (they use FE stats on
  every frame).
- Rules it out: under 29.5 fps. Then something besides the BE limits the cycle.

**E6. Is the BE slowed by contention?** Run E2 while recording with Core's copy replaced by a no-op (brief §6 idea), and again
with the swap off (16-bit swap is mandatory for correct data, so run it only as a timing test).
- Prediction under the contention view: t_HW falls from >= 33 ms toward the idle about 13 ms as traffic is removed.
- Rules it out: t_HW unchanged. Then the BE's own work for this configuration is the cost (Q1).

Pre-check for every experiment (read-only): `vcgencmd measure_clock isp`. The BE clock is firmware clock 7
(`bcm2712-ds.dtsi:386-394`, `clocks = <&firmware_clocks 7>`). PROBABLE that `isp` is accepted on the Pi 5. Also run
`grep -E 'pispbe|rp1-cfe' /proc/interrupts` to see the IRQ CPU.

## Unknowns

- **t_HW for this configuration, idle and recording.** Only the Pi can settle it (E1/E2). Every conclusion in §5 depends on it.
- Whether the PiSP BE can ever run two jobs at once. The specification PDF (datasheets.raspberrypi.com) was blocked by the proxy.
  The driver code points to one running job plus one queued job.
- Whether the 20:50 RPI:0 journal window still exists on the Pi (`journalctl -u apertar-core --since "2026-10-26 20:49" --until "2026-10-26 20:53" -o cat | wc -l`).
- What the remaining 34 % PH-thread load under L2 is, about 12.6 ms per frame. `usample.py` on the CameraManager thread with L2 would show it.
- Whether the Pi's kernel has `CONFIG_EVENT_TRACING` and tracefs mounted. Whether `vcgencmd measure_clock isp` works on the Pi 5.
- The meaning of `AXI QOS=0` on the BCM2712 fabric (`pisp_be.c:1716-1720`).
- Whether the installed libpisp is 1.3.0. It does not matter for Q2: `Prepare` copies the config per job (`backend_prepare.cpp:1002-1043@9ba67e6`).
- Whether upstream ever discussed pipelining on libcamera-devel. The archives were unreachable from here.
- Side note, UNCONFIRMED effect: the `disable_tdn` path removes `TdnInput` twice and never removes `TdnOutput` from `streams_`
  (`pisp.cpp:1659-1665@6b0b49f`, identical in `7e9fef0` and `bfe0b76`). Check this before using `disable_tdn` in any Q1 experiment.

## Verification

Verifier: adversarial pass (Claude Opus 5.5, cloud subagent), 2026-10-26. Every cited line was reopened at the cited commit
(libcamera-apertar `6b0b49f`, libcamera-qbc `7e9fef0`, libcamera `bfe0b76`, libpisp `9ba67e6`, kernel-rpi `5bd564a`). Extra sources: a
blob-less, non-shallow clone of `github.com/raspberrypi/libcamera` `main` @ `c682979` (scratch only, nothing in the source trees touched), and
GitHub web pages. `pisp_be_config` sizes were measured by compiling the kernel uapi header on the host. `datasheets.raspberrypi.com` still does not
resolve (ENOTFOUND) and `git.kernel.org` is refused by the proxy. Verdicts: CONFIRMED / CORRECTED (holds, but a cite or detail is wrong) / REFUTED /
UNVERIFIABLE (needs the Pi or a source that cannot be reached). Abbreviations: `la` = libcamera-apertar, `kr` = kernel-rpi, `rpl` = raspberrypi/libcamera.

| # | Claim (report section) | Verdict | Evidence |
| --- | --- | --- | --- |
| 1 | Gate is `state_ != State::Idle` in `tryRunPipeline` (Short answer, §1) | CONFIRMED | `la/src/libcamera/pipeline/rpi/pisp/pisp.cpp:3112-3117@6b0b49f`; `libcamera-qbc/.../pisp.cpp:2860-2863@7e9fef0` |
| 2 | `Idle` returns only when the front request has no pending buffers and the state is `IpaComplete` | CONFIRMED | `la/src/libcamera/pipeline/rpi/common/pipeline_base.cpp:1525-1542@6b0b49f` (`completeRequest` 1538, `Idle` 1542) |
| 3 | Inline path waits for the "front CFE job" (§1 gate row) | CORRECTED | The inline path calls `cfeJobComplete()`, which tests the **newest** job, `cfeJobQueue_.back()` (`la/.../pisp.cpp:1096-1102@6b0b49f`). Only the L2 path (`cfeJobReady`, 1105-1112) tests the front. Upstream `main` is the same (`rpl/.../pisp.cpp:837,2330@c682979`). No effect today (PROBABLE: depends on fd order): the streams are opened Output0, Config, Stats (`pisp.cpp:1428-1447`), so a job is incomplete only between its image and stats dequeues |
| 4 | States enum, single-thread comment, `handleState` fall-through, start sets `Idle` | CONFIRMED | `la/.../common/pipeline_base.h:119-124`; `pipeline_base.cpp:1502-1523, 724@6b0b49f` |
| 5 | `Idle -> Busy`, then `pop_front` + `prepareIsp` | CONFIRMED | `la/.../pisp.cpp:3139, 3222-3223@6b0b49f` |
| 6 | `prepareIsp` is `[async]` and runs on the IPA proxy thread; the IPA is in-process | CONFIRMED (in-process is PROBABLE) | `la/include/libcamera/ipa/raspberrypi.mojom:201`; `la/utils/codegen/ipc/generators/libcamera_templates/module_ipa_proxy.cpp.tmpl:90,95,111@6b0b49f`; `lessons/hardware-log.md:208` (maps). That the IPA .so being mapped proves it is in-process is an inference |
| 7 | PiSP stats are inline: `processStats` inside `prepareIsp`; `statsInline = true` | CONFIRMED | `la/src/ipa/rpi/common/ipa_base.cpp:500-501, 515-516, 519@6b0b49f`; `la/src/ipa/rpi/controller/controller.cpp:189` (VC4 `false` at :173); `metadataReady.emit` in `reportMetadata` at `ipa_base.cpp:1777` |
| 8 | `prepareIspComplete` queues the BE and then sets `IpaComplete` | CONFIRMED | `la/.../pisp.cpp:2363-2389@6b0b49f` (2385, 2387) |
| 9 | `prepareBe` order: log 2754, Input 2757, TDN 2760-2764, stitch 2766-2771, config 2774, `Prepare` 2779, config QBUF 2800; the kernel forms the job on that last QBUF | CONFIRMED | `la/.../pisp.cpp:2750-2801@6b0b49f`; `kr/drivers/media/platform/raspberrypi/pisp_be/pisp_be.c:501-506, 885-892@5bd564a` (no config buffer means no job) |
| 10 | `IpaComplete -> Idle` fires on `beInputDequeue`/`beOutputDequeue`; `processStatsComplete` leaves the state alone | CONFIRMED | `la/.../pisp.cpp:2272-2284, 2286-2338, 2340-2347@6b0b49f` |
| 11 | `completeRequest` emits `requestCompleted` synchronously, before `Idle` | CONFIRMED | `la/src/libcamera/pipeline_handler.cpp:584-603`; `la/src/libcamera/camera.cpp:1488@6b0b49f` |
| 12 | `handleState` callers: 836-837, 2269, 2162, 2283, 2337, 2388 | CONFIRMED | `la/.../pipeline_base.cpp:836-837`; `pisp.cpp:2162, 2269, 2283, 2337, 2388@6b0b49f` |
| 13 | "Only one of these events can start the next frame: in practice the BE completion" (§1) | CORRECTED | True only under backlog. When nothing is queued (25 fps, preview), the CFE stats dequeue (`pisp.cpp:2269`) starts the frame. With L2, `rawCpuJobDone` (`:2162`) starts it when the front job's CPU pass ends after the request completed |
| 14 | Other single-frame assumptions: `metadataReady` into `front()`; `front()` in `tryRunPipeline`/`checkRequestCompleted`; `Prepare` unlocked while FE is locked | CONFIRMED | `la/.../pipeline_base.cpp:1286-1287, 1527`; `pisp.cpp:3122, 2779, 2741@6b0b49f`. The IPA side never locks the `BackEnd` either (only `scoped_lock<FrontEnd>`, `la/src/ipa/rpi/pisp/pisp.cpp:337,379,492,1034,1101,1181`). Incomplete list: see Missed 4 |
| 15 | VC4 needed the serial loop: stats come from the ISP; `IpaComplete` only in `processStatsComplete` | CONFIRMED | `la/src/libcamera/pipeline/rpi/vc4/vc4.cpp:884-888, 906@6b0b49f` |
| 16 | "Inherited from the VC4 handler" (PROBABLE in the report) | CONFIRMED (upgrade); the reason stays PROBABLE | `rpl@740fd1b6` (Naushir Patuck, 2020-05-03, "libcamera: pipeline: Raspberry Pi pipeline handler") `raspberrypi.cpp:345` `enum class State { Stopped, Idle, Busy, IpaComplete }`, `:1469` same `Idle` gate, `:1194` `IpaComplete` set on `RPI_IPA_ACTION_STATS_METADATA_COMPLETE` (ISP stats). Neither the commit message nor the code says why only one frame runs at a time |
| 17 | "Local clones are shallow, so the 2020 origin cannot be read here" (§4) | REFUTED (as a limit) | A blob-less clone of `github.com/raspberrypi/libcamera` is non-shallow (`git rev-parse --is-shallow-repository` = false) and contains `740fd1b6` (row 16) |
| 18 | v0.0.1 has the same states, gate and "Process all the user controls by the IPA..." comment | CONFIRMED | `rpl@v0.0.1:src/libcamera/pipeline/raspberrypi/raspberrypi.cpp:254, 2131, 2153-2155` |
| 19 | RPi fork `main` has no pipelining commit: 33 `pisp.cpp` titles, newest c682979 2026-10-09; `pipeline_base.cpp` newest d48b72e 2026-09-29; current `handleState`/`checkRequestCompleted`/`metadataReady` unchanged | CONFIRMED | `git log -- <path>` on `rpl` main: 33 commits, newest `c682979b 2026-10-09`, `d48b72e7 2026-09-29`. No title mentions pipelining or in-flight depth. `rpl/main:.../pipeline_base.cpp:1253-1260, 1499-1516`; `pisp.cpp:2330` |
| 20 | Never discussed on libcamera-devel | UNVERIFIABLE | Archives unreachable. Five searches found nothing; that is not proof |
| 21 | Kernel accepts any number of jobs; libcamera's 2 config / 2 TDN / 2 stitch buffers allow 2 in flight | CONFIRMED | `kr/.../pisp_be.c:473-595` (list add 575), `874-893@5bd564a`; `la/.../pisp.cpp:1305-1307@6b0b49f` |
| 22 | Hardware queue depth 2 (`running_job`, `queued_job`); `hw_busy` cleared on each start interrupt | CONFIRMED | `kr/.../pisp_be.c:239-244, 597-631, 678-690@5bd564a` |
| 23 | Job N+1 can be queued while N runs (`COPY_CONFIG | QUEUE_JOB`, `STATUS_QUEUED` check); ISR comment on start+finish at once (cited 672-676) | CORRECTED (cite) | Code `pisp_be.c:270, 319-321` CONFIRMED. The comment is at `:667-671`; 672-676 is the code below it |
| 24 | The two jobs never execute at the same time | UNVERIFIABLE | The driver models one running job (`pisp_be.c:672-690`). The PiSP spec PDF (`datasheets.raspberrypi.com`) does not resolve from here |
| 25 | Register programming: `sizeof(pisp_be_config)` 6476, offset 120, (6476-120)/4 = 1589 writes; ~1620 MMIO writes/job; ~0.16 ms | CONFIRMED (cost PROBABLE) | Host compile of `kr/include/uapi/linux/media/raspberrypi/pisp_be_config.h`: sizeof=6476, offsetof(global.bayer_order)=120, `pisp_tile`=160 B, 64 tiles. 26+2+1589+2+1 = 1620 writes, plus 26 read-backs (`pisp_be.c:279-321`). 1620 x 0.1 us = 0.162 ms |
| 26 | Programming runs in the QBUF ioctl when idle, in the start ISR when a job waits | CONFIRMED | `kr/.../pisp_be.c:891-892, 701@5bd564a` |
| 27 | 2 node groups share one queue and one engine | CONFIRMED | `kr/.../pisp_be.c:32-38, 239-244@5bd564a` |
| 28 | Start+done IRQs enabled; IRQ name `pispbe`; CFE IRQ `rp1-cfe` | CONFIRMED | `kr/.../pisp_be.c:40, 1723, 1758-1759`; `kr/.../rp1_cfe/cfe.c:2301@5bd564a` |
| 29 | Every buffer of a job stamped with `ktime_get_ns()` at done; `TIMESTAMP_MONOTONIC` | CONFIRMED | `kr/.../pisp_be.c:633-649, 1454@5bd564a` |
| 30 | `AXI QOS=0` comment; its meaning on BCM2712 | CONFIRMED comment; meaning UNVERIFIABLE | `kr/.../pisp_be.c:1716-1720@5bd564a` |
| 31 | Linux 972eed0 "media: pisp_be: Split jobs creation and scheduling", Jul 2025; job assembly moved out of IRQ context (UNCONFIRMED in the report) | CONFIRMED (upgrade) | github.com/torvalds/linux/commit/972eed08261fb1048afea8e8f7db05b5531eed66 (Jacopo Mondi, committed by Hans Verkuil; listed Jul 3, 2025): "To avoid executing the time consuming job creation in interrupt context split the job creation and job scheduling in two distinct operations." The same message says `pispbe_schedule()` was already called "at ... irq handler" time, which supports "queued jobs since the 2024 driver" |
| 32 | libpisp `BackendDevice::Run` is synchronous (1000 ms dequeue) | CONFIRMED | `libpisp/src/helpers/backend_device.cpp:120-143@9ba67e6` |
| 33 | IPU3 has no state gate and overlaps frames by id; `completeRequest` completes in order | CONFIRMED | `la/src/libcamera/pipeline/ipu3/ipu3.cpp` (0 hits for `state_`), `:1219-1237, 1292-1326`; `pipeline_handler.cpp:592-600@6b0b49f` |
| 34 | Depth 2 needs no new buffers (TDN ping-pong, 2 config) | CONFIRMED (code); safety PROBABLE | `la/.../pisp.cpp:2760-2774, 1262-1308@6b0b49f`. Holds because jobs run in order. Hazard: `acquireBuffer` on 2 config buffers ASSERTs if a third `prepareBe` comes before a config dequeue (`pisp.cpp:2774-2775`; `rpi_stream.cpp:211-221`) |
| 35 | 34.6 ms is log time between "Input re-queue to ISP" and "Stream ISP Input buffer complete" | CONFIRMED | `apertar-kb/working/tools/libcam_stages.py:15-16, 59`; `la/.../pisp.cpp:2754, 2277@6b0b49f`; `la/src/libcamera/base/log.cpp:857`; `la/include/libcamera/base/utils.h:82` |
| 36 | The done line's `timestamp:` is the BE ISR time | CONFIRMED | `la/.../pisp.cpp:2277-2279`; `la/src/libcamera/v4l2_videodevice.cpp:1893-1900` (set before the output-type return at 1902); `kr/.../pisp_be.c:637-643` (the driver overwrites the timestamp at done, so an OUTPUT queue cannot carry user space's value) |
| 37 | libstdc++ `steady_clock` = `CLOCK_MONOTONIC` | UNVERIFIABLE (here) | libstdc++ source not opened. Check on the Pi: `python3 -c "import time;print(time.clock_gettime(time.CLOCK_MONOTONIC))"` next to a libcamera log line |
| 38 | Short answer: the most pipelining can recover is 1.6 ms to "about 21 ms" of 36.2 ms | CORRECTED | BE idle per cycle = 36.2 - t_HW: 36.2 - 34.6 = 1.6 ms; 36.2 - 13.4 = **22.8 ms**. 21.2 = 34.6 - 13.4 leaves out the 1.6 ms gap. And the cycle time that can be **recovered** is at most 36.2 - 33.33 = **2.87 ms** in every case, as the report's own §5 table shows. 22.8 ms is BE idle time, not a saving |
| 39 | t_HW >= 33.3 ms means no 30 fps by pipelining; best case 1000/34.6 = 28.9 fps | CONFIRMED | One engine (rows 22, 24). 1000/34.6 = 28.90. 28.9 is the case t_HW = 34.6, not every t_HW >= 33.3 |
| 40 | L2 at 26.3-28.2 fps "points to a BE of about 34-36 ms while recording" | CORRECTED (substance) | Arithmetic CONFIRMED: 1000/28.2 - 1.6 = 33.9; 1000/26.3 - 1.6 = 36.4. But it is an **upper bound**. It assumes zero done latency, while the report's caveat 2 leaves 12.6 ms/frame of PH-thread work unexplained. It also needs the BE to run 33.9/13.4 = 2.53x to 36.4/13.4 = 2.72x slower than the idle *upper bound*. The CPU slowed 1.44x (IPC 1.87/1.30, `hardware-log.md:161-162`) or ~1.6x (`hardware-log.md:144-145`). The report's own §5 row 3 gives 19.4 ms. Q1 (`q1-backend.md`, short answer 4) gets the same 2.2-2.5x threshold |
| 41 | §5 table: 1000/34.6 = 28.9 fps, (30 - 28.9) x 10 = 11 lost; 13.4 x 1.45 = 19.4; 1.87/1.30 = 1.44; 33.3 - 19.4 - 1.6 = 12.3 | CONFIRMED | Recomputed: 28.90; 11; 19.43; 1.438; 12.3 |
| 42 | Caveat 1: means 11.7/24.0, SDs 7.2/8.9, pooled 8.1, SE 6.6, t = 1.86, df 4, p ~0.14 | CONFIRMED | Recomputed: 11.67/24.00, 7.23/8.89, 8.10, 6.62, t = 1.864, two-sided p = 0.136 |
| 43 | Caveat 2: 0.34 x 37 ms = 12.6 ms/frame of PH-thread work, unnamed | CONFIRMED (arithmetic); content UNVERIFIABLE | 0.34 x 37 = 12.58 ms |
| 44 | Consistency check: 26.45 fps -> 37.8 ms, deficit 4.5 ms, a loss every 7.4 frames, 3.6-6.4 buffers of slack | CONFIRMED | 1000/26.45 = 37.81; 37.81 - 33.33 = 4.47; 33.33/4.47 = 7.45; 27 x 4.47/33.33 = 3.62 and 47 x 4.47/33.33 = 6.31 (6.35 with the rounded 4.5) |
| 45 | "Pipelining at depth 2 keeps one more raw buffer in the BE queue and removes one buffer of slack" | REFUTED | A backlogged frame holds its raw buffer whether it waits in `cfeJobQueue_` or in the BE's V4L2 queue. The CFE sees the same number of free buffers. Without a backlog, the queued job is a frame that is already captured. Pipelining only shortens the cycle (PROBABLE reasoning from `la/.../pisp.cpp:2171-2203, 3112-3123`) |
| 46 | M1 parser and log format | CONFIRMED (format); result UNVERIFIABLE | `la/src/libcamera/base/utils.cpp:205-217` (`H:MM:SS.nnnnnnnnn`, hours unbounded, matches the regex), `log.cpp:246-256` (stream target prefixes the time). Unit name `apertar-core` from the brief §8 |
| 47 | M2: tracer options via `CONFIG_SCHED_TRACER`/`STACK_TRACER`; tracepoints at ioctl time; `vb2_v4l2_*` have no caller; `vb2_buf_done` has no minor | CONFIRMED | `kr/arch/arm64/configs/bcm2712_defconfig:1782-1784` (no explicit `EVENT_TRACING`); `kr/drivers/media/v4l2-core/v4l2-ioctl.c:3475-3479`; only export lines for `vb2_v4l2_*` (`v4l2-trace.c:9-12`); `kr/include/trace/events/vb2.h` fields (owner, counts, index, type, bytesused, timestamp) |
| 48 | M2/E2 order "v4l2_qbuf (job submitted), then pispbe IRQ (start)"; "start IRQ follows the config QBUF within about 0.1 ms" | CORRECTED | `trace_v4l2_qbuf` fires **after** the ioctl handler returns (`v4l2-ioctl.c:3475-3479`). The job is written to the hardware **inside** that handler (`pisp_be.c:891-892 -> 319-321`). So the start IRQ can appear in the trace before the `v4l2_qbuf` event. Use the IRQ pairs (the awk) and not the qbuf->IRQ delta. Also check that `paste - -` starts on a start IRQ |
| 49 | E3: no ISP output stream -> `beEnabled_ = false` -> raw handed back at once; a request without a preview buffer still runs the BE into an internal buffer | CONFIRMED | `la/.../pisp.cpp:1921-1951, 2033, 2377-2384`; `la/.../pipeline_base.cpp:795-806`; `la/.../rpi_stream.cpp:131-152@6b0b49f`; External flag on ISP outputs `pisp.cpp:1989` |
| 50 | E5 change: "skip `prepareBe` when a request carries no ISP output buffer ... force a TDN reset" | REFUTED (as written) | It would stall. A request without a preview buffer still **queues an internal buffer to the BE output node when the request is queued** (`pipeline_base.cpp:806` -> `rpi_stream.cpp:131-152`). The kernel takes the first ready buffer of each node (`pisp_be.c:557-559`). So the next BE job writes into that stale internal buffer. The next request's preview buffer stays queued, the request keeps a pending buffer, `handleStreamBuffer` matches only `front()` (`pipeline_base.cpp:1472-1473`), the state stays `IpaComplete`, and no further BE job is started. Also, `tdnReset_` is private IPA state (`la/src/ipa/rpi/pisp/pisp.cpp:282, 826-856`), so "force a TDN reset" needs an IPA interface change |
| 51 | Pre-check: BE clock is firmware clock 7; `vcgencmd measure_clock isp` works on Pi 5 | CONFIRMED (DT); command UNVERIFIABLE | `kr/arch/arm64/boot/dts/broadcom/bcm2712-ds.dtsi:386-394@5bd564a` |
| 52 | `disable_tdn` removes `TdnInput` twice and never `TdnOutput`, identical in 7e9fef0 and bfe0b76 | CONFIRMED; effect UNVERIFIABLE | `la/.../pisp.cpp:1659-1665@6b0b49f`; `libcamera-qbc/.../pisp.cpp:1478-1479@7e9fef0`; `libcamera/.../pisp.cpp:1370-1371@bfe0b76` |
| 53 | `BackEnd::Prepare` copies config + tiles per job, so the installed libpisp version does not matter for Q2 | CONFIRMED | `libpisp/src/libpisp/backend/backend_prepare.cpp:1002-1043@9ba67e6` (copies at 1036-1038, clears dirty flags at 1041) |
| 54 | Measured inputs: 36.2 / 34.6 / 13.4 / 33.3 ms, 78 %, 217 ms (hardware-log:182-193); L1 7/8/20, L2 27/31/14, 34 % busy | CONFIRMED | `apertar-kb/lessons/hardware-log.md:184-194, 209-211, 225-226` |
| 55 | E1, E2, E4 predictions and kill thresholds (H-BE ruled out if `BE hw upper` <= 28 ms at interval >= 35 ms; 35 - 28 = 7 ms software) | UNVERIFIABLE (need the Pi); logic CONFIRMED | Arithmetic checks. E4's "150-300 lines" is PROBABLE and too low: see Missed 4 |

Counts (55 rows, by primary verdict): **CONFIRMED 42** (rows 16 and 31 are upgrades of the report's PROBABLE/UNCONFIRMED; rows 30, 43, 46, 51, 52
are confirmed with an unverifiable effect), **CORRECTED 6** (rows 3, 13, 23, 38, 40, 48), **REFUTED 3** (rows 17, 45, 50), **UNVERIFIABLE 4**
(rows 20, 24, 37, 55). 42 + 6 + 3 + 4 = 55.

### Corrections that change substance

1. **The t_HW estimate from L2 (row 40) is an upper bound, not an estimate.** The report leans on "BE about 34-36 ms" in its short answer and
   when it gates E4 ("only if t_HW <= 31 ms") and makes E5 conditional. The same data fit t_HW ~19-26 ms plus PH-thread latency just as well:
   12.6 ms/frame of PH work is unexplained, and the BE would have to slow 2.5-2.7x against 1.4-1.6x measured on the CPU. On the present
   evidence, E4 (pipelining) and the Q1 BE-work levers cannot be ranked against each other. E1/E2 decide. Until then, neither "pipelining
   cannot help" nor "pipelining is the fix" is PROBABLE.
2. **The ceiling on the gain (row 38).** No t_HW lets pipelining shorten the cycle by more than 2.87 ms (36.2 -> 33.33). "About 21 ms" is BE idle time
   (correctly 22.8 ms) and must not be read as a saving.
3. **E5 as specified would stall the pipeline (row 50).** BE output buffers, internal ones included, are queued to the kernel when the request is
   queued, not in `prepareBe`. A decimation patch must also stop `queueRequestDevice` from queueing an internal ISP-output buffer for the
   skipped requests (or must dequeue/return it). It also needs an IPA change for the TDN reset. Size and risk are higher than the report implies.
4. **"Pipelining removes one buffer of slack" is wrong (row 45).** Pipelining does not change how many raw buffers the CFE has free. It does
   not trade slack for throughput.

### Missed

1. The E5 stall (Corrections 3): the BE output queue is filled at request-queue time (`pipeline_base.cpp:806`, `rpi_stream.cpp:131-152`, kernel FIFO
   `pisp_be.c:557-559`).
2. The 2020 origin can be read (`rpl@740fd1b6`). It confirms the VC4 inheritance (states, gate, `IpaComplete` only after ISP stats) and that no reason was ever
   written down. This upgrades §4's UNCONFIRMED row.
3. `libcam_stages.py:58` already prints "IPA signalled -> back end start". That number measures the IPA + dispatch gap the report derives by
   subtracting medians (1.6 ms). Re-parse the 20:50 window if the Pi still has it: `journalctl -u apertar-core --since "2026-10-26 20:49" --until
   "2026-10-26 20:53" -o cat > /tmp/w.txt; python3 ~/apertar-kb/working/tools/libcam_stages.py /tmp/w.txt` (path to the tools on the Pi
   UNCONFIRMED). Also, the `timestamp:` on "Input re-queue to ISP" is the CFE start-of-frame time (`pisp.cpp:2754-2755`, `cfe.c:692,714`), so
   M1 can also print SOF -> BE-done per frame.
4. E4 scope: `handleStreamBuffer` matches buffers only against `requestQueue_.front()` (`pipeline_base.cpp:1472-1473`). With two requests in flight,
   a buffer for N+1 that comes back while N is still front is recycled to the stream, and N+1 never completes. Two more items for the depth-2
   patch: this, and the 2-config-buffer `acquireBuffer` ASSERT (`pisp.cpp:2774-2775`).
5. M2 ordering: the start IRQ can come before the `v4l2_qbuf` event (row 48).

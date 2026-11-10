# Installing the campaign helper (Patrik, on the Pi)

The campaign helper is a small root script for the NVMe campaign. Unattended, the runner may read the card's health,
check the card, trim it and pause the timers. Your password is still needed for anything that changes Core: loading the
depth 4 pipeline file and restarting Core, plus reboot and power-off.
Files: `apertar-campaign-helper.sh` (the script) and `campaign-sudoers` (which commands pi may run). Both sit in this folder.

## 1. Install (once, at S0)

Run these as pi on the Pi after the KB has been synced to it:

```bash
cd ~/apertar-kb/working/drop-frames/nvme-campaign/scripts
sudo install -o root -g root -m 0755 apertar-campaign-helper.sh /usr/local/libexec/apertar-campaign-helper
sudo install -o root -g root -m 0440 campaign-sudoers /etc/sudoers.d/apertar-nvme-campaign
sudo visudo -cf /etc/sudoers.d/apertar-nvme-campaign
md5sum apertar-campaign-helper.sh /usr/local/libexec/apertar-campaign-helper
```

`visudo` must say `parsed OK`. If it doesn't, remove the file at once: `sudo rm /etc/sudoers.d/apertar-nvme-campaign`.
The two md5 sums must be the same.

## 2. Test

```bash
sudo -k
sudo -n /usr/local/libexec/apertar-campaign-helper status    # must print the status, no password asked
sudo -n /usr/local/libexec/apertar-campaign-helper arm       # must FAIL ("a password is required")
```

## 3. Every night (after each power-on): one command, no password

FE depth 4 is already set by `/home/pi/start-apertar-core.sh` (since 2026-11-06), so it survives the power-off and nothing
needs re-arming. The runner masks the timers itself (`timers-mask` needs no password). Start a night from any terminal on the
Pi, for example an ssh app on your phone:

```bash
bash ~/nvme-campaign/start-night.sh S2
bash ~/nvme-campaign/start-night.sh S4,S5 --go "S4=unconditional" --go "S5=if all_passed S4"
bash ~/nvme-campaign/start-night.sh S6,END --go "S6=unconditional"
cat ~/longtakes/nvme-20261110/status.md      # how it is going (between takes only)
```

The Pi powers itself off when the night is over and the settings read back. Only if the session asks for the larger audio
buffer: `sudo /usr/local/libexec/apertar-campaign-helper arm 1000` (asks your password, restarts Core) before the night.

## 4. At the end of the campaign

```bash
sudo /usr/local/libexec/apertar-campaign-helper disarm
sudo -n /usr/local/libexec/apertar-campaign-helper timers-unmask
sudo rm /etc/sudoers.d/apertar-nvme-campaign /usr/local/libexec/apertar-campaign-helper
ls -l /etc/sudoers.d/apertar-nvme-campaign /usr/local/libexec/apertar-campaign-helper   # both: "No such file"
systemctl is-enabled fstrim.timer man-db.timer logrotate.timer                     # "enabled", not "masked"
tr '\0' '\n' < /proc/$(systemctl show -p MainPID --value apertar-core)/environ | grep LIBCAMERA_RPI_CONFIG_FILE
# prints the Tuning-Files depth 4 path: that comes from start-apertar-core.sh (2026-11-06), not from the campaign
```

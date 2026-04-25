<p align="center">
<img src="images/gs-logo.svg" width="300" alt="Gravity Sync">
</p>

<span align="center">

# Gravity Sync

</span>

### This is an updated fork of Gravity Sync, modified to support Pi-hole v6.x. The original project by [vmstan](https://github.com/vmstan/gravity-sync) was retired in July 2024. This version (6.4.1) restores compatibility with the Pi-hole v6 architecture.

What is better than a [Pi-hole](https://github.com/pi-hole/pi-hole) blocking trackers, advertisements, and other malicious domains on your network? That's right, **two** Pi-hole blocking all that junk on your network!

- [Seriously. Why two Pi-hole?](https://github.com/vmstan/gravity-sync/wiki/Frequent-Questions#why-do-i-need-more-than-one-pi-hole)

But if you have redundant Pi-hole in your network you'll want a simple way to keep the list configurations and local DNS settings identical between the two. That's where Gravity Sync comes in. Setup should only take a few minutes.

## What changed for Pi-hole v6

- `pihole-FTL sql` replaced with `pihole-FTL sqlite3 -ni`
- `pihole restartdns` replaced with `pihole reloaddns` / `pihole reloadlists`
- Custom DNS records path updated to `hosts/custom.list`
- CNAME and static DHCP sync now uses the FTL config API (`pihole-FTL --config`) instead of dnsmasq config files, which were removed in v6
- Automatic Pi-hole v6 detection — falls back to legacy dnsmasq file sync if v6 is not detected

## Features

Gravity Sync replicates the core of Pi-hole's ad/telemetry blocking settings, which includes:

- Adlist settings with status and comments.
- Domain/RegEx whitelists and blacklist along with status and comments.
- Clients and group assignments, along with status and descriptions.

Gravity Sync also replicates local network DNS/DHCP settings, which includes:

- Local DNS Records.
- Local CNAME Records (via FTL config API on v6).
- Static DHCP Assignments (via FTL config API on v6).

### Limitations

Gravity Sync will **not**:

- Modify or sync the individual Pi-hole's upstream DNS resolvers.
- Merge query logs, statistics, long-term data, caches, or other resolution information.
- Sync individual Pi-hole DHCP scoping information or leases.

## Requirements

- Pi-hole v6.x on both primary and secondary instances
- SSH key-based authentication between the two hosts
- `rsync` installed on both hosts
- `inotify-tools` (optional, for event-based auto-sync)

## Setup

1. Copy `gravity-sync` to `/usr/local/bin/gravity-sync` on the primary Pi-hole
2. Create config: `sudo mkdir -p /etc/gravity-sync && sudo nano /etc/gravity-sync/gravity-sync.conf`
3. Set `REMOTE_HOST` and `REMOTE_USER` in the config
4. Set `GS_SSH_PKIF` to your SSH private key path
5. Test: `sudo gravity-sync compare`
6. Sync: `sudo gravity-sync push`

## Automation

### Option A: File watcher (event-based, recommended)

Reacts instantly when Pi-hole config changes, zero CPU overhead while idle.

```bash
sudo apt install inotify-tools -y
sudo cp templates/gravity-sync-watch.sh /usr/local/bin/
sudo chmod +x /usr/local/bin/gravity-sync-watch.sh
sudo cp templates/gravity-sync-watch.service /etc/systemd/system/
sudo systemctl enable --now gravity-sync-watch.service
```

### Option B: Systemd timer (polling every 5 min)

```bash
sudo cp templates/gravity-sync.service /etc/systemd/system/
sudo cp templates/gravity-sync.timer /etc/systemd/system/
sudo systemctl enable --now gravity-sync.timer
```

## Disclaimer

Gravity Sync is not developed by or affiliated with the Pi-hole project. This is an unofficial, community effort, that seeks to implement replication (which is currently not a part of the core Pi-hole product) in a way that provides stability and value to Pi-hole users. The code has been tested across multiple user environments but there always is an element of risk involved with running any arbitrary software you find on the Internet.

Pi-hole is and the Pi-hole logo are [registered trademarks](https://pi-hole.net/trademark-rules-and-brand-guidelines/) of Pi-hole LLC.

## Additional Documentation

- [Frequently Asked Questions](https://github.com/vmstan/gravity-sync/wiki/Frequent-Questions)
- [Changelog](https://github.com/vmstan/gravity-sync/wiki/Changelog)

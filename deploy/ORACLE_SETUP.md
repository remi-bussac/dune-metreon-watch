# Oracle Cloud setup — the parts only you can do

Everything else is automated by `deploy/deploy.sh`. This file covers account
creation, the VM, and the firewall, because those need your identity, your
card, and Oracle's web console.

Budget about **30 minutes**, most of it waiting.

---

## Step 1 — Create the Oracle Cloud account (~10 min)

1. Go to **https://signup.oraclecloud.com**
2. Fill in your details. **Home region matters and can never be changed** —
   pick **US West (San Jose)** or **US West (Phoenix)**. Closest to you, and
   ARM capacity is usually available there.
3. It asks for a **credit card**. This is for identity verification. Always
   Free resources stay free; you are not charged for what we build here.
4. Verify your email, then sign in.

> If signup is rejected (it happens, and it is usually the card/region combo),
> try a different browser or a different card. This is a known Oracle
> annoyance, not something you did wrong.

---

## Step 2 — Upgrade to Pay As You Go (~2 min) — **do not skip this**

Counter-intuitive but important. Oracle **reclaims idle Always Free VMs**:
if 95th-percentile CPU stays under 20% for 7 days, they can take it back.
Our monitor is bursty and might sit under that line.

Upgrading to Pay As You Go **removes reclamation risk entirely while still
costing $0**, because Always Free resources remain free on a PAYG account.

1. Console → the **hamburger menu** (top left) → **Billing & Cost Management**
2. **Upgrade and Payment** → **Upgrade to Pay As You Go**
3. Confirm.

Then set a safety net so a mistake can never surprise you:

4. **Billing & Cost Management → Budgets → Create Budget**
5. Amount **$1**, alert at **100%**. You will get an email if anything ever
   starts costing money.

---

## Step 3 — Create the VM (~10 min)

1. Console → hamburger → **Compute → Instances → Create Instance**
2. **Name**: `dune-watch`
3. **Image and shape** → **Edit**:
   - **Image**: `Canonical Ubuntu 24.04` (or 22.04)
   - **Shape** → **Change shape** → **Ampere** tab → `VM.Standard.A1.Flex`
   - Set **2 OCPUs** and **12 GB memory**

   > Why 2 and not the full 4: fewer cores means our workload registers as a
   > *higher* CPU percentage, which keeps you further from Oracle's idle
   > threshold. It is also plenty — a pass uses about one core for a minute.

4. **Networking**: leave defaults, but make sure **Assign a public IPv4
   address** is **Yes**.
5. **Add SSH keys** → **Paste public keys** → paste the key printed below by
   the command in Step 4.
6. **Create**. Wait for the state to go orange → **green (RUNNING)**.
7. **Copy the Public IP address** shown on the instance page. You need it next.

> **"Out of host capacity"** is the common failure here. Ampere is popular and
> free. Just retry — different availability domain (AD-1/AD-2/AD-3) from the
> dropdown, or try again in a few hours. It is not a problem with your account.

---

## Step 4 — Get your SSH public key

On your laptop:

```bash
cat ~/.ssh/id_ed25519.pub
```

Copy the whole line (starts `ssh-ed25519`, ends with your email) and paste it
into the box in Step 3.5.

---

## Step 5 — Deploy (~10 min, mostly the Chromium download)

One command on your laptop. Replace the IP with yours from Step 3.7:

```bash
./deploy/deploy.sh 141.148.1.2
```

The first time, SSH asks `Are you sure you want to continue connecting?` —
type **yes**.

This copies the code, installs Python, Playwright and Chromium, and registers
the systemd timer.

---

## Step 6 — Add the Gmail app password

The bootstrap creates the credentials file but cannot fill in the secret.

```bash
ssh ubuntu@141.148.1.2
nano ~/.dune-metreon-watch.env
```

Replace `PUT_YOUR_16_CHAR_APP_PASSWORD_HERE` with the app password (the same
one on your laptop — `grep GMAIL_APP_PASSWORD ~/.dune-metreon-watch.env`).

In `nano`: edit, then **Ctrl+O**, **Enter** to save, **Ctrl+X** to exit.

Then run one pass to confirm mail works:

```bash
sudo systemctl start dune-watch.service
journalctl -u dune-watch.service -n 30 --no-pager
```

You want to see four `ok` lines and `run end (exit 0)`.

---

## Step 7 — Confirm it is scheduled

```bash
systemctl list-timers dune-watch.timer
```

Shows the next run time. Then log out — it keeps running whether or not your
laptop is on. That is the entire point of this migration.

---

## Everyday commands

| What | Command |
|---|---|
| Is it alive? | `systemctl list-timers dune-watch.timer` |
| Watch live | `journalctl -u dune-watch.service -f` |
| Last run | `journalctl -u dune-watch.service -n 40 --no-pager` |
| Run one now | `sudo systemctl start dune-watch.service` |
| Push code changes | `./deploy/deploy.sh <IP>` (from the laptop) |
| Pause it | `sudo systemctl stop dune-watch.timer` |
| Resume | `sudo systemctl start dune-watch.timer` |

## Changing the cadence

Edit **one line** — `OnUnitActiveSec` in `deploy/dune-watch.timer` — then
redeploy:

```bash
./deploy/deploy.sh <IP>
```

Suggested: `15min` now, `10min` from October, `5min` in December. Cost is $0
at every one of these, so the only limit is being polite to Fandango.

## Teardown (December, or whenever you are done)

```bash
ssh ubuntu@<IP> 'sudo systemctl disable --now dune-watch.timer'
```

Then Console → **Compute → Instances → dune-watch → Terminate**. Tick
**"Permanently delete the attached boot volume"** so nothing lingers.

## If it stops working

1. `journalctl -u dune-watch.service -n 60 --no-pager` — the error is almost
   always in the last 20 lines.
2. `df -h` — a full disk breaks Chromium in confusing ways. Logs are the usual
   culprit; `sudo journalctl --vacuum-time=7d` clears them.
3. `free -m` — if memory is exhausted, Chromium was probably left running:
   `pkill -f chromium`.
4. Nothing in the inbox for over a week and the timer looks fine? The weekly
   heartbeat is the canary — no heartbeat means the VM is not running the job,
   regardless of what the timer says.

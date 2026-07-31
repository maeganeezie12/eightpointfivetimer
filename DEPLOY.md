# Deploying to the Ubuntu server (192.119.82.215)

```
sudo git clone https://github.com/maeganeezie12/eightpointfivetimer.git /opt/eightpointfivetimer
sudo chown -R $USER:$USER /opt/eightpointfivetimer
cd /opt/eightpointfivetimer

python3 -m venv venv
venv/bin/pip install -r requirements.txt

cp .env.example .env
# edit .env if needed (timezone, work duration, port)

sudo cp work_timer.service /etc/systemd/system/work_timer.service
sudo systemctl daemon-reload
sudo systemctl enable --now work_timer.service

# allow the port through the firewall if ufw is active
sudo ufw allow 8000

# verify
curl http://localhost:8000/health
```

Provision users (run inside the venv, from `/opt/eightpointfivetimer`):

```
venv/bin/python provision.py add "Bob Tan"
venv/bin/python provision.py list
```

Copy the printed password into that person's `client_config.env` (see `client/SETUP.md`).

Confirm reachability from another machine on the network:

```
curl http://192.119.82.215:8000/health
```

## Updating after a future `git push`

```
cd /opt/eightpointfivetimer
git pull
venv/bin/pip install -r requirements.txt
sudo systemctl restart work_timer.service
```

## Deploying a second, isolated instance (e.g. a different group of coworkers)

A port belongs to one running process, so a different port means a second
instance — its own clone, own venv, own database, own dashboard, fully
separate from the first. No code changes needed; it's the same repo, just
deployed twice. Example for port 6767, naming this one "teamb" (swap in
whatever name fits):

```
sudo git clone https://github.com/maeganeezie12/eightpointfivetimer.git /opt/eightpointfivetimer-teamb
sudo chown -R $USER:$USER /opt/eightpointfivetimer-teamb
cd /opt/eightpointfivetimer-teamb

python3 -m venv venv
venv/bin/pip install -r requirements.txt

cp .env.example .env
# edit .env: set PORT=6767 (and TIMEZONE/WORK_DURATION_HOURS if this group needs different defaults)
# — the systemd unit reads PORT from this file, no need to edit the unit's port directly

sudo cp work_timer.service /etc/systemd/system/work_timer_teamb.service
sudo sed -i 's|/opt/eightpointfivetimer|/opt/eightpointfivetimer-teamb|g' /etc/systemd/system/work_timer_teamb.service
sudo systemctl daemon-reload
sudo systemctl enable --now work_timer_teamb.service

sudo ufw allow 6767

curl http://localhost:6767/health
```

Provision this group's users the same way, just from the new directory:
```
cd /opt/eightpointfivetimer-teamb
venv/bin/python provision.py add "Their Name"
```

Their dashboard is `http://192.119.82.215:6767/`, completely independent of the
one on 8000 — different users, different database, different checkins. Each
group's `checkin_daemon.py` client just points its `SERVER_URL` at the port
for its own group.

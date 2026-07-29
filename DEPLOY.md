# Deploying to the Ubuntu server (192.119.82.215)

```
sudo mkdir -p /opt/work_timer_server
sudo chown $USER:$USER /opt/work_timer_server
# copy this folder's contents to /opt/work_timer_server (scp, rsync, or git)

cd /opt/work_timer_server
python3 -m venv venv
venv/bin/pip install -r requirements.txt

cp .env.example .env
# edit .env if needed (timezone, work duration, done message, port)

sudo cp work_timer.service /etc/systemd/system/work_timer.service
sudo systemctl daemon-reload
sudo systemctl enable --now work_timer.service

# allow the port through the firewall if ufw is active
sudo ufw allow 8000

# verify
curl http://localhost:8000/health
```

Provision users (run inside the venv, from `/opt/work_timer_server`):

```
venv/bin/python provision.py add "Bob Tan"
venv/bin/python provision.py list
```

Copy the printed token into that person's `client_config.env` (see `maeg_apps/work_timer/client/SETUP.md`).

Confirm reachability from another machine on the network:

```
curl http://192.119.82.215:8000/health
```

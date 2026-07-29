# Deploying to the Ubuntu server (192.119.82.215)

```
sudo git clone https://github.com/maeganeezie12/eightpointfivetimer.git /opt/eightpointfivetimer
sudo chown -R $USER:$USER /opt/eightpointfivetimer
cd /opt/eightpointfivetimer

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

Provision users (run inside the venv, from `/opt/eightpointfivetimer`):

```
venv/bin/python provision.py add "Bob Tan"
venv/bin/python provision.py list
```

Copy the printed token into that person's `client_config.env` (see `client/SETUP.md`).

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

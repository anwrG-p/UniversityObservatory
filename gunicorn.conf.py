# gunicorn.conf.py
# ----------------
# Gunicorn configuration file for Render deployment.

# Render free tier has 512MB RAM, so we keep workers low
workers = 2

# Increase timeout to 120 seconds so the AI pipeline has time to run
timeout = 120

# Log level
loglevel = "info"

# -*- coding: utf-8 -*-
import time, json, subprocess, sys

def load_cfg():
    with open("config.json","r",encoding="utf-8") as f:
        return json.load(f)

def run_once():
    return subprocess.call([sys.executable, "tracker_category_fixed.py"], shell=False)

def main():
    cfg = load_cfg()
    minutes = int(cfg.get("check_interval_minutes", 60))
    print(f"[info] Loop every {minutes} minutes")
    while True:
        code = run_once()
        time.sleep(minutes*60)

if __name__ == "__main__":
    main()

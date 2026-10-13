import sqlite3, json, time
from pathlib import Path
class ScenarioStore:
    def __init__(self,path:Path):
        path.parent.mkdir(parents=True,exist_ok=True); self.path=path
        with sqlite3.connect(path) as c: c.execute("CREATE TABLE IF NOT EXISTS scenarios(id INTEGER PRIMARY KEY,name TEXT,created REAL,config TEXT)")
    def save(self,name,config):
        with sqlite3.connect(self.path) as c: c.execute("INSERT INTO scenarios(name,created,config) VALUES(?,?,?)",(name,time.time(),json.dumps(config)))
    def list(self):
        with sqlite3.connect(self.path) as c: rows=c.execute("SELECT name,created,config FROM scenarios ORDER BY created DESC").fetchall()
        return [{"name":n,"created":time.strftime('%Y-%m-%d %H:%M',time.localtime(t)),"config":cfg} for n,t,cfg in rows]

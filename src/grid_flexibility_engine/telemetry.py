from dataclasses import dataclass,asdict
import time,uuid
@dataclass
class Event:
    event_id:str; timestamp:float; operation:str; duration_ms:float; status:str; entity_id:str|None=None; metadata:dict|None=None
class Telemetry:
    def __init__(self): self.events=[]
    def record(self,operation,start,status="success",entity_id=None,metadata=None): self.events.append(Event(str(uuid.uuid4()),time.time(),operation,(time.perf_counter()-start)*1000,status,entity_id,metadata))
    def export(self): return [asdict(x) for x in self.events]

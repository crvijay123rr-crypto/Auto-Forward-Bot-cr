import time as tm
from database import db 
from .test import parse_buttons

STATUS = {}

class STS:
    def __init__(self, id):
        self.id = id
        self.data = STATUS
    
    def verify(self):
        return self.data.get(self.id)
    
    def store(self, From, to, skip, limit, continuous=False):
        self.data[self.id] = {
            "FROM": From, 'TO': to, 'total_files': 0, 'skip': skip, 
            'limit': limit, 'fetched': skip, 'filtered': 0, 
            'deleted': 0, 'duplicate': 0, 'total': limit, 
            'start': 0, 'continuous': continuous
        }
        self.get(full=True)
        return self
        
    def get(self, value=None, full=False):
        values = self.data.get(self.id)
        if not values: return None
        if not full:
           return values.get(value)
        for k, v in values.items():
            setattr(self, k, v)
        return self

    def add(self, key=None, value=1, time=False):
        if time:
            return self.data[self.id].update({'start': tm.time()})
        
        # Safe addition: agar key exist nahi karti toh 0 maan kar add karega
        current_val = self.data[self.id].get(key, 0)
        self.data[self.id].update({key: current_val + value}) 
    
    def divide(self, no, by):
        try:
            return float(no) / float(by)
        except (ZeroDivisionError, ValueError, TypeError):
            return 0.0
    
    async def get_data(self, user_id):
        bot = await db.get_bot(user_id)
        configs = await db.get_configs(user_id)
        
        # Agar db.get_filters alag se hai toh thik, warna configs se nikalna
        filters = await db.get_filters(user_id) if hasattr(db, 'get_filters') else configs.get('filters', {})
        
        size = None
        if configs.get('file_size') != 0:
            size = [configs['file_size'], configs['size_limit']]
            
        duplicate = False
        if configs.get('duplicate'):
           duplicate = [configs['db_uri'], self.TO]
           
        button = parse_buttons(configs['button'] if configs.get('button') else '')
        
        return bot, configs.get('caption'), configs.get('forward_tag'), {
            'chat_id': self.FROM, 
            'limit': self.limit, 
            'offset': self.skip, 
            'filters': filters,
            'keywords': configs.get('keywords'), 
            'media_size': size, 
            'extensions': configs.get('extension'), 
            'skip_duplicate': duplicate
        }, configs.get('protect'), button
        

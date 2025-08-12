import yaml

class MCPConfigLoader:
    def __init__(self, config_path):
        self.config_path = config_path
        self.servers = self.load_config()

    def load_config(self):
        with open(self.config_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        return data.get('servers', []) 
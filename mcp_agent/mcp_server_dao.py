class MCPServerDAO:
    """MCP Server 数据库访问对象"""
    def __init__(self, mongo_uri=None):
        from pymongo import MongoClient
        import os
        self.mongo_uri = mongo_uri or os.getenv('MONGO_URI')
        self.client = MongoClient(self.mongo_uri)
        self.db = self.client.get_default_database()

    def list_servers(self):
        return list(self.db.servers.find({"enabled": {"$ne": False}}))
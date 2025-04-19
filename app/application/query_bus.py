from app.application.commands import CheckVoterExistsQuery
class QueryBus:
    def __init__(self):
        self.handlers = {}  # A dictionary to store query types and their handlers

    def register_handler(self, query_type, handler):
        """
        Registers a handler for a specific query type.
        :param query_type: The type of the query (e.g., CheckVoterExistsQuery).
        :param handler: The handler responsible for processing the query.
        """
        self.handlers[query_type] = handler

    def handle(self, query):
        """
        Dispatches the query to its appropriate handler.
        :param query: The query object.
        :return: The result from the handler.
        """
        query_type = type(query)
        if query_type not in self.handlers:
            raise ValueError(f"No handler registered for query type: {query_type}")
        handler = self.handlers[query_type]
        return handler.handle(query)

query_bus = QueryBus()

# Register query handlers

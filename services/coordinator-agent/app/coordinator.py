from app.state import WorkflowState

class CoordinatorAgent:

    def handle(self, request):
        context = self._init_context(request)
        return self._route(context)

    def _route(self, context):
        state = context.state

        if state == WorkflowState.RECEIVED:
            return self._dispatch_intake(context)

        raise NotImplementedError("Unsupported workflow state")
